import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pdfplumber
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from groq import Groq
from pydantic import BaseModel, ConfigDict, ValidationError
from werkzeug.utils import secure_filename

if __package__:
    from .prompts import (
        build_candidate_extraction_prompt,
        build_document_type_prompt,
        build_job_description_extraction_prompt,
        build_match_score_prompt,
    )
else:
    from prompts import (
        build_candidate_extraction_prompt,
        build_document_type_prompt,
        build_job_description_extraction_prompt,
        build_match_score_prompt,
    )

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
CORS(app)  # allows Angular (localhost:4200) to call this API (localhost:5000)

client = None
UPLOAD_FOLDER_INPUT = str(BASE_DIR / "input")
UPLOAD_FOLDER_OUTPUT = str(BASE_DIR / "output")
BULK_CANDIDATE_FOLDER = BASE_DIR.parent / "samples" / "CD"

MODEL_NAME = "openai/gpt-oss-120b"


class CandidateExtract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: str
    skills: list[str]
    summary: str
    responsibilities: list[str]
    email: str
    contact_no: str
    location: str
    years_of_experience: int


class JobDescriptionExtract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    required_skills: list[str]
    nice_to_have_skills: list[str]
    responsibilities: list[str]
    min_years_experience: int
    max_years_experience: int
    summary: str


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_percentage: int
    match_reasoning: str
    matched_skills: list[str]
    missing_required_skills: list[str]


class DocumentTypeCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Literal["resume", "job_description", "other"]
    confidence: Literal["low", "medium", "high"]
    reasoning: str


# Maps the uploadType the frontend sends ("CD" / "JD") to the document_type
# label we expect the classifier to return for it.
EXPECTED_DOCUMENT_TYPE = {
    "CD": "resume",
    "JD": "job_description",
}

DOCUMENT_TYPE_LABELS = {
    "resume": "a candidate resume",
    "job_description": "a job description",
    "other": "neither a resume nor a job description",
}


def get_groq_client():
    global client

    if client is not None:
        return client

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    client = Groq(api_key=api_key)
    return client


def call_groq_structured(
    prompt: str,
    schema_model: type[BaseModel],
    schema_name: str,
    model: str = MODEL_NAME,
):
    """
    Calls Groq with response_format=json_schema (strict mode) built from a
    Pydantic model, then validates+parses the result back into that model.

    Returns (parsed_model, error_message). error_message is None on success.
    """
    try:
        groq_client = get_groq_client()
        completion = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema_model.model_json_schema(),
                },
            },
        )
    except (RuntimeError, ValueError, OSError) as exc:
        return None, f"AI request failed: {exc}"

    raw_content = completion.choices[0].message.content

    try:
        parsed = schema_model.model_validate_json(raw_content)
    except ValidationError as exc:
        return None, f"AI response did not match expected schema: {exc}"
    except json.JSONDecodeError:
        return None, "AI response was not valid JSON"

    return parsed, None


def classify_document_type(document_text: str):
    """
    Lightweight classification pass that runs BEFORE the full (expensive)
    extraction. Confirms whether the uploaded document is actually a resume
    or a job description, so we can reject a mismatched upload early instead
    of running a full extraction on the wrong document type.
    """
    prompt = build_document_type_prompt(document_text)

    # Use the smaller/faster model here — classification is a simple task
    # and doesn't need the larger model's extra reasoning capacity.
    parsed, error = call_groq_structured(
        prompt, DocumentTypeCheck, "document_type_check", model="openai/gpt-oss-20b"
    )
    return parsed, error


