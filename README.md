# AI Career Intelligence Platform

A career planning workspace with profile-aware planning, deterministic resume scoring, skill comparison, project directions, job description analysis, interview practice, application tracking and progress views. The frontend is static HTML/CSS/vanilla JavaScript; the REST API is Flask. User records live in user-scoped JSON files.

## What works

- Account registration, sign-in/out, hashed passwords, expiring one-use password reset tokens and optional SMTP delivery.
- Profile reused across modules, 30-day starter roadmap, role skill comparison and transparent readiness simulation.
- In-memory PDF/DOCX/TXT extraction with a deterministic weighted ATS estimate and resume version history.
- Job description keyword comparison, non-live role direction suggestions linking to established job portals, and project recommendations.
- Interview question flow; Gemini-based evaluation when configured, with an honest note when unavailable.
- Application create/update/delete, status pipeline, progress dashboard and mobile navigation.
- Responsive dark glass interface with an animated CSS AI guide illustration and reduced reliance on heavy graphics.

Gemini-dependent personalization reports a distinct configuration/service error when Gemini is unavailable. Career plans, skill comparison, project suggestions and interview prompts include useful local fallback behavior. Job role suggestions are not represented as live vacancies, and no third-party job URLs are invented.

## Structure

```text
frontend/                 Static Vercel site
  index.html
  pages/                  Login, registration and product modules
  css/main.css
  js/config.js            Central API base configuration
  js/api.js               Centralized fetch, errors, timeout, credentials
  js/auth.js
  js/app.js
backend/                  Flask API for Render
  app.py
  routes/                 REST blueprints by feature
  services/               Gemini, ATS and local career plan services
  utils/                  JSON persistence, validation, auth and document parsing
  data/                   JSON files created as needed
  uploads/                Reserved; uploaded resumes are not retained
```

## Local setup

Use Python 3.10+ and serve the static frontend from a local HTTP server (do not open HTML with `file://`).

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py app.py
```

In another terminal, serve `frontend/` on port 5500, for example with VS Code Live Server. Visit `http://127.0.0.1:5500/`. Edit `backend/.env` and set a random `SECRET_KEY`; add a Gemini key to enable personalized AI responses. Restart the backend after environment changes. Local data files are created automatically in `backend/data/`.

For development password recovery, set `FLASK_DEBUG=1`; without SMTP, the API returns a development-only one-time token. Production responses never include reset tokens. Configure all SMTP variables to deliver reset emails.

## Configuration

`backend/.env.example` documents:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask session signing key; use a strong unique secret in production |
| `GEMINI_API_KEY` | Server-only Google Gemini API credential |
| `GEMINI_MODEL` | Gemini model identifier |
| `GEMINI_FALLBACK_MODELS` | Comma-separated fallback model IDs used on rate limits, temporary provider failures, unavailable models, or unusable responses |
| `FRONTEND_URL` | Allowed frontend origin; comma-separated origins are supported |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | Optional password reset email delivery |
| `DATA_DIR` | JSON data directory; defaults to `backend/data` |


The frontend API base defaults to `http://127.0.0.1:5000/api`. Before deploying, edit `frontend/js/config.js` and set `window.CAREER_API_URL` to your Render HTTPS API origin plus `/api`. Never place provider secrets in frontend code.

## API overview

All application APIs are rooted at `/api`. Authenticated routes use an HTTP-only Flask session cookie and send credentials with CORS.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Service health and AI configured status |
| POST | `/auth/register`, `/auth/login`, `/auth/logout` | Account lifecycle |
| POST | `/auth/forgot-password`, `/auth/reset-password` | One-use, 30-minute password reset |
| GET/PUT | `/profile` | Current user's career profile |
| GET/POST | `/career/plan` | Read or generate an adaptive career plan |
| POST/GET | `/skills/analyze`, `/skills/gaps` | Skill comparison |
| POST/GET | `/resume/analyze`, `/resume/history` | Document analysis and evolution |
| POST | `/jobs/match`, `/jobs/analyze-description` | Role direction and JD comparison |
| POST | `/projects/recommend` | Project directions |
| POST | `/interview/start`, `/interview/answer` | Interview question and answer evaluation |
| POST | `/assistant/message` | Career Q&A grounded in the signed-in user's saved context |
| GET/POST/PUT/DELETE | `/applications` | User's application tracker |
| GET | `/progress` | User-scoped career progress |

