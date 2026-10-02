from flask import Blueprint, request, jsonify
import re

from utils.auth_utils import current_user_id, login_required
from utils.json_manager import user_rows
from utils.validators import skills, text
from utils.error_handler import ApiError
from services.gemini_service import generate

bp = Blueprint("projects", __name__)
RESUME_SKILL_CATALOG = (
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "HTML", "CSS",
    "Flask", "Django", "React", "Node.js", "SQL", "MySQL", "PostgreSQL", "MongoDB",
    "Git", "REST APIs", "Docker", "AWS", "Azure", "Excel", "Power BI", "Tableau",
    "Machine Learning", "Data Analysis", "Communication", "Problem Solving",
)


def _terms(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,\n]", value) if part.strip()]
    return []


def _project_context(uid):
    profiles = user_rows("profiles", uid)
    profile = profiles[0] if profiles else {}
    resumes = user_rows("resumes", uid)
    resume_result = resumes[-1].get("result", {}) if resumes else {}
    ats = resume_result.get("ats") or {}
    analysis = resume_result.get("analysis") or {}

    # Keep concise skill names only; generated resume feedback may contain
    # full sentences that are useful commentary but not valid skill tags.
    resume_skills = _terms(ats.get("matched_keywords"))
    resume_skills += [
        item for item in _terms(analysis.get("strengths"))
        if len(item) <= 40 and len(item.split()) <= 5
    ]
    preview = str(resume_result.get("text_preview") or "")
    for skill in RESUME_SKILL_CATALOG:
        pattern = r"(?<![\w+#])" + re.escape(skill) + r"(?![\w+#])"
        if re.search(pattern, preview, re.IGNORECASE):
            resume_skills.append(skill)

    combined_skills = []
    seen = set()
    for skill in resume_skills + _terms(profile.get("skills")):
        if len(skill) > 60:
            continue
        key = skill.casefold()
        if key not in seen:
            seen.add(key)
            combined_skills.append(skill)

    resume_role = resume_result.get("target_role")
    role = resume_role or profile.get("target_role", "")
    return {
        "target_role": role,
        "skills": combined_skills[:12],
        "experience": profile.get("experience", ""),
        "resume_filename": resume_result.get("filename", ""),
        "role_source": "Latest resume analysis" if resume_role else "Saved profile",
        "skills_source": "Latest resume analysis + saved profile" if resume_result else "Saved profile",
        "has_resume": bool(resume_result),
    }


@bp.get("/projects/context")
@login_required
def context():
    return jsonify(context=_project_context(current_user_id()))


@bp.post("/projects/recommend")
@login_required
def recommend():
    uid = current_user_id()
    d = request.get_json(silent=True) or {}
    context_data = _project_context(uid)
    role = text(d.get("target_role", context_data["target_role"]), "Target role", 120)
    raw_skills = _terms(d.get("skills", context_data["skills"]))
    if any(len(skill) > 60 for skill in raw_skills):
        raise ApiError("Enter short skill names, each 60 characters or fewer. Remove full resume sentences from the skills field.")
    current_skills = skills(raw_skills)[:12]
    experience = text(d.get("experience", context_data["experience"]), "Experience", 80)
    payload = {
        "role": role or "career exploration",
        "skills": current_skills,
        "experience": experience,
        "resume_context": {
            "source": context_data["skills_source"],
            "resume_filename": context_data["resume_filename"],
        },
    }
    prompt = (
        "Recommend three distinctive, feasible portfolio projects tailored to the user's target role, "
        "experience and skills extracted from their resume/profile. Each must be a learning idea, not "
        "something the user has already done. Return JSON with projects array. Each project must include "
        "title, difficulty, skills, description, features, roadmap and resume_bullets. Be specific to the "
        "provided context, avoid generic clones, and do not invent user experience."
    )
    try:
        result = generate(prompt, payload)
    except ApiError as e:
        if e.code != "ai_not_configured":
            raise
        result = {
            "projects": [{
                "title": f"{payload['role'].title()} Portfolio Project",
                "difficulty": "Beginner to intermediate",
                "skills": current_skills,
                "description": f"Build a focused project that demonstrates {payload['role']} skills using your current experience as a starting point.",
                "features": ["One realistic user workflow", "Input validation and clear error states", "A concise README with screenshots and setup steps"],
                "roadmap": ["Define the user problem and success criteria", "Build the core workflow and test it", "Polish the interface, document it and deploy if practical"],
                "resume_bullets": ["After completing: describe the feature you built and add a truthful measured result."],
                "note": "Starter recommendation based on your saved context; configure Gemini for more tailored project options.",
            }]
        }
    return jsonify(result=result, context={
        **context_data,
        "target_role": role,
        "skills": current_skills,
        "experience": experience,
        "role_source": "Edited by you" if d.get("target_role") is not None else context_data["role_source"],
        "skills_source": "Edited by you" if d.get("skills") is not None else context_data["skills_source"],
    })
