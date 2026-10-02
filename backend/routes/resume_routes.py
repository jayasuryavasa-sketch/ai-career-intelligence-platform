from flask import Blueprint,request,jsonify
from datetime import datetime,timezone
import uuid
from utils.auth_utils import current_user_id,login_required
from utils.json_manager import user_rows,upsert
from utils.validators import text
from utils.resume_parser import extract
from services.ats_service import score_resume
from services.gemini_service import generate
from utils.error_handler import ApiError
bp=Blueprint("resume",__name__)
@bp.post("/resume/analyze")
@login_required
def analyze():
 uid=current_user_id(); f=request.files.get("file")
 if not f: raise ApiError("Choose a resume file to analyze.")
 filename,body=extract(f); p=(user_rows("profiles",uid) or [{}])[0]; role=text(request.form.get("target_role",p.get("target_role","")),"Target role",120); ats=score_resume(body,role,p.get("skills",[])); result={"id":"res_"+uuid.uuid4().hex,"filename":filename,"target_role":role,"ats":ats,"text_preview":body[:1200],"created_at":datetime.now(timezone.utc).isoformat()}
 try: result["analysis"]=generate("Review this resume against its target role. Return JSON keys summary, strengths, missing_skills, improvements. Never recommend fabricating credentials.",{"resume":body,"role":role,"ats":ats})
 except ApiError as e:
  if e.code!="ai_not_configured": raise
  result["analysis"]={"summary":"Resume text was extracted and scored using reproducible local checks.","strengths":ats["matched_keywords"],"missing_skills":ats["missing_keywords"],"improvements":["Add measurable outcomes where accurate.","Use clear section headings and contact information.","Tailor relevant experience to the target role."],"ai_status":"Gemini is not configured; the score remains deterministic."}
 rows=user_rows("resumes",uid); rows.append({"user_id":uid,"result":result}); allrows=__import__("utils.json_manager",fromlist=["read"]).read("resumes"); allrows=[r for r in allrows if r.get("user_id")!=uid]+rows; __import__("utils.json_manager",fromlist=["write"]).write("resumes",allrows)
 return jsonify(result=result)
@bp.get("/resume/history")
@login_required
def history(): return jsonify(items=[r["result"] for r in user_rows("resumes",current_user_id())])
