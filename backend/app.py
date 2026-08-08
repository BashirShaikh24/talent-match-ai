import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from groq import Groq
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
CORS(app)  # allows Angular (localhost:4200) to call this API (localhost:5000)

client = None
UPLOAD_FOLDER_INPUT = str(BASE_DIR / "input")
UPLOAD_FOLDER_OUTPUT = str(BASE_DIR / "output")


def get_groq_client():
    global client

    if client is not None:
        return client

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    client = Groq(api_key=api_key)
    return client


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

    # Candidate Extract Prompt
    cd_prompt = f"""
    You are an expert recruitment assistant specializing in resume analysis.

    Your task is to extract structured information from the candidate's resume.

    Return ONLY valid JSON.
    Do NOT include markdown, explanations, or additional text.

    JSON Format

    {{
        "name": "string",
        "role": "string",
        "skills": [],
        "summary": "string",
        "responsibilities": [],
        "email": "string",
        "contact_no": "string",
        "location": "string",
        "years_of_experience": 0
    }}

    =========================
    EXTRACTION RULES
    =========================

    1. NAME

    Extract the candidate's full name.

    -------------------------

    2. ROLE

    Extract the candidate's current or most recent professional job title.

    Do not invent or modify the role.

    -------------------------

    3. SKILLS

    Extract all professional skills that are either:

    • Explicitly listed in the resume
    OR
    • Clearly demonstrated through work experience.

    Skills may include:

    - Programming languages
    - Frameworks
    - Libraries
    - Databases
    - Cloud platforms
    - Software
    - Tools
    - Platforms
    - Technologies
    - Methodologies
    - Business applications
    - Professional techniques
    - Certifications representing a skill
    - Domain knowledge

    Do NOT include:

    - Company names
    - Responsibilities
    - Soft skills
    - Personality traits
    - Generic adjectives

    Normalization Rules

    Normalize ONLY obvious naming variations.

    Examples

    Angular 17 → Angular
    Angular 18 → Angular
    ReactJS → React
    RESTful APIs → REST API
    REST Services → REST API
    MS Excel → Microsoft Excel
    Power BI Desktop → Power BI

    Remove duplicate skills.

    IMPORTANT

    If two skills are different technologies,
    DO NOT merge them.

    Examples

    Angular ≠ AngularJS

    Java ≠ JavaScript

    SQL ≠ SQL Server

    AWS ≠ Azure

    If you are NOT confident that two skills represent the same technology,
    KEEP THE ORIGINAL SKILL.

    Never guess.

    -------------------------

    4. SUMMARY

    Generate a concise professional summary.

    2–3 sentences.

    Include:

    - Overall background
    - Seniority
    - Primary expertise

    Do not exaggerate.

    -------------------------

    5. RESPONSIBILITIES

    Summarize the candidate's primary responsibilities.

    Requirements

    - Preserve original meaning
    - Do NOT copy resume bullets verbatim
    - Use concise action statements
    - Remove duplicates
    - Maximum 10 items
    - Do NOT invent responsibilities

    -------------------------

    6. EMAIL

    Extract email.

    -------------------------

    7. CONTACT NUMBER

    Extract primary phone number.

    -------------------------

    8. LOCATION

    Extract latest location.

    -------------------------

    9. YEARS OF EXPERIENCE

    Estimate total professional experience based on employment history.

    Return a whole number.

    =========================
    OUTPUT RULES
    =========================

    Return ONLY valid JSON.

    Remove duplicate skills.

    Remove duplicate responsibilities.

    Do not include markdown.

    Resume

    {upload_document_text}
    """

    # Job Description Extract Prompt
    jd_prompt = f"""
    You are an expert recruitment assistant specializing in job description analysis.

    Your task is to extract structured information from a Job Description.

    Return ONLY valid JSON.

    Do NOT include markdown, explanations, or additional text.

    JSON Format

    {{
        "title": "string",
        "required_skills": [],
        "nice_to_have_skills": [],
        "responsibilities": [],
        "min_years_experience": 0,
        "max_years_experience": 0,
        "summary": "string"
    }}

    =========================
    EXTRACTION RULES
    =========================

    1. TITLE

    Extract the advertised job title.

    -------------------------

    2. REQUIRED SKILLS

    Extract ONLY mandatory skills.

    Look for wording such as:

    - Must have
    - Required
    - Mandatory
    - Essential
    - Strong experience
    - Hands-on experience
    - Proven experience

    Normalization Rules

    Normalize ONLY obvious naming variations.

    Examples

    Angular 17 → Angular

    ReactJS → React

    RESTful APIs → REST API

    MS Excel → Microsoft Excel

    Power BI Desktop → Power BI

    Remove duplicates.

    IMPORTANT

    Do NOT merge different technologies.

    Angular ≠ AngularJS

    Java ≠ JavaScript

    SQL ≠ SQL Server

    AWS ≠ Azure

    If uncertain,
    KEEP THE ORIGINAL SKILL.

    -------------------------

    3. NICE TO HAVE SKILLS

    Extract preferred skills.

    Look for

    - Nice to have
    - Preferred
    - Bonus
    - Good to have
    - Plus
    - Exposure to
    - Familiarity with

    Apply the same normalization rules.

    Remove duplicates.

    -------------------------

    4. RESPONSIBILITIES

    Summarize responsibilities.

    Requirements

    - Preserve meaning
    - Do not copy JD verbatim
    - Use concise action statements
    - Remove duplicates
    - Maximum 10 items
    - Do not invent responsibilities

    -------------------------

    5. EXPERIENCE

    If a range exists

    Example

    3–5 years

    Return

    min = 3

    max = 5

    If only one value

    5+ years

    Return

    min = 5

    max = 8

    If not specified

    Infer

    Junior → 0–2

    Mid → 2–5

    Senior → 5–8

    Lead / Principal / Staff → 8–12

    -------------------------

    6. SUMMARY

    Generate a concise 2–3 sentence summary describing

    - Purpose of the role
    - Main expectations
    - Success profile

    Do not copy the JD.

    =========================
    OUTPUT RULES
    =========================

    Return ONLY valid JSON.

    Remove duplicate skills.

    Remove duplicate responsibilities.

    Normalize ONLY obvious naming variations.

    If uncertain,
    preserve the original value.

    Do not invent required skills.

    Do not include markdown.

    Job Description

    {upload_document_text}
    """

    try:
        groq_client = get_groq_client()
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": cd_prompt if upload_type == "CD" else jd_prompt,
                }
            ],
            response_format={"type": "json_object"},
        )
    except (RuntimeError, ValueError, OSError) as exc:
        return None, jsonify({"error": "AI analysis failed", "details": str(exc)}), 502

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
    os.makedirs(UPLOAD_FOLDER_OUTPUT, exist_ok=True)
    store_path = os.path.join(UPLOAD_FOLDER_OUTPUT, f"{upload_type.lower()}_data.json")

    records = []
    if os.path.exists(store_path):
        with open(store_path, "r", encoding="utf-8") as f:
            records = json.load(f)

    records.append({"filename": filename, **ai_result})

    with open(store_path, "w", encoding="utf-8") as f:
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

    try:
        groq_client = get_groq_client()
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    except (RuntimeError, ValueError, OSError):
        return None

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
    safe_filename_value = secure_filename(filename)
    new_path = os.path.join(UPLOAD_FOLDER_INPUT, f"{safe_upload_type}_list")

    if not os.path.isdir(new_path):
        return jsonify(
            {"error": f"Upload folder not found for type: {upload_type}"}
        ), 404

    return send_from_directory(new_path, safe_filename_value, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
