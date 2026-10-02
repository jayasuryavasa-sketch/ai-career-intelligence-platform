from routes.auth_routes import bp as auth_bp
from routes.profile_routes import bp as profile_bp
from routes.career_routes import bp as career_bp
from routes.skill_routes import bp as skill_bp
from routes.resume_routes import bp as resume_bp
from routes.job_routes import bp as job_bp
from routes.project_routes import bp as project_bp
from routes.interview_routes import bp as interview_bp
from routes.application_routes import bp as application_bp
from routes.progress_routes import bp as progress_bp
from routes.assistant_routes import bp as assistant_bp

def register_blueprints(app):
    for bp in (auth_bp, profile_bp, career_bp, skill_bp, resume_bp, job_bp, project_bp, interview_bp, application_bp, progress_bp, assistant_bp): app.register_blueprint(bp, url_prefix="/api")
