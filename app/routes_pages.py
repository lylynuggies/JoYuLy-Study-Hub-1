from __future__ import annotations

import re
from datetime import timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .db import attempts, save_users, users
from .security import me, must
from .services import concept_rows
from .ui import render

router = APIRouter()


def _title_words(s: str) -> str:
    words = [w for w in re.split(r"\s+", (s or "").strip()) if w]
    return " ".join(x[:1].upper() + x[1:].lower() for x in words)


def _welcome_name(u: dict) -> str:
    fn = _title_words(str(u.get("firstName", "")))
    ln = _title_words(str(u.get("lastName", "")))
    full = _title_words(str(u.get("name", "")))
    candidate = (f"{fn} {ln}".strip() if (fn or ln) else full) or "Student"
    if len(candidate) > 20 and fn:
        return fn
    return candidate


@router.get("/")
def home(request: Request):
    if me(request):
        return RedirectResponse("/dashboard", 303)
    return RedirectResponse("/auth", 303)


@router.get("/profile")
def profile(request: Request):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    return render(request, "profile.html", "Profile", user=u)


@router.post("/profile")
def profile_save(
    request: Request,
    firstName: str = Form(""),
    lastName: str = Form(""),
    name: str = Form(...),
    school: str = Form(""),
    grade: str = Form(""),
    bio: str = Form(""),
    theme: str = Form("light"),
):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    rows = users()
    for i, x in enumerate(rows):
        if x.get("id") == u["id"]:
            fn = firstName.strip()
            ln = lastName.strip()
            full = (f"{fn} {ln}".strip() if (fn or ln) else (name.strip() or x.get("name")))
            x.update(
                {
                    "firstName": fn,
                    "lastName": ln,
                    "name": full,
                    "school": school.strip(),
                    "grade": grade.strip(),
                    "bio": bio.strip(),
                    "theme": theme if theme in {"light", "dark", "ocean"} else "light",
                }
            )
            rows[i] = x
    save_users(rows)
    return RedirectResponse("/profile", 303)


@router.get("/dashboard")
def dashboard(request: Request):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u

    mine = [a for a in attempts() if a.get("user_id") == u["id"]]
    mine.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
    rows = concept_rows([q for a in mine for q in a.get("question_rows", []) if q.get("attempted")])
    by_subject = {}
    for r in rows:
        s = r.get("subject", "General")
        c = by_subject.setdefault(s, {"subject": s, "scored": 0.0, "possible": 0.0, "attempted": 0, "avg_predicted_seconds": 0.0})
        c["scored"] += float(r.get("scored", 0.0))
        c["possible"] += float(r.get("possible", 0.0))
        c["attempted"] += int(r.get("attempted", 0))
        c["avg_predicted_seconds"] += float(r.get("predicted_seconds", 0.0)) * int(r.get("attempted", 0))
    subject_rows = []
    for c in by_subject.values():
        mastery = round(100.0 * c["scored"] / max(1.0, c["possible"]), 2)
        avg_sec = int(c["avg_predicted_seconds"] / max(1, c["attempted"]))
        subject_rows.append({"subject": c["subject"], "mastery_pct": mastery, "avg_predicted_seconds": avg_sec, "attempted": c["attempted"]})
    top = sorted(subject_rows, key=lambda z: z["mastery_pct"], reverse=True)[:3]
    low = sorted(subject_rows, key=lambda z: z["mastery_pct"])[:3]

    end = __import__("datetime").datetime.utcnow().date()
    start = end - timedelta(days=6)
    wd = [0.0] * 7
    for a in mine:
        if not a.get("started_at"):
            continue
        d = __import__("datetime").datetime.fromisoformat(a["started_at"])
        if start <= d.date() <= end:
            wd[d.weekday()] += float(a.get("duration_seconds", 0)) / 3600.0

    chart = {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "values": [round(v, 2) for v in wd]}
    return render(
        request,
        "dashboard.html",
        "Dashboard",
        user=u,
        welcome_name=_welcome_name(u),
        weekly_total=round(sum(wd), 2),
        chart=chart,
        top=top,
        low=low,
        recent=mine[:8],
    )


@router.get("/subjects")
def subjects(request: Request):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    mine = [a for a in attempts() if a.get("user_id") == u["id"]]
    mine.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
    rows = concept_rows([q for a in mine for q in a.get("question_rows", []) if q.get("attempted")])
    by_subject = {}
    for r in rows:
        s = r.get("subject", "General")
        c = by_subject.setdefault(s, {"subject": s, "scored": 0.0, "possible": 0.0, "attempted": 0, "concepts": 0, "time_total": 0})
        c["scored"] += float(r.get("scored", 0.0))
        c["possible"] += float(r.get("possible", 0.0))
        c["attempted"] += int(r.get("attempted", 0))
        c["concepts"] += 1
        c["time_total"] += int(r.get("predicted_seconds", 0))
    subject_stats = []
    for c in by_subject.values():
        mastery = round(100.0 * c["scored"] / max(1.0, c["possible"]), 2)
        avg_pred_time = int(c["time_total"] / max(1, c["concepts"]))
        total_hours = round(sum(float(a.get("duration_seconds", 0)) / 3600.0 for a in mine if a.get("subject") == c["subject"]), 2)
        avg_score = round(sum(float(a.get("overall_pct", 0)) for a in mine if a.get("subject") == c["subject"]) / max(1, len([a for a in mine if a.get("subject") == c["subject"]])), 2)
        subject_stats.append(
            {
                "subject": c["subject"],
                "mastery_pct": mastery,
                "attempted": c["attempted"],
                "concept_count": c["concepts"],
                "avg_pred_time": avg_pred_time,
                "total_hours": total_hours,
                "avg_score": avg_score,
            }
        )
    subject_stats.sort(key=lambda x: x["mastery_pct"], reverse=True)
    return render(request, "subjects.html", "Subjects", subject_stats=subject_stats)
