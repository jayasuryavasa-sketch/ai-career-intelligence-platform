import hashlib, secrets, uuid, re, smtplib, os
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from flask import Blueprint, request, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from utils.json_manager import read, write, upsert
from utils.error_handler import ApiError
from utils.validators import text

bp = Blueprint("auth", __name__)
def public(user): return {k:user.get(k,"") for k in ("id","name","email","username","created_at")}

@bp.post("/auth/register")
def register():
    d=request.get_json(silent=True) or {}; name=text(d.get("name"),"Name",100,True); email=text(d.get("email"),"Email",254,True).lower(); username=text(d.get("username"),"Username",40,True).lower(); password=text(d.get("password"),"Password",200,True)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): raise ApiError("Enter a valid email address.")
    if len(password)<10: raise ApiError("Use a password with at least 10 characters.")
    users=read("users")
    if any(u["email"]==email or u["username"]==username for u in users): raise ApiError("That email or username is already registered.",409,"account_exists")
    user={"id":"usr_"+uuid.uuid4().hex,"name":name,"email":email,"username":username,"password_hash":generate_password_hash(password),"created_at":datetime.now(timezone.utc).isoformat()}; users.append(user); write("users",users); session["user_id"]=user["id"]; session["csrf_token"]=secrets.token_urlsafe(32); session.permanent=True
    upsert("profiles",{"user_id":user["id"],"name":name,"email":email,"username":username,"skills":[],"target_role":"","experience":"","available_time":"1 hour","education":"","interests":""},"user_id")
    return jsonify(user=public(user)),201

@bp.post("/auth/login")
def login():
    d=request.get_json(silent=True) or {}; identity=text(d.get("identity"),"Email or username",254,True).lower(); password=text(d.get("password"),"Password",200,True)
    user=next((u for u in read("users") if identity in (u["email"],u["username"])),None)
    if not user or not check_password_hash(user["password_hash"],password): raise ApiError("Email/username or password is incorrect.",401,"invalid_credentials")
    session.clear(); session["user_id"]=user["id"]; session["csrf_token"]=secrets.token_urlsafe(32); session.permanent=True
    return jsonify(user=public(user))

@bp.post("/auth/logout")
def logout(): session.clear(); return jsonify(message="Signed out.")

@bp.get("/auth/me")
def me():
    u=next((u for u in read("users") if u["id"]==session.get("user_id")),None)
    if not u: raise ApiError("Please sign in to continue.",401,"unauthorized")
    return jsonify(user=public(u), csrf_token=session.get("csrf_token", ""))

def send_reset(email, token):
    host=os.getenv("SMTP_HOST"); username=os.getenv("SMTP_USERNAME"); password=os.getenv("SMTP_PASSWORD"); sender=os.getenv("SMTP_FROM")
    if not all((host,username,password,sender)): return False
    msg=EmailMessage(); msg["Subject"]="Reset your Career Intelligence password"; msg["From"]=sender; msg["To"]=email; msg.set_content(f"Use this one-time link to reset your password: {os.getenv('FRONTEND_URL','http://localhost:5500')}/pages/reset-password.html?token={token}\nThe link expires in 30 minutes.")
    with smtplib.SMTP(host,int(os.getenv("SMTP_PORT","587")),timeout=15) as smtp: smtp.starttls(); smtp.login(username,password); smtp.send_message(msg)
    return True

@bp.post("/auth/forgot-password")
def forgot():
    d=request.get_json(silent=True) or {}; email=text(d.get("email"),"Email",254,True).lower(); user=next((u for u in read("users") if u["email"]==email),None)
    result={"message":"If that account exists, password reset instructions will be sent."}
    if not user: return jsonify(result)
    token=secrets.token_urlsafe(32); tokens=read("password_reset_tokens"); tokens=[t for t in tokens if t["user_id"]!=user["id"]]; tokens.append({"user_id":user["id"],"token_hash":hashlib.sha256(token.encode()).hexdigest(),"expires_at":(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()}); write("password_reset_tokens",tokens)
    try: mailed=send_reset(email,token)
    except Exception:
        current_app.logger.exception("Password reset email delivery failed")
        mailed=False
    if not mailed and os.getenv("FLASK_DEBUG")=="1": result.update(dev_reset_token=token,delivery="Email is not configured; development-only reset token.")
    return jsonify(result)

@bp.post("/auth/reset-password")
def reset():
    d=request.get_json(silent=True) or {}; token=text(d.get("token"),"Reset token",200,True); password=text(d.get("password"),"Password",200,True)
    if len(password)<10: raise ApiError("Use a password with at least 10 characters.")
    hashed=hashlib.sha256(token.encode()).hexdigest(); tokens=read("password_reset_tokens"); entry=next((t for t in tokens if secrets.compare_digest(t["token_hash"],hashed)),None)
    if not entry or datetime.fromisoformat(entry["expires_at"])<datetime.now(timezone.utc): raise ApiError("This reset link is invalid or expired. Request a new one.",400,"reset_expired")
    users=read("users")
    for u in users:
        if u["id"]==entry["user_id"]: u["password_hash"]=generate_password_hash(password)
    write("users",users); write("password_reset_tokens",[t for t in tokens if t is not entry]); return jsonify(message="Password updated. You can now sign in.")