JSON errors use `{ "error": { "code": "...", "message": "..." } }`. The API validates inputs and uses `user_id` scoping for records. The JSON store uses atomic replacement and a process lock; it is intended for a small single-instance project, not high-concurrency or multi-instance production workloads.

## Resume scoring

ATS scoring is reproducible and computed in Python from target-role/profile keyword overlap, sections, contact details, experience evidence, education, certifications and formatting heuristics. Gemini may explain findings; it does not set the numeric score. It is an estimate, not a guarantee of how any applicant tracking system will rank a resume. Uploaded files are size/extension checked and parsed in memory; the app does not retain their bytes.

## Deployment

### Render backend

Deploy the `backend/` directory as the Render root (or use `backend/render.yaml`). Set `SECRET_KEY`, `FRONTEND_URL`, `GEMINI_API_KEY` and optional SMTP values. The included blueprint attaches a persistent disk at `/var/data` for JSON files. The Flask cookie is HTTP-only; HTTPS deployments use secure, cross-site cookies. Configure Render's allowed-origin value to your exact Vercel origin.

### Vercel frontend

Import the repository and set the project root to `frontend/`. Configure the API base as described above, using the deployed Render HTTPS origin. The static site has no build step. Configure the matching Render `FRONTEND_URL` origin. Both services must use HTTPS in production for session cookies.

## Security and limitations

- Passwords use Werkzeug's password hashing; session cookies are HTTP-only and use secure flags on HTTPS deployments. Mutating authenticated requests also require a per-session CSRF token.
- Gemini and SMTP secrets remain in backend environment variables; reset tokens are hashed at rest and expire after 30 minutes.
- CORS is limited to configured frontend origins; request fields, upload size and extensions are validated.
- JSON flat files do not provide database-grade transactions, multi-process locking, backups or horizontal scaling. Render persistent disk is required to retain data across restarts.
- SMTP is optional but required for real password recovery outside development mode. Gemini requires a configured API key. Third-party services can change their limits and availability.
- The front end is a static site and the API uses cookie sessions. Set the API URL before app scripts load; do not use wildcard CORS.

## Verification

Run the backend checks from `backend/`:

```powershell
py -m unittest discover -s tests -v
py -m compileall app.py routes services utils
```

The checks cover health, registration/login/session isolation, profile persistence, deterministic ATS scoring, authenticated skill analysis and invalid resume types. Manual deployment smoke checks should additionally cover SMTP delivery, Gemini's configured and unavailable cases, and a real browser at desktop and mobile widths.

## Deploy from GitHub

The repository root includes a Render Blueprint (`render.yaml`) and a Vercel config under `frontend/`.

1. Push the project to a GitHub repository.
2. In Render, create a Blueprint from that repository using the root `render.yaml`. It sets the service root to `backend/`, configures the health check, and mounts persistent data at `/var/data`.
3. In Vercel, import the same repository and set the project root directory to `frontend/`. The site is static and needs no build command.
4. After both providers create their public URLs, set `FRONTEND_URL` in Render to the exact Vercel site origin. Set the API base in `frontend/js/config.js` to the Render service URL followed by `/api`, then redeploy Vercel.
5. `GEMINI_API_KEY` is optional; without it, the API uses the app's local fallback responses. Add it in Render's environment settings if you want Gemini responses. Do not commit `.env` files or API keys.

The API's persistent disk is defined in the Render Blueprint. Confirm the selected Render plan supports that disk before creating the service.
