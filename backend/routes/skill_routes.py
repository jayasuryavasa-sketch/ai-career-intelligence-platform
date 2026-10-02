import re
from flask import Blueprint,request,jsonify
from utils.auth_utils import current_user_id,login_required
from utils.json_manager import user_rows,upsert
from utils.validators import skills,text
from services.gemini_service import generate
from utils.error_handler import ApiError
bp=Blueprint("skills",__name__)

def _skill_matches(skill, requirement):
 skill=re.sub(r"\s+"," ",str(skill).strip().lower())
 requirement=re.sub(r"\s+"," ",str(requirement).strip().lower())
 if not skill or not requirement: return False
 if skill==requirement: return True
 # Requirements from the AI provider are often phrases, such as
 # "proficiency in a programming language (Python, Java, ...)". Match the
 # user's named skill as a whole word within that phrase.
 if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", requirement): return True
 aliases={
  "js":("javascript",),"javascript":("js",),"ts":("typescript",),"typescript":("ts",),
  "communication":("communicate","written communication","verbal communication","interpersonal skills"),
  "problem solving":("problem-solving","analytical thinking","analytical skills"),
  "git":("github","version control"),"github":("git","version control"),
  "rest api":("rest apis","restful api","restful apis"),"rest apis":("rest api","restful api","restful apis"),
  "oop":("object-oriented programming","object oriented programming"),
 }
 variants=aliases.get(skill,())
 return any(re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",requirement) for alias in variants)

@bp.post("/skills/analyze")
@login_required
def analyze():
 uid=current_user_id(); d=request.get_json(silent=True) or {}; p=(user_rows("profiles",uid) or [{}])[0]; role=text(d.get("target_role",p.get("target_role")),"Target role",120,True); current=skills(d.get("skills",p.get("skills",[]))); required=d.get("required_skills",[]); comparison_basis="Supplied role requirements"
 if not current: raise ApiError("Add at least one current skill so I can identify your strengths and gaps.",400,"skills_required")
 ai_data={}
 if not required:
  try:
   ai_data=generate("Compare this person's skills with a target role. Return JSON with required_skills (5-8 concise skill names or phrases), developing_skills (array of relevant partially developed skills), and priority_skills (up to 3 names chosen from required skills not already covered). Use whole recognizable skill names in requirements, not vague paragraphs. Do not make employer-specific claims.",{"role":role,"experience":p.get("experience"),"current_skills":current})
   required=ai_data.get("required_skills",[]); comparison_basis="AI-generated representative role baseline; validate against relevant job postings."
  except ApiError as e:
   if e.code!="ai_not_configured": raise
   required=["Communication","Problem solving","REST APIs","Git","Testing"]; comparison_basis="Generic starter baseline; add role-specific requirements or configure Gemini for a tailored comparison."
 if isinstance(required,str): required=[required]
 if not isinstance(required,list): required=[]
 required=list(dict.fromkeys(str(x).strip() for x in required if str(x).strip()))
 if not required: raise ApiError("No role requirements were available for comparison.",503,"requirements_unavailable")
 strong=[x for x in current if any(_skill_matches(x,r) for r in required)]
 missing=[r for r in required if not any(_skill_matches(s,r) for s in current)]
 role_lower=role.lower()
 adjacent=["Python API developer","Junior backend developer"] if "python" in role_lower or "backend" in role_lower else ["Junior data analyst","Business intelligence analyst"] if "data" in role_lower else [f"Entry-level {role}",f"Adjacent roles using {missing[0]}" ] if missing else []
 result={"target_role":role,"comparison_basis":comparison_basis,"strong_skills":strong,"developing_skills":[],"missing_skills":missing,"priority_skills":missing[:3],"action_plan":[{"skill":x,"action":f"Learn {x} fundamentals, then demonstrate it in a small project."} for x in missing[:5]],"simulation":{"skill":missing[0] if missing else "No priority gap identified","readiness_before":min(95,45+len(strong)*9),"readiness_after":min(98,55+len(strong)*9),"unlocked_roles":adjacent if missing else []},"disclaimer":"Readiness and adjacent role directions are illustrative estimates, not employment predictions."}
 for key in ("developing_skills","priority_skills"):
  values=ai_data.get(key)
  if isinstance(values,list): result[key]=[str(value).strip() for value in values if str(value).strip()]
 if not ai_data and comparison_basis != "Supplied role requirements":
  result["ai_status"]="Gemini is not configured; showing transparent local comparison."
 upsert("skill_gaps",{"user_id":uid,"result":result},"user_id"); return jsonify(result=result)
@bp.get("/skills/gaps")
@login_required
def get_gaps():
 r=user_rows("skill_gaps",current_user_id()); return jsonify(result=r[0]["result"] if r else None)
