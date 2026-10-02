from flask import Blueprint, request, jsonify
from utils.auth_utils import current_user_id, login_required
from utils.json_manager import user_rows, upsert
from utils.validators import text
from services.gemini_service import generate
bp=Blueprint("career",__name__)

@bp.post("/career/plan")
@login_required
def plan():
    uid=current_user_id(); d=request.get_json(silent=True) or {}; rows=user_rows("profiles",uid); profile=rows[0] if rows else {}; payload={**profile,**d}; role=text(payload.get("target_role"),"Target role",120,True)
    result=generate("Create a realistic adaptive 30-day career plan. Return keys summary, strengths, skill_gaps, plan (30 objects with day, topic, why, objective, practice, estimated_minutes, resources), next_action. Do not invent URLs; resources should use descriptive names only.",payload)
    result["mode"]="gemini"
    stored={"user_id":uid,"target_role":role,"result":result}; upsert("career_plans",stored,"user_id"); return jsonify(plan=result)
@bp.get("/career/plan")
@login_required
def get_plan():
    rows=user_rows("career_plans",current_user_id()); return jsonify(plan=(rows[-1].get("result") if rows else None))
