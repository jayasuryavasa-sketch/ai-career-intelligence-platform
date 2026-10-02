from flask import Blueprint,request,jsonify
from utils.auth_utils import current_user_id,login_required
from utils.json_manager import user_rows,read,write
from utils.validators import text
from utils.error_handler import ApiError
import uuid
bp=Blueprint("applications",__name__); STATUSES={"Saved","Applied","Assessment","Interview","Offer","Rejected"}
@bp.get("/applications")
@login_required
def list_apps(): return jsonify(items=user_rows("applications",current_user_id()))
@bp.post("/applications")
@login_required
def create():
 d=request.get_json(silent=True) or {}; item={"id":"app_"+uuid.uuid4().hex,"user_id":current_user_id(),"company":text(d.get("company"),"Company",120,True),"role":text(d.get("role"),"Role",120,True),"application_date":text(d.get("application_date"),"Application date",20),"status":d.get("status","Saved"),"interview_date":text(d.get("interview_date"),"Interview date",20),"notes":text(d.get("notes"),"Notes",1500)}
 if item["status"] not in STATUSES: raise ApiError("Choose a valid application status.")
 rows=read("applications"); rows.append(item); write("applications",rows); return jsonify(item=item),201
@bp.put("/applications/<app_id>")
@login_required
def update(app_id):
 uid=current_user_id(); d=request.get_json(silent=True) or {}; rows=read("applications"); item=next((r for r in rows if r["id"]==app_id and r["user_id"]==uid),None)
 if not item: raise ApiError("Application not found.",404,"not_found")
 for k,limit in (("company",120),("role",120),("application_date",20),("interview_date",20),("notes",1500)):
  if k in d: item[k]=text(d[k],k,limit)
 if "status" in d:
  if d["status"] not in STATUSES: raise ApiError("Choose a valid application status.")
  item["status"]=d["status"]
 write("applications",rows); return jsonify(item=item)
@bp.delete("/applications/<app_id>")
@login_required
def delete(app_id):
 uid=current_user_id(); rows=read("applications"); kept=[r for r in rows if not(r["id"]==app_id and r["user_id"]==uid)]
 if len(kept)==len(rows): raise ApiError("Application not found.",404,"not_found")
 write("applications",kept); return jsonify(message="Application removed.")
