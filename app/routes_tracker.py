from __future__ import annotations

import csv
import io
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse

from .db import attempts, delete_bank, get_bank, list_banks_for_user, save_attempts, save_bank
from .firebase_backend import upload_bytes
from .security import must, now, slug
from .services import (
    ai_questions_from_text,
    concept_rows,
    extract_text_from_file,
    grade,
    infer_paper_title,
    parse_questions,
    predict,
)
from .state import pd
from .ui import render

router = APIRouter()


@router.get("/study-tracker")
def tracker(request: Request):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    banks = list_banks_for_user(u["id"])
    bank_cards = [
        {
            "subject": x.get("subject", ""),
            "title": x.get("title", ""),
            "questions": len(x.get("questions", [])),
            "bank_id": x.get("bank_id", ""),
        }
        for x in banks
    ]
    recent_attempts = [a for a in attempts() if a.get("user_id") == u["id"]]
    recent_attempts.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)

    def hhmmss(seconds: int) -> str:
        s = max(0, int(seconds or 0))
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"

    session_rows = [
        {
            "subject": a.get("subject", "General"),
            "duration": hhmmss(int(a.get("duration_seconds", 0))),
        }
        for a in recent_attempts[:8]
    ]

    return render(request, "study_tracker.html", "Study Tracker", banks=bank_cards, sessions=session_rows)


@router.post("/study-tracker/upload")
async def upload(request: Request, subject: str = Form(...), file: UploadFile = File(...)):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".txt"}:
        return JSONResponse({"error": "Only .pdf/.docx/.txt"}, 400)
    stamp = now().strftime("%Y%m%d_%H%M%S")
    file_bytes = await file.read()
    fname = f"{slug(Path(file.filename).stem)}_{stamp}{ext}"
    blob_path = f"uploads/{u['id']}/{fname}"
    try:
        upload_bytes(blob_path, file_bytes, content_type=file.content_type or "application/octet-stream")
    except Exception as e:
        # Keep the flow alive even if Storage upload fails; questions can still be processed.
        blob_path = ""
        print(f"[study-tracker/upload] storage upload failed: {e}")

    text = ""
    inferred_title = Path(file.filename).stem
    with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)
    try:
        try:
            text = extract_text_from_file(tmp_path)
        except Exception as e:
            print(f"[study-tracker/upload] extract failed: {e}")
            text = ""
        try:
            inferred_title = infer_paper_title(tmp_path, text)
        except Exception as e:
            print(f"[study-tracker/upload] title inference failed: {e}")
            inferred_title = Path(file.filename).stem
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
    qs = ai_questions_from_text(text, subject) or parse_questions(text)
    bid = f"{slug(subject)}-{slug(inferred_title)}-{stamp}"
    try:
        save_bank(
            {
                "bank_id": bid,
                "user_id": u["id"],
                "subject": subject.strip() or "General",
                "title": inferred_title,
                "source_filename": file.filename,
                "source_blob": blob_path,
                "created_at": now().isoformat(),
                "questions": qs,
            }
        )
    except Exception as e:
        return JSONResponse(
            {
                "error": f"Failed to save paper: {e}",
                "hint": "Check Firebase Firestore/Storage credentials and project settings.",
            },
            500,
        )
    return RedirectResponse(f"/banks/{bid}", 303)


@router.get("/banks/{bank_id}")
def bank(request: Request, bank_id: str):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    b = get_bank(bank_id)
    if not b or b.get("user_id") != u["id"]:
        return render(request, "bank.html", "Paper", bank=None, bank_id=bank_id)
    return render(request, "bank.html", b.get("title", "Paper"), bank=b, bank_id=bank_id)


@router.post("/banks/{bank_id}/edit")
def bank_edit(request: Request, bank_id: str, title: str = Form(...), subject: str = Form(...)):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    b = get_bank(bank_id)
    if not b or b.get("user_id") != u["id"]:
        return JSONResponse({"error": "not found"}, 404)
    b["title"], b["subject"] = title.strip(), subject.strip()
    save_bank(b)
    return RedirectResponse(f"/banks/{bank_id}", 303)


@router.post("/banks/{bank_id}/delete")
def bank_delete(request: Request, bank_id: str):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    b = get_bank(bank_id)
    if b and b.get("user_id") == u["id"]:
        delete_bank(bank_id)
    save_attempts([a for a in attempts() if not (a.get("user_id") == u["id"] and a.get("bank_id") == bank_id)])
    return RedirectResponse("/study-tracker", 303)


