from flask import Blueprint, request, jsonify
from utils.auth_utils import current_user_id, login_required
from utils.json_manager import user_rows, upsert
from utils.validators import text, skills

bp=Blueprint("profile",__name__)
@bp.get("/profile")
@login_required
def get_profile():
    rows=user_rows("profiles",current_user_id()); return jsonify(profile=rows[0] if rows else {})

@bp.put("/profile")
@login_required
def update_profile():
    uid=current_user_id(); rows=user_rows("profiles",uid); p=rows[0] if rows else {"user_id":uid,"skills":[]}; d=request.get_json(silent=True) or {}
    for key,limit in (("name",100),("target_role",120),("experience",50),("available_time",30),("education",300),("interests",600)):
        if key in d: p[key]=text(d[key],key.replace("_"," "),limit)
    if "skills" in d: p["skills"]=skills(d["skills"])
    return jsonify(profile=upsert("profiles",p,"user_id"))
