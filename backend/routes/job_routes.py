from flask import Blueprint,request,jsonify
from utils.auth_utils import current_user_id,login_required
from utils.json_manager import user_rows
from utils.validators import text
from utils.error_handler import ApiError
from services.gemini_service import generate
from urllib.parse import quote_plus
import re
bp=Blueprint("jobs",__name__)
RESUME_SKILL_CATALOG=("Python","JavaScript","TypeScript","Java","C++","C#","C","HTML","CSS","Flask","Django","React","Node.js","SQL","MySQL","PostgreSQL","MongoDB","Git","REST APIs","Docker","AWS","Azure","Excel","Power BI","Tableau","Machine Learning","Data Analysis","Communication","Problem Solving")

def portal_links(role, skills, search_override=None):
 # Use a compact query so each destination opens a useful role search while
 # avoiding excessively long URLs for profiles with many saved skills.
 skill_terms = skills if isinstance(skills, list) else str(skills or "").replace(",", " ").split()
 skill_terms = list(dict.fromkeys(str(skill).strip() for skill in skill_terms if str(skill).strip()))[:8]
 search_terms = search_override or " ".join([role, *skill_terms])
 q=quote_plus(search_terms)
 role_slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-")
 return {
  "LinkedIn":f"https://www.linkedin.com/jobs/search/?keywords={q}",
  # Indeed requires both its search-results path and q parameter; include
  # India as the default location so the link opens listings, not its homepage.
  "Indeed India":f"https://in.indeed.com/jobs?q={q}&l=India",
  "Naukri":f"https://www.naukri.com/jobs-in-india?keyword={q}",
  "Foundit":f"https://www.foundit.in/search/{role_slug}-jobs-in-india?query={q}",
  "National Career Service (Govt. of India)":f"https://www.ncs.gov.in/Pages/Search.aspx?search={q}",
  "Internshala (jobs & internships)":f"https://internshala.com/jobs/{role_slug}-jobs/?search={q}",
  "Wellfound (startups)":f"https://wellfound.com/jobs?keywords={q}",
  "Cutshort (tech jobs)":f"https://cutshort.io/search-jobs?query={q}",
 }

def _terms(value):
 if isinstance(value, list):
  return [str(item).strip() for item in value if str(item).strip()]
 if isinstance(value, str):
  return [part.strip() for part in re.split(r"[,\n]", value) if part.strip()]
 return []

def _resume_skill_terms(resume_result):
 ats=resume_result.get("ats") or {}; analysis=resume_result.get("analysis") or {}
 terms=_terms(ats.get("matched_keywords"))+_terms(analysis.get("strengths"))
 preview=str(resume_result.get("text_preview") or "")
 for skill in RESUME_SKILL_CATALOG:
  pattern=r"(?<![\w+#])"+re.escape(skill)+r"(?![\w+#])"
  if re.search(pattern,preview,re.IGNORECASE):
   terms.append(skill)
 found=[]; seen=set()
 for term in terms:
  key=term.casefold()
  if key not in seen:
   seen.add(key); found.append(term)
 return found

@bp.post("/jobs/match")
@login_required
def match():
 uid=current_user_id(); p=(user_rows("profiles",uid) or [{}])[0]
 latest_resume=(user_rows("resumes",uid) or [])
 resume_result=latest_resume[-1].get("result",{}) if latest_resume else {}
 request_data=request.get_json(silent=True) or {}
 requested_role=request_data.get("target_role")
 role=text(requested_role or resume_result.get("target_role") or p.get("target_role"),"Target role",120,True)
 profile_skills=_terms(p.get("skills"))
 resume_skills=_resume_skill_terms(resume_result)
 # Build query skills from the user's profile and resume analysis, de-duplicated
 # without turning the entire resume text into noisy search keywords.
 skill_terms=[]; seen=set()
 for skill in resume_skills+profile_skills:
  key=skill.casefold()
  if key not in seen:
   seen.add(key); skill_terms.append(skill)
 skill_terms=skill_terms[:8]
 search_override=request_data.get("search_terms")
 search_terms=text(search_override,"Search terms",300,True) if search_override is not None else " ".join([role, *skill_terms])
 q=quote_plus(role)
 learning=[{"name":"Coursera courses","url":f"https://www.coursera.org/courses?query={q}","description":"Courses to build skills for this role."},{"name":"SWAYAM courses","url":"https://swayam.gov.in/","description":"Courses from Indian universities and institutions."}]
 search_basis="your custom search terms" if search_override is not None else ("your latest resume's target role and extracted skills, plus your saved profile skills" if resume_result else "your saved target role and profile skills")
 return jsonify(matches=[{"role":role,"search_terms":search_terms,"search_basis":search_basis,"why_it_matches":f"Search terms are based on {search_basis}. Portal results are live listings to review, not guaranteed matches.","required_skills":skill_terms,"missing_skills":[],"portals":portal_links(role,skill_terms,search_terms if search_override is not None else None),"learning_resources":learning}])
@bp.post("/jobs/analyze-description")
@login_required
def analyze_description():
 d=request.get_json(silent=True) or {}; jd=text(d.get("description"),"Job description",12000,True); p=(user_rows("profiles",current_user_id()) or [{}])[0]; resume=(user_rows("resumes",current_user_id()) or []); resume_text=resume[-1]["result"].get("text_preview","") if resume else ""; known=[s for s in p.get("skills",[]) if s.lower() in jd.lower()]; import re
 keywords=list(dict.fromkeys(re.findall(r"\b[A-Za-z][A-Za-z+#.]{2,}\b",jd)))[:35]; missing=[x for x in keywords[:20] if x.lower() not in (resume_text+" "+" ".join(p.get("skills",[]))).lower()]
 return jsonify(result={"match":round(100*len(known)/max(1,len(p.get("skills",[])))),"matched_skills":known,"missing_skills":missing[:12],"important_keywords":keywords[:15],"resume_improvements":["Use evidence from your actual experience to address relevant requirements."],"interview_topics":missing[:6],"disclaimer":"Keyword overlap is an estimate, not a hiring prediction."})