@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    # 1. Validate file presence
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # 2. Validate uploadType
    upload_type = request.form.get("uploadType")
    if not upload_type:
        return jsonify({"error": "Missing uploadType"}), 400

    # 3. Build a safe, unique filename
    safe_name = secure_filename(file.filename)
    name, ext = os.path.splitext(safe_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    new_filename = f"{name}_{timestamp}{ext}"

    # 4. Build destination folder and ensure it exists
    new_path = os.path.join(UPLOAD_FOLDER_INPUT, f"{upload_type.lower()}_list")
    os.makedirs(new_path, exist_ok=True)

    # 5. Save the file
    filepath = os.path.join(new_path, new_filename)
    file.save(filepath)

    # 6. Run AI extraction on the saved file
    ai_result, error_response, status_code = analyze_document_with_ai(
        filepath, upload_type
    )

    if error_response:
        return error_response, status_code

    # 7. Persist the extracted data
    save_upload_record(upload_type, new_filename, ai_result)

    # 8. Respond with success
    ai_result["filename"] = new_filename

    return jsonify(
        {
            "message": "File uploaded successfully",
            "filename": new_filename,
            "uploadType": upload_type,
            "results": ai_result,
        }
    ), 200


def analyze_document_with_ai(filepath, upload_type):
    # Extract text from the resume PDF
    upload_document_text = ""

    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    upload_document_text += page_text + "\n"
    except (FileNotFoundError, OSError, ValueError) as exc:
        return (
            None,
            jsonify({"error": "Could not read the uploaded PDF", "details": str(exc)}),
            422,
        )

    if not upload_document_text.strip():
        return None, jsonify({"error": "Could not extract text from PDF"}), 422

    # ---------------------------------------------------------------
    # Validate the uploaded document actually matches uploadType before
    # running the full (expensive) extraction. Catches cases like a JD
    # uploaded to the candidate section or vice versa.
    # ---------------------------------------------------------------
    expected_type = EXPECTED_DOCUMENT_TYPE.get(upload_type)

    if expected_type is not None:
        type_check, type_check_error = classify_document_type(upload_document_text)

        if type_check_error:
            # Don't hard-fail the whole upload just because the lightweight
            # classification step had an issue — log and continue to the
            # real extraction rather than blocking the user.
            print(
                f"Document type classification failed, skipping check: {type_check_error}"
            )
        elif type_check.document_type != expected_type:
            expected_label = DOCUMENT_TYPE_LABELS[expected_type]

            return (
                None,
                jsonify(
                    {
                        "error": "Document type mismatch",
                        "details": f"This doesn't look like {expected_label}. Please upload {expected_label}.",
                        "detected_document_type": type_check.document_type,
                        "expected_document_type": expected_type,
                        "confidence": type_check.confidence,
                    }
                ),
                422,
            )

    if upload_type == "CD":
        parsed, error = call_groq_structured(
            build_candidate_extraction_prompt(upload_document_text),
            CandidateExtract,
            "candidate_extract",
        )
    else:
        parsed, error = call_groq_structured(
            build_job_description_extraction_prompt(upload_document_text),
            JobDescriptionExtract,
            "job_description_extract",
        )

    if error:
        return None, jsonify({"error": "AI analysis failed", "details": error}), 502

    return parsed.model_dump(), None, None


def save_upload_record(upload_type, filename, ai_result):
    os.makedirs(UPLOAD_FOLDER_OUTPUT, exist_ok=True)
    store_path = os.path.join(UPLOAD_FOLDER_OUTPUT, f"{upload_type.lower()}_data.json")

    records = []
    if os.path.exists(store_path):
        with open(store_path, "r", encoding="utf-8") as f:
            records = json.load(f)

    records.append({"filename": filename, **ai_result})

    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


@app.route("/api/upload-all-candidates", methods=["POST"])
def upload_all_candidates():
    candidate_folder = BULK_CANDIDATE_FOLDER
    if not candidate_folder.is_dir():
        return jsonify({"error": "Candidate upload folder not found"}), 404

    candidate_files = sorted(
        path
        for path in candidate_folder.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    store_path = Path(UPLOAD_FOLDER_OUTPUT) / "cd_data.json"
    existing_records = []
    if store_path.exists():
        with store_path.open("r", encoding="utf-8") as file:
            existing_records = json.load(file)

    existing_filenames = {
        record.get("filename") for record in existing_records if record.get("filename")
    }
    processed = 0
    skipped = 0
    failed = []

    for candidate_file in candidate_files:
        if candidate_file.name in existing_filenames:
            skipped += 1
            continue

        ai_result, error_response, _ = analyze_document_with_ai(
            str(candidate_file), "CD"
        )
        if error_response:
            error_details = error_response.get_json()
            failed.append(
                {
                    "filename": candidate_file.name,
                    "error": error_details.get("details")
                    or error_details.get("error")
                    or "Candidate processing failed",
                }
            )
            continue

        save_upload_record("CD", candidate_file.name, ai_result)
        existing_filenames.add(candidate_file.name)
        processed += 1

    return jsonify(
        {
            "total": len(candidate_files),
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
        }
    ), 200


@app.route("/api/match-score-with-ai", methods=["POST"])
def match_score_with_ai():
    data = request.json

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    cd_data = data.get("cd_result")
    jd_data = data.get("jd_result")

    if not cd_data or not jd_data:
        return jsonify({"error": "Missing jd_result or cd_result"}), 400

    match_result_final, error = get_match_score_with_ai(cd_data, jd_data)

    if error:
        return jsonify({"error": "AI matching failed", "details": error}), 502

    return jsonify(match_result_final), 200


def get_match_score_with_ai(cd_data, jd_data):
    prompt = build_match_score_prompt(cd_data, jd_data)

    parsed, error = call_groq_structured(prompt, MatchResult, "match_result")

    if error:
        return None, error

    return {**cd_data, **parsed.model_dump()}, None


@app.route("/api/candidate_list", methods=["GET"])
def candidate_list():
    cdListJsonPath = os.path.join(UPLOAD_FOLDER_OUTPUT, "cd_data.json")
    if not os.path.exists(cdListJsonPath):
        return jsonify([]), 200

    with open(cdListJsonPath, "r", encoding="utf-8") as file:
        cd_json_list = json.load(file)

    return jsonify(list(reversed(cd_json_list))), 200


@app.route("/api/download-uploaded-file/<filename>", methods=["GET"])
def download_uploaded_file(filename):
    upload_type = request.args.get("uploadType") or request.form.get("uploadType")
    if not upload_type:
        return jsonify(
            {"error": "Missing uploadType query parameter or form field"}
        ), 400

    safe_upload_type = secure_filename(upload_type).lower()
    safe_filename_value = secure_filename(filename)
    new_path = os.path.join(UPLOAD_FOLDER_INPUT, f"{safe_upload_type}_list")

    if not os.path.isdir(new_path):
        return jsonify(
            {"error": f"Upload folder not found for type: {upload_type}"}
        ), 404

    return send_from_directory(new_path, safe_filename_value, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
