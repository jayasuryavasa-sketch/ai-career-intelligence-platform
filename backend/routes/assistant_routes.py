from flask import Blueprint,request,jsonify
from utils.auth_utils import current_user_id,login_required
from utils.json_manager import user_rows
from utils.validators import text
from services.gemini_service import generate
bp=Blueprint("assistant",__name__)
@bp.post("/assistant/message")
@login_required
def message():
 uid=current_user_id(); d=request.get_json(silent=True) or {}; question=text(d.get("message"),"Message",1500,True); p=(user_rows("profiles",uid) or [{}])[0]; plans=user_rows("career_plans",uid); resume=user_rows("resumes",uid); gaps=user_rows("skill_gaps",uid)
 result=generate("Answer the user's career question using only provided profile context. Be concise and actionable. Avoid guarantees. Return JSON keys finding, why_it_matters, recommended_action, next_step.",{"question":question,"profile":p,"latest_plan":plans[-1]["result"] if plans else None,"latest_resume_score":resume[-1]["result"]["ats"]["score"] if resume else None,"latest_skill_analysis":gaps[-1]["result"] if gaps else None,"page":text(d.get("page",""),"Current page",60)})
 return jsonify(result=result)
