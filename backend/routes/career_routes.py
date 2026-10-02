from flask import Blueprint, request, jsonify
from utils.auth_utils import current_user_id, login_required
from utils.json_manager import user_rows, upsert
from utils.validators import text
from utils.error_handler import ApiError
from services.gemini_service import generate
from services.local_career import fallback_plan
bp=Blueprint("career",__name__)

@bp.post("/career/plan")
@login_required
def plan():
    uid=current_user_id(); d=request.get_json(silent=True) or {}; rows=user_rows("profiles",uid); profile=rows[0] if rows else {}; payload={**profile,**d}; role=text(payload.get("target_role"),"Target role",120,True)
    try:
        result=generate("Create a realistic adaptive 30-day career plan. Return keys summary, strengths, skill_gaps, plan (30 objects with day, topic, why, objective, practice, estimated_minutes, resources), next_action. Do not invent URLs; resources should use descriptive names only.",payload,request_budget_seconds=25)
        result["mode"]="gemini"
    except ApiError as error:
        fallback_codes={"ai_not_configured","ai_rate_limited","ai_unavailable","ai_timeout","ai_model_unavailable","ai_invalid_response","ai_auth_failed"}
        if error.code not in fallback_codes:
            raise
        result=fallback_plan(role,payload.get("skills",[]),payload.get("available_time","1 hour"))
        result["mode"]="local_fallback"
        result["ai_status"]="Gemini did not return a plan, so CareerOS created this starter plan locally. You can retry AI guidance later."
    result["target_role"]=role
    stored={"user_id":uid,"target_role":role,"result":result}; upsert("career_plans",stored,"user_id"); return jsonify(plan=result)
@bp.get("/career/plan")
@login_required
def get_plan():
    rows=user_rows("career_plans",current_user_id()); return jsonify(plan=(rows[-1].get("result") if rows else None))
