from flask import Blueprint,request,jsonify
from utils.auth_utils import current_user_id,login_required
from utils.json_manager import user_rows,read,write
from utils.validators import text
from services.gemini_service import generate
from utils.error_handler import ApiError
import uuid,datetime
bp=Blueprint("interview",__name__)

def _fallback_question(role, mode, difficulty, followup=False):
 questions={
  "technical":{
   "beginner":f"For a {role} role, explain one programming concept you use often and give a simple example of when it is useful.",
   "intermediate":f"For a {role} role, describe how you would investigate a bug that appears only for some users. What would you check first, and why?",
   "advanced":f"For a {role} role, describe a technical design decision where you had to balance performance, maintainability, and delivery time. How would you evaluate the trade-offs?"},
  "behavioral":{
   "beginner":"Tell me about a time you worked with someone else to complete a task. What did you contribute?",
   "intermediate":"Describe a time a project did not go as planned. How did you respond, and what changed because of your actions?",
   "advanced":"Tell me about a time you had to influence a team through disagreement or uncertainty. How did you approach it, and what did you learn?"},
  "hr":{
   "beginner":f"What interests you about starting a career as a {role}, and what would you like to learn in your first role?",
   "intermediate":f"Why are you interested in this {role}, and which part of your experience best prepares you for it?",
   "advanced":f"What kind of work environment helps you do your best work, and how do you adapt when a team's expectations differ from your own?"},
  "mixed":{
   "beginner":f"Tell me about a project related to {role}. What were you trying to build, what part did you handle, and what did you learn?",
   "intermediate":f"Walk me through a project relevant to {role}: the problem, a technical choice you made, how you worked with others, and the outcome.",
   "advanced":f"Choose a project relevant to {role}. Explain the trade-offs behind a key technical decision, how you aligned with others, and how you measured the result."}}
 normalized_mode=str(mode or "mixed").strip().lower()
 normalized_mode="hr" if normalized_mode in {"hr","human resources"} else normalized_mode
 normalized_difficulty=str(difficulty or "beginner").strip().lower()
 if normalized_mode not in questions: normalized_mode="technical"
 if normalized_difficulty not in questions[normalized_mode]: normalized_difficulty="beginner"
 if followup:
  followups={"technical":f"For a {role} role, how would you test the approach you described, and what edge case would you check first?","behavioral":"Looking back on that situation, what would you do differently next time, and why?","hr":"Which strength would you bring to this role, and how have you demonstrated it in practice?","mixed":f"What was the biggest challenge in that {role} project, and what would you improve if you built it again?"}
  return followups[normalized_mode]
 return questions[normalized_mode][normalized_difficulty]

def _offline_feedback(answer, role, mode, difficulty):
 words=answer.split(); word_count=len(words); lower=answer.lower()
 score=35 if word_count<12 else 52 if word_count<28 else 66 if word_count<55 else 74
 if any(token in lower for token in ("because","so that","therefore","which meant")): score+=6
 if any(token in lower for token in ("result","improved","reduced","increased","learned","outcome")): score+=8
 if any(char.isdigit() for char in answer): score+=4
 score=min(score,88)
 strengths=[]
 if word_count>=20: strengths.append("You gave enough detail to explain your thinking.")
 if any(token in lower for token in ("because","therefore","so that")): strengths.append("You explained why you chose that approach.")
 if any(token in lower for token in ("result","improved","reduced","increased","learned","outcome")): strengths.append("You included an outcome or learning point.")
 if not strengths: strengths.append("You made a start by answering the question directly.")
 next_question=_fallback_question(role,mode,difficulty,followup=True)
 return {"score":score,"strengths":strengths,"improvement":"Add a specific example, explain the actions you took, and finish with the result or what you learned.","suggested_structure":"Use context → your responsibility → actions you took → result and reflection.","next_question":next_question,"ai_status":"Gemini is temporarily rate-limited. This practice estimate is based on answer detail and is not an AI evaluation."}

def _can_use_fallback(error):
 return error.code in {"ai_not_configured","ai_rate_limited","ai_unavailable","ai_timeout"}

@bp.post("/interview/start")
@login_required
def start():
 d=request.get_json(silent=True) or {}; p=(user_rows("profiles",current_user_id()) or [{}])[0]; role=(d.get("target_role") or p.get("target_role") or "your target role").strip(); mode=d.get("type","mixed"); difficulty=d.get("difficulty","beginner")
 try: result=generate("You are conducting the user's selected interview round. Ask one concise first question that clearly fits the selected interview type and difficulty, and stays focused on the target role. Do not switch to another interview round. Return JSON keys question, evaluation_criteria.",{"role":role,"type":mode,"difficulty":difficulty})
 except ApiError as e:
  if not _can_use_fallback(e): raise
  result={"question":_fallback_question(role,mode,difficulty),"evaluation_criteria":["clear context","your contribution","specific outcome"],"ai_status":"Gemini is temporarily unavailable. This built-in question keeps your selected round moving; AI-generated questions will return when the service recovers."}
 item={"id":"int_"+uuid.uuid4().hex,"user_id":current_user_id(),"role":role,"type":mode,"difficulty":difficulty,"question":result.get("question"),"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}; rows=read("interviews"); rows.append(item); write("interviews",rows); return jsonify(session=item,criteria=result.get("evaluation_criteria",[]),ai_status=result.get("ai_status"))
@bp.post("/interview/answer")
@login_required
def answer():
 d=request.get_json(silent=True) or {}; ans=text(d.get("answer"),"Answer",6000,True); q=text(d.get("question"),"Question",1000,True)
 mode=text(d.get("type","mixed"),"Interview round",30,True); difficulty=text(d.get("difficulty","beginner"),"Difficulty",30,True); role=text(d.get("role","your target role"),"Target role",120,True)
 try: result=generate("Evaluate the answer for the user's selected interview round and difficulty. Keep the next_question within that same interview round, at the same difficulty, and focused on the same target role. Return JSON keys score (0-100), strengths (array), improvement, suggested_structure, next_question. Be constructive and specific.",{"question":q,"answer":ans,"type":mode,"difficulty":difficulty,"role":role})
 except ApiError as e:
  if not _can_use_fallback(e): raise
  result=_offline_feedback(ans,role,mode,difficulty)
 rows=read("interviews"); rows.append({"user_id":current_user_id(),"question":q,"answer":ans,"evaluation":result}); write("interviews",rows); return jsonify(result=result)
