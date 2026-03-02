from __future__ import annotations

import json
import re
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .db import attempts, exams, save_exams
from .security import must, now
from .services import grouped_concept_rows, predict, regression_hours_needed, split_concepts
from .state import ai
from .ui import render

router = APIRouter()


def _ai_generate_recap_mcq(subject: str, topics: list[str], weak: list[dict], n: int = 5) -> list[dict]:
    if not ai:
        return []
    weak_topics = [w.get("concept", "") for w in weak[:6] if w.get("concept")]
    pool = [t for t in topics if t] or weak_topics or [subject]
    try:
        prompt = (
            "Generate strict JSON array only (no markdown). "
            "Create 5 concept-check MCQs for a student. "
            "Each item must be: "
            '{"qid":"R1","title":"Recap Question 1","prompt":"...","options":[{"label":"A","text":"..."},{"label":"B","text":"..."},{"label":"C","text":"..."},{"label":"D","text":"..."}],"answer":"A","explanation":"..."} '
            f"Subject: {subject}. Focus topics: {', '.join(pool[:8])}. "
            f"Weaker concepts to prioritize: {', '.join(weak_topics[:6]) or 'N/A'}."
        )
        resp = ai.responses.create(model="gpt-4.1-mini", input=prompt)
        raw = getattr(resp, "output_text", "")
        m = re.search(r"\[.*\]", raw, re.S)
        arr = json.loads(m.group(0)) if m else []
        out = []
        for i, q in enumerate(arr[:n], 1):
            opts = q.get("options", []) if isinstance(q.get("options", []), list) else []
            if len(opts) != 4:
                continue
            clean_opts = []
            for j, o in enumerate(opts):
                label = str(o.get("label", "")).strip().upper() or ["A", "B", "C", "D"][j]
                text = str(o.get("text", "")).strip()
                clean_opts.append({"label": label, "text": text, "value": label})
            ans = str(q.get("answer", "A")).strip().upper()
            if ans not in {"A", "B", "C", "D"}:
                ans = "A"
            out.append(
                {
                    "qid": f"R{i}",
                    "type": "mcq",
                    "title": str(q.get("title", f"Recap Question {i}")),
                    "prompt": str(q.get("prompt", "")),
                    "options": clean_opts,
                    "answer": ans,
                    "explanation": str(q.get("explanation", "")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/study-plan")
def study_plan(request: Request):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    today = now().date()
    ex = []
    for e in exams():
        if e.get("user_id") != u["id"]:
            continue
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        left = (d - today).days
        if left >= 0:
            ex.append({**e, "days_left": left, "within_14": left <= 14})
    ex.sort(key=lambda x: x["days_left"])
    all_attempts = [a for a in attempts() if a.get("user_id") == u["id"]]
    mastery = grouped_concept_rows([q for a in all_attempts for q in a.get("question_rows", []) if q.get("attempted")])

    plans = []
    for e in [x for x in ex if x["within_14"]]:
        rows = [m for m in mastery if m["subject"] == e["subject"]]
        topics = [t.strip() for t in e.get("topics", []) if t.strip()]
        if topics:
            rows2 = [m for m in rows if any(t.lower() in m["concept"].lower() for t in topics)]
            rows = rows2 or rows
        pri = sorted(rows, key=lambda z: z["mastery_pct"])[:6]
        strg = sorted(rows, key=lambda z: z["mastery_pct"], reverse=True)[:3]
        hrs = round(sum(max(0.75, max(0.0, (85 - x["mastery_pct"]) / 20.0)) for x in pri), 1) if pri else 0
        hrs_to_70 = regression_hours_needed(u["id"], e["subject"], target_pct=70.0)
        tracked_hours = round(sum(float(a.get("duration_seconds", 0)) / 3600.0 for a in all_attempts if a.get("subject") == e["subject"]), 1)
        on_track = (hrs_to_70 is not None and tracked_hours >= hrs_to_70) or (hrs_to_70 is None and (predict(u["id"], e["subject"]) or 0) >= 70)
        plans.append({"exam": e, "pri": pri, "strg": strg, "hrs": hrs, "pred": predict(u["id"], e["subject"]), "hrs_to_70": hrs_to_70, "tracked_hours": tracked_hours, "on_track": on_track})

    return render(request, "study_plan.html", "Study Plan", exams_list=ex, plans=plans)


@router.post("/study-plan/generate")
def generate_practice(request: Request, exam_id: str = Form(...), mode: str = Form(...)):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    ex = next((e for e in exams() if e.get("exam_id") == exam_id and e.get("user_id") == u["id"]), None)
    if not ex:
        return RedirectResponse("/study-plan", 303)
    all_attempts = [a for a in attempts() if a.get("user_id") == u["id"] and a.get("subject") == ex.get("subject")]
    qrows = [q for a in all_attempts for q in a.get("question_rows", []) if q.get("attempted")]
    subject_concepts = grouped_concept_rows(qrows)
    weak = sorted(subject_concepts, key=lambda x: x.get("mastery_pct", 0.0))
    strong = sorted(subject_concepts, key=lambda x: x.get("mastery_pct", 0.0), reverse=True)
    exam_topics = []
    for t in ex.get("topics", []):
        exam_topics.extend(split_concepts(t))
    exam_topics = [x for i, x in enumerate(exam_topics) if x and x.lower() not in {y.lower() for y in exam_topics[:i]}]
    topic_pool = exam_topics or [x["concept"] for x in weak[:5]] or [ex.get("subject", "General Concepts")]

    questions = []
    if mode == "tutorial":
        questions = [
            {
                "qid": "T1",
                "type": "open",
                "title": "Tutorial / Exam Practice Question 1",
                "prompt": f"{topic_pool[0]}: A particle moves in a curved path where radius of curvature changes with time. Derive required acceleration components, compute numerical values from given data, and justify assumptions used.",
                "hint": "Show full workings, units, and final numeric answer.",
            },
            {
                "qid": "T2",
                "type": "open",
                "title": "Tutorial / Exam Practice Question 2",
                "prompt": f"{topic_pool[min(1, len(topic_pool)-1)]}: Model a real scenario (vehicle/robot/projectile). Build equations, solve for unknowns, and evaluate if the result is physically realistic.",
                "hint": "Include setup, method, and final conclusion.",
            },
        ]
    else:
        questions = _ai_generate_recap_mcq(ex.get("subject", "General"), topic_pool, weak, n=5)
        if not questions:
            labels = ["A", "B", "C", "D"]
            for i in range(1, 6):
                t = topic_pool[(i - 1) % len(topic_pool)]
                correct_idx = (i + 1) % 4
                opts = [
                    f"{t}: option about formula interpretation",
                    f"{t}: option about sign/direction convention",
                    f"{t}: option about unit consistency",
                    f"{t}: option about limiting case behavior",
                ]
                questions.append(
                    {
                        "qid": f"R{i}",
                        "type": "mcq",
                        "title": f"Recap Question {i}",
                        "prompt": f"{t}: choose the best statement for a quick concept check.",
                        "options": [{"label": labels[k], "text": opts[k], "value": labels[k]} for k in range(4)],
                        "answer": labels[correct_idx],
                        "explanation": f"Best choice checks core understanding in {t}.",
                    }
                )
    return render(
        request,
        "practice_questions.html",
        "Practice Generator",
        exam=ex,
        mode=mode,
        questions=questions,
        weak_concepts=weak[:6],
        strong_concepts=strong[:6],
    )


@router.post("/study-plan/exams")
def exam_add(request: Request, subject: str = Form(...), title: str = Form(...), date: str = Form(...), topics: str = Form("")):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse({"error": "Date must be YYYY-MM-DD"}, 400)
    ex = exams()
    ex.append({"exam_id": __import__("secrets").token_hex(6), "user_id": u["id"], "subject": subject.strip(), "title": title.strip(), "date": date, "topics": [x.strip() for x in topics.split(",") if x.strip()], "created_at": now().isoformat()})
    save_exams(ex)
    return RedirectResponse("/study-plan", 303)


@router.post("/study-plan/exams/{exam_id}/edit")
def exam_edit(request: Request, exam_id: str, subject: str = Form(...), title: str = Form(...), date: str = Form(...), topics: str = Form("")):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse({"error": "Date must be YYYY-MM-DD"}, 400)
    ex = exams()
    for i, e in enumerate(ex):
        if e.get("exam_id") == exam_id and e.get("user_id") == u["id"]:
            e.update({"subject": subject.strip(), "title": title.strip(), "date": date, "topics": [x.strip() for x in topics.split(",") if x.strip()]})
            ex[i] = e
    save_exams(ex)
    return RedirectResponse("/study-plan", 303)


@router.post("/study-plan/exams/{exam_id}/delete")
def exam_delete(request: Request, exam_id: str):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    save_exams([e for e in exams() if not (e.get("exam_id") == exam_id and e.get("user_id") == u["id"])])
    return RedirectResponse("/study-plan", 303)
