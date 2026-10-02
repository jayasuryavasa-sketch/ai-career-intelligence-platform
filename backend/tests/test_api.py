import os, tempfile, unittest

_data = tempfile.TemporaryDirectory()
os.environ["DATA_DIR"] = _data.name
os.environ["SECRET_KEY"] = "test-secret-not-for-production"
os.environ["FRONTEND_URL"] = "http://localhost:5500"
os.environ.pop("GEMINI_API_KEY", None)

from app import app
from utils.json_manager import write
from services.ats_service import score_resume
from services.local_career import fallback_plan

class PlatformApiTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        for name in ("users", "profiles", "career_plans", "resumes", "skill_gaps", "applications", "password_reset_tokens", "interviews"):
            write(name, [])

    def secured(self, method, path, **kwargs):
        auth=self.client.get("/api/auth/me").json
        headers={**kwargs.pop("headers",{}),"X-CSRF-Token":auth["csrf_token"]}
        return self.client.open(path,method=method,headers=headers,**kwargs)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["status"], "ok")

    def test_register_login_and_profile_scope(self):
        res = self.client.post("/api/auth/register", json={"name":"A User", "email":"a@example.com", "username":"alpha", "password":"correct horse battery"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.client.get("/api/profile").status_code, 200)
        self.secured("POST","/api/auth/logout")
        self.assertEqual(self.client.get("/api/profile").status_code, 401)
        res = self.client.post("/api/auth/login", json={"identity":"alpha", "password":"correct horse battery"})
        self.assertEqual(res.status_code, 200)

    def test_passwords_are_hashed(self):
        self.client.post("/api/auth/register", json={"name":"A User", "email":"b@example.com", "username":"beta", "password":"correct horse battery"})
        from utils.json_manager import read
        self.assertNotEqual(read("users")[0]["password_hash"], "correct horse battery")

    def test_ats_is_deterministic_and_role_sensitive(self):
        resume="Alex Doe alex@example.com\nExperience\nBuilt Python REST APIs and improved latency 30%.\nEducation\nSkills\nPython, Flask, SQL\nProjects"
        first=score_resume(resume,"Python Developer",["Python","Flask"])
        self.assertEqual(first, score_resume(resume,"Python Developer",["Python","Flask"]))
        self.assertNotEqual(first["score"], score_resume(resume,"Cloud Architect",["Kubernetes","AWS"])['score'])

    def test_local_plan_adapts_workload_to_daily_time(self):
        short=fallback_plan("Developer",[],"30 minutes")['plan'][0]
        medium=fallback_plan("Developer",[],"1 hour")['plan'][0]
        deep=fallback_plan("Developer",[],"3+ hours")['plan'][0]
        self.assertEqual((short['estimated_minutes'],medium['estimated_minutes'],deep['estimated_minutes']),(30,60,180))
        self.assertNotEqual(short['practice'],deep['practice'])

    def test_skill_analysis_requires_session_then_succeeds(self):
        self.assertEqual(self.client.post("/api/skills/analyze", json={}).status_code,401)
        self.client.post("/api/auth/register", json={"name":"A User", "email":"c@example.com", "username":"gamma", "password":"correct horse battery"})
        res=self.secured("POST","/api/skills/analyze", json={"target_role":"Backend developer", "skills":["Python"]})
        self.assertEqual(res.status_code,200)
        self.assertTrue(res.json["result"]["missing_skills"])

    def test_unsupported_resume_extension_rejected(self):
        import io
        self.client.post("/api/auth/register", json={"name":"A User", "email":"d@example.com", "username":"delta", "password":"correct horse battery"})
        res=self.secured("POST","/api/resume/analyze", data={"file":(io.BytesIO(b"nope"),"resume.exe")}, content_type="multipart/form-data")
        self.assertEqual(res.status_code,400)

    def test_password_reset_is_one_time(self):
        import hashlib
        self.client.post("/api/auth/register", json={"name":"A User", "email":"reset@example.com", "username":"resetter", "password":"correct horse battery"})
        from utils.json_manager import read,write
        user=read("users")[0]
        raw="single-use-reset-token"
        from datetime import datetime,timedelta,timezone
        write("password_reset_tokens",[{"user_id":user["id"],"token_hash":hashlib.sha256(raw.encode()).hexdigest(),"expires_at":(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()}])
        res=self.client.post("/api/auth/reset-password",json={"token":raw,"password":"a-new-safe-password"})
        self.assertEqual(res.status_code,200)
        self.assertEqual(self.client.post("/api/auth/reset-password",json={"token":raw,"password":"another-safe-password"}).status_code,400)

    def test_user_cannot_read_another_users_application(self):
        self.client.post("/api/auth/register", json={"name":"A User", "email":"one@example.com", "username":"one", "password":"correct horse battery"})
        created=self.secured("POST","/api/applications",json={"company":"Example","role":"Analyst"})
        self.assertEqual(created.status_code,201)
        app_id=created.json["item"]["id"]
        self.secured("POST","/api/auth/logout")
        self.client.post("/api/auth/register", json={"name":"B User", "email":"two@example.com", "username":"two", "password":"correct horse battery"})
        self.assertEqual(self.secured("PUT",f"/api/applications/{app_id}",json={"status":"Offer"}).status_code,404)

    def test_cookie_session_mutations_require_csrf(self):
        self.client.post("/api/auth/register", json={"name":"A User", "email":"csrf@example.com", "username":"csrf", "password":"correct horse battery"})
        self.assertEqual(self.client.post("/api/auth/logout").status_code,403)

    def test_feature_flow_without_optional_gemini(self):
        import io
        self.client.post("/api/auth/register", json={"name":"A User", "email":"flow@example.com", "username":"flow", "password":"correct horse battery"})
        profile=self.secured("PUT","/api/profile",json={"target_role":"Python developer","skills":["Python","SQL"],"available_time":"1 hour"})
        self.assertEqual(profile.status_code,200)
        self.assertEqual(self.secured("POST","/api/career/plan",json={}).status_code,200)
        self.assertEqual(self.client.get("/api/career/plan").status_code,200)
        resume=self.secured("POST","/api/resume/analyze",data={"target_role":"Python developer","file":(io.BytesIO(b"Alex alex@example.com\nExperience\nBuilt Python API\nEducation\nSkills\nPython SQL"),"resume.txt")},content_type="multipart/form-data")
        self.assertEqual(resume.status_code,200)
        self.assertIn("score",resume.json["result"]["ats"])
        self.assertEqual(self.client.get("/api/resume/history").status_code,200)
        self.assertEqual(self.secured("POST","/api/jobs/match",json={}).status_code,200)
        jd=self.secured("POST","/api/jobs/analyze-description",json={"description":"Python developer with SQL and API experience"})
        self.assertEqual(jd.status_code,200)
        self.assertEqual(self.secured("POST","/api/projects/recommend",json={}).status_code,200)
        interview=self.secured("POST","/api/interview/start",json={})
        self.assertEqual(interview.status_code,200)
        self.assertEqual(self.secured("POST","/api/interview/answer",json={"question":interview.json["session"]["question"],"answer":"I built an example API and tested it."}).status_code,200)
        app=self.secured("POST","/api/applications",json={"company":"Example Co","role":"Developer"})
        self.assertEqual(app.status_code,201)
        self.assertEqual(self.client.get("/api/applications").status_code,200)
        self.assertEqual(self.client.get("/api/progress").status_code,200)
        self.assertEqual(self.secured("POST","/api/assistant/message",json={"message":"What should I focus on?"}).status_code,503)

if __name__ == "__main__": unittest.main()
