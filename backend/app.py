import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import pdfplumber
from groq import Groq
from datetime import datetime
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
CORS(app)  # allows Angular (localhost:4200) to call this API (localhost:5000)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
UPLOAD_FOLDER_INPUT = "input"
UPLOAD_FOLDER_OUTPUT = "output"


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
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
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
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                upload_document_text += page_text + "\n"

    if not upload_document_text.strip():
        return jsonify({"error": "Could not extract text from PDF"}), 422

    # Candidate Extract Prompt
    cd_prompt = f"""Extract structured information from this resume and respond
    with ONLY valid JSON (no markdown, no commentary) in this exact shape:
    {{
    "name": "string",
    "role": "string (their current or most recent job title)",
    "skills": (as a list),
    "summary": "2-3 sentence summary of their background and seniority level",
    "responsibilities": (as a list),
    "email": "string",
    "contact_no": "number",
    "location": "string",
    "years_of_experience": 0
    }}

    Guidelines:
    - "skills" should include both explicitly listed skills AND ones clearly
    implied by their experience (e.g., "built CI/CD pipelines in GitHub Actions"
    implies both "CI/CD" and "GitHub Actions", even without a skills section).
    - "responsibilities" should be YOUR OWN paraphrase of what this person likely
    did day-to-day across their roles — not copied verbatim from resume bullets.
    - "years_of_experience" should be your best estimate based on their work
    history dates, as a whole number.
    - Infer seniority (junior/mid/senior/lead) from experience depth and scope,
    and reflect that in "summary".

    Resume text:
    {upload_document_text}
    """
    # Job Description Extract Prompt
    jd_prompt = f"""Extract structured information from this job description and
    respond with ONLY valid JSON (no markdown, no commentary) in this exact shape:

    {{
    "title": "string (the job title being hired for)",
    "required_skills": ["string", "string"],
    "nice_to_have_skills": ["string", "string"],
    "responsibilities": ["string", "string"],
    "min_years_experience": 0,
    "max_years_experience": 0,
    "summary": "2-3 sentence summary of the role and what success looks like",
    }}

    Guidelines:
    - Separate "required_skills" (must-haves, non-negotiable) from
    "nice_to_have_skills" (preferred but not mandatory) based on the language
    used (e.g., "must have", "required" vs "nice to have", "bonus", "plus").
    - "responsibilities" should paraphrase the core duties in your own words,
    not copy bullet points verbatim.
    - "min_years_experience" and "max_years_experience" should reflect the
    experience range stated or implied in the JD:
    * If a range is explicitly stated (e.g., "3-5 years"), use those exact
        numbers: min=3, max=5.
    * If only a single number is stated (e.g., "5+ years"), use it as the
        min, and set max to a reasonable upper bound for that seniority
        (e.g., min=5, max=8).
    * If no number is stated at all, infer both from seniority language:
        - "Junior" / "Entry-level" → min=0, max=2
        - "Mid-level" → min=2, max=5
        - "Senior" → min=5, max=8
        - "Lead" / "Staff" / "Principal" → min=8, max=12
    * "max_years_experience" should always be greater than or equal to
        "min_years_experience".

    Job description text:
    {upload_document_text}
    """

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": cd_prompt if upload_type == "CD" else jd_prompt,
            }
        ],
        response_format={"type": "json_object"},
    )

    ai_result_text = completion.choices[0].message.content

    try:
        ai_result = json.loads(ai_result_text)
    except json.JSONDecodeError:
        return (
            None,
            jsonify({"error": "AI response was not valid JSON", "raw": ai_result_text}),
            502,
        )

    return ai_result, None, None


def save_upload_record(upload_type, filename, ai_result):
    store_path = os.path.join(UPLOAD_FOLDER_OUTPUT, f"{upload_type.lower()}_data.json")

    records = []
    if os.path.exists(store_path):
        with open(store_path, "r") as f:
            records = json.load(f)

    records.append({"filename": filename, **ai_result})

    with open(store_path, "w") as f:
        json.dump(records, f, indent=2)


@app.route("/api/match-score-with-ai", methods=["POST"])
def match_score_with_ai():
    data = request.json

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    cd_data = data.get("cd_result")
    jd_data = data.get("jd_result")

    if not cd_data or not jd_data:
        return jsonify({"error": "Missing jd_result or cd_result"}), 400

    match_result_final = get_match_score_with_ai(cd_data, jd_data)

    if match_result_final is None:
        return jsonify({"error": "AI matching failed"}), 502

    return jsonify(match_result_final), 200


def get_match_score_with_ai(cd_data, jd_data):
    prompt = f"""You are an expert technical recruiter performing a SEMANTIC
    comparison — not a keyword or list comparison — between a candidate and a job.

    Respond with ONLY valid JSON (no markdown, no commentary) in this exact shape:

    {{
    "match_percentage": 0,
    "match_reasoning": "2-3 sentences explaining the score",
    "matched_skills": ["string", "string"],
    "missing_required_skills": ["string", "string"]
    }}

    HOW TO REASON — this is the most important part:
    - Do NOT simply check whether words in "required_skills" appear in "skills".
    That is keyword matching, and it is explicitly wrong for this task.
    - Instead, read the candidate's "summary" and "responsibilities" as evidence.
    Ask yourself: "Based on what this person has actually DONE, could they
    reasonably do what this job REQUIRES?" — even if the exact terms differ.
    - Only mark something as "missing_required_skills" if, after reading the
    full context, there is genuinely no reasonable evidence of it.
    - Weigh "required_skills" much more heavily than "nice_to_have_skills".

    Job description:
    Title: {jd_data.get("title")}
    Required skills: {jd_data.get("required_skills")}
    Nice to have skills: {jd_data.get("nice_to_have_skills")}
    Responsibilities: {jd_data.get("responsibilities")}
    Summary: {jd_data.get("summary")}

    Candidate resume:
    Role: {cd_data.get("role")}
    Listed skills: {cd_data.get("skills")}
    Responsibilities: {cd_data.get("responsibilities")}
    Summary: {cd_data.get("summary")}
    Years of experience: {cd_data.get("years_of_experience")}
    """

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    try:
        match_result = json.loads(completion.choices[0].message.content)
    except json.JSONDecodeError:
        return None

    return {**cd_data, **match_result}


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
    print(upload_type, "upload_type")
    if not upload_type:
        return jsonify(
            {"error": "Missing uploadType query parameter or form field"}
        ), 400

    safe_upload_type = secure_filename(upload_type).lower()
    new_path = os.path.join(UPLOAD_FOLDER_INPUT, f"{safe_upload_type}_list")

    if not os.path.isdir(new_path):
        return jsonify(
            {"error": f"Upload folder not found for type: {upload_type}"}
        ), 404

    return send_from_directory(new_path, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
