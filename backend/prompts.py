def build_document_type_prompt(document_text: str) -> str:
    return f"""
    You are a document classifier for a recruitment platform.

    Look at the document below and classify it as exactly one of:

    - "resume"            → a candidate's CV/resume (work history, skills, education, personal contact details)
    - "job_description"   → a job posting/JD (role title, responsibilities, required skills, "we are hiring" language)
    - "other"              → anything that is clearly neither of the above

    Base your classification on the overall structure and intent of the
    document, not just keyword matches.

    Document

    {document_text[:6000]}
    """


def build_candidate_extraction_prompt(upload_document_text: str) -> str:
    return f"""
    You are an expert recruitment assistant specializing in resume analysis.

    Your task is to extract structured information from the candidate's resume.

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

    Remove duplicate skills.

    Remove duplicate responsibilities.

    Resume

    {upload_document_text}
    """


def build_job_description_extraction_prompt(upload_document_text: str) -> str:
    return f"""
    You are an expert recruitment assistant specializing in job description analysis.

    Your task is to extract structured information from a Job Description.

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

    Remove duplicate skills.

    Remove duplicate responsibilities.

    Normalize ONLY obvious naming variations.

    If uncertain,
    preserve the original value.

    Do not invent required skills.

    Job Description

    {upload_document_text}
    """


def build_match_score_prompt(cd_data: dict, jd_data: dict) -> str:
    return f"""You are an expert technical recruiter performing a SEMANTIC
    comparison — not a keyword or list comparison — between a candidate and a job.

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
