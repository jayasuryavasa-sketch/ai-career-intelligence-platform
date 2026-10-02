import re

SECTIONS = {"experience": r"experience|employment|work history", "education": r"education|academic", "skills": r"skills|technical skills|competencies", "projects": r"projects|portfolio", "certifications": r"certifications|certificates|licenses"}
CONTACT = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:\+?\d[\d ()-]{7,}\d)|linkedin\.com", re.I)

def score_resume(body, role="", skills=None):
    body = body or ""
    low = body.lower()
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.]{1,}", body)
    role_terms = [w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", role) if len(w) > 3]
    terms = list(dict.fromkeys([*(skills or []), *role_terms]))
    keyword = round(100 * sum(1 for t in terms if t.lower() in low) / max(len(terms), 1)) if terms else min(70, len(words)//5)
    section = round(100 * sum(1 for p in SECTIONS.values() if re.search(p, low)) / len(SECTIONS))
    contact = 100 if CONTACT.search(body) else 25
    quantified = len(re.findall(r"\b\d+\s*(?:%|\+|x|users|clients|projects|hours|days|k)\b", low))
    experience = min(100, 35 + quantified * 13 + min(len(re.findall(r"\b(?:built|led|improved|created|developed|managed|reduced|increased)\b", low)), 4)*8)
    formatting = max(35, min(100, 100 - max(0, len(body.splitlines()) - 90)//3 - (20 if "  " in body else 0)))
    education = 90 if re.search(SECTIONS["education"], low) else 30
    certs = 85 if re.search(SECTIONS["certifications"], low) else 55
    parts = {"keyword_match": keyword, "skills_match": keyword, "section_structure": section, "contact_information": contact, "experience_relevance": experience, "education": education, "certifications": certs, "formatting": formatting}
    weights = {"keyword_match": .2, "skills_match": .18, "section_structure": .16, "contact_information": .1, "experience_relevance": .16, "education": .08, "certifications": .04, "formatting": .08}
    return {"score": round(sum(parts[k]*w for k,w in weights.items())), "breakdown": parts, "matched_keywords": [t for t in terms if t.lower() in low], "missing_keywords": [t for t in terms if t.lower() not in low], "word_count": len(words), "disclaimer": "A consistent heuristic estimate, not a guarantee of an ATS result."}
