def fallback_plan(role, skills, time):
    skills=skills or []; gaps=[x for x in ["REST APIs","Git","SQL","Testing","Deployment"] if x.lower() not in [s.lower() for s in skills]]
    label=str(time).lower()
    minutes=30 if "30" in label else 180 if "3" in label else 120 if "2" in label else 60
    practices={30:"Review one focused concept, then do a 10-minute recall or micro-exercise.",60:"Study the concept, complete a guided exercise, and write down one question.",120:"Study the concept, implement a practical exercise, then test and reflect on the result.",180:"Study deeply, complete a practical exercise, extend a small project, and review the result."}
    days=[]
    for i in range(1,31):
        topic=gaps[(i-1)//3 % len(gaps)] if gaps else (skills[(i-1)%len(skills)] if skills else "Role fundamentals")
        days.append({"day":i,"topic":topic,"why":f"Build job-relevant capability for {role}.","objective":f"Understand and apply {topic}.","practice":practices[minutes],"estimated_minutes":minutes,"resources":[]})
    return {"summary":f"A starter roadmap toward {role}; tailor it as you learn.","strengths":skills[:5],"skill_gaps":gaps[:5],"plan":days,"next_action":f"Start with {days[0]['topic']} fundamentals.","disclaimer":"Starter plan generated locally. Configure Gemini for personalized AI planning."}