@router.post("/banks/{bank_id}/submit")
async def submit(request: Request, bank_id: str, duration_seconds: int = Form(0), workings: UploadFile | None = File(None)):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    b = get_bank(bank_id)
    if not b or b.get("user_id") != u["id"]:
        return JSONResponse({"error": "bank not found"}, 404)
    qs = b.get("questions", [])
    if not qs:
        return JSONResponse({"error": "no questions"}, 400)

    aid = f"attempt-{bank_id}-{now().strftime('%Y%m%d%H%M%S')}"
    dur = max(0, int(duration_seconds or 0))
    form = await request.form()
    ans = {k.replace("answer_", "", 1): str(v) for k, v in form.items() if k.startswith("answer_")}
    att = {q["qid"] for q in qs if ans.get(q["qid"], "").strip()}
    per = dur // len(att) if att else 0
    scored = 0.0
    poss_att = 0.0
    poss_all = 0.0
    rows = []
    for q in qs:
        a = ans.get(q["qid"], "").strip()
        tried = bool(a)
        s, fb = grade(q, a)
        mm = float(q.get("max_marks", 5))
        poss_all += mm
        if tried:
            scored += s
            poss_att += mm
        rows.append({"attempt_id": aid, "subject": b.get("subject", "General"), "bank_title": b.get("title", ""), "qid": q["qid"], "concept": q.get("concept", "General"), "difficulty": q.get("difficulty", "medium"), "question_text": q.get("question_text", ""), "correct_answer": q.get("correct_answer", "N/A"), "student_answer": a, "mark_scored": round(s, 2), "max_marks": round(mm, 2), "attempted": tried, "feedback": fb, "time_spent_seconds": per if tried else 0, "predicted_seconds": int(q.get("predicted_seconds", 0))})
    report_blob = ""
    report_filename = ""

    cs = [{"concept": x["concept"], "attempted_questions": x["attempted"], "marks_scored": round(x["scored"], 2), "marks_possible": round(x["possible"], 2), "mastery_pct": x["mastery_pct"]} for x in concept_rows(rows)]
    if pd is not None:
        try:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as w:
                pd.DataFrame(rows).to_excel(w, "Question Report", index=False)
                pd.DataFrame(cs).to_excel(w, "Concept Summary", index=False)
            report_filename = f"{aid}.xlsx"
            report_blob = f"reports/{u['id']}/{report_filename}"
            upload_bytes(
                report_blob,
                excel_buf.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            report_filename = ""
            report_blob = ""
    if not report_blob:
        try:
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()) if rows else ["note"])
            writer.writeheader()
            writer.writerows(rows) if rows else writer.writerow({"note": "No rows"})
            report_filename = f"{aid}.csv"
            report_blob = f"reports/{u['id']}/{report_filename}"
            upload_bytes(report_blob, out.getvalue().encode("utf-8"), content_type="text/csv")
        except Exception:
            report_filename = ""
            report_blob = ""

    summ = {"attempt_id": aid, "user_id": u["id"], "bank_id": bank_id, "subject": b.get("subject", "General"), "bank_title": b.get("title", ""), "started_at": (now() - __import__("datetime").timedelta(seconds=dur)).isoformat(), "submitted_at": now().isoformat(), "duration_seconds": dur, "questions_total": len(qs), "questions_attempted": len(att), "progress_pct": round(100 * len(att) / len(qs), 2), "overall_pct": round(100 * scored / max(1.0, poss_att), 2) if att else 0.0, "marks_scored_attempted": round(scored, 2), "marks_possible_attempted": round(poss_att, 2), "marks_possible_all": round(poss_all, 2), "workings_file": workings.filename if workings else "", "question_rows": rows, "predicted_score": predict(u["id"], b.get("subject", "General")), "report_filename": report_filename, "report_blob": report_blob}
    try:
        ar = attempts()
        ar.append(summ)
        save_attempts(ar)
    except Exception as e:
        return JSONResponse(
            {
                "error": f"Failed to save attempt: {e}",
                "hint": "Check Firebase Firestore credentials and connectivity.",
            },
            500,
        )
    return RedirectResponse(f"/reports/{aid}", 303)
