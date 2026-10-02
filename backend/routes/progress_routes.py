from flask import Blueprint,jsonify
from utils.auth_utils import current_user_id,login_required
from utils.json_manager import user_rows
bp=Blueprint("progress",__name__)
@bp.get("/progress")
@login_required
def progress():
 uid=current_user_id(); apps=user_rows("applications",uid); resumes=user_rows("resumes",uid); plans=user_rows("career_plans",uid); interviews=user_rows("interviews",uid); profile=(user_rows("profiles",uid) or [{}])[0]
 return jsonify(progress={"applications":len(apps),"interviews":sum(1 for x in apps if x.get("status")=="Interview"),"offers":sum(1 for x in apps if x.get("status")=="Offer"),"resume_analyses":len(resumes),"latest_ats":resumes[-1]["result"]["ats"]["score"] if resumes else None,"plan_created":bool(plans),"target_role":profile.get("target_role",""),"journey":[{"stage":"Profile","complete":bool(profile.get("target_role"))},{"stage":"Skill analysis","complete":bool(user_rows("skill_gaps",uid))},{"stage":"Learning plan","complete":bool(plans)},{"stage":"Resume","complete":bool(resumes)},{"stage":"Interview practice","complete":bool(interviews)},{"stage":"Applications","complete":bool(apps)}]})
