from __future__ import annotations

import io
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.responses import Response

from .db import attempts
from .firebase_backend import download_bytes
from .security import must
from .services import grouped_concept_rows
from .ui import render

router = APIRouter()


@router.get("/reports/{attempt_id}")
def report(request: Request, attempt_id: str):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    a = next((x for x in attempts() if x.get("attempt_id") == attempt_id and x.get("user_id") == u["id"]), None)
    if not a:
        return RedirectResponse("/dashboard", 303)
    cr = [x for x in grouped_concept_rows(a.get("question_rows", [])) if x["subject"] == a.get("subject")]
    return render(
        request,
        "report.html",
        "Report",
        report=a,
        concept_summary=cr,
        report_filename=a.get("report_filename"),
        attempt_id=attempt_id,
    )


@router.get("/reports/download/{attempt_id}")
def report_download(request: Request, attempt_id: str):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    a = next((x for x in attempts() if x.get("attempt_id") == attempt_id and x.get("user_id") == u["id"]), None)
    if not a:
        return JSONResponse({"error": "not found"}, 404)
    blob = a.get("report_blob", "")
    name = a.get("report_filename", f"{attempt_id}.dat")
    if not blob:
        return JSONResponse({"error": "report blob missing"}, 404)
    try:
        data = download_bytes(blob)
    except Exception:
        return JSONResponse({"error": "not found"}, 404)
    media = "application/octet-stream"
    if str(name).lower().endswith(".xlsx"):
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif str(name).lower().endswith(".csv"):
        media = "text/csv"
    headers = {"Content-Disposition": f"attachment; filename={name}"}
    return Response(content=data, media_type=media, headers=headers)


@router.get("/reports/pdf/{attempt_id}")
def report_pdf(request: Request, attempt_id: str):
    u = must(request)
    if isinstance(u, RedirectResponse):
        return u
    a = next((x for x in attempts() if x.get("attempt_id") == attempt_id and x.get("user_id") == u["id"]), None)
    if not a:
        return RedirectResponse("/dashboard", 303)
    cr = [x for x in grouped_concept_rows(a.get("question_rows", [])) if x["subject"] == a.get("subject")]
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        return JSONResponse({"error": "PDF export requires reportlab. Install with: pip install reportlab"}, 500)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, f"Report: {a.get('bank_title','')}")
    y -= 24
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Subject: {a.get('subject','')}   Progress: {a.get('progress_pct',0)}%   Score: {a.get('overall_pct',0)}%")
    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Concept Mastery (Bar Chart)")
    y -= 16

    from reportlab.pdfbase import pdfmetrics

    def draw_wrapped(text: str, x: int, y0: int, max_w: int, font: str, size: int, line_h: int) -> int:
        c.setFont(font, size)
        words = str(text or "").split()
        line = ""
        yv = y0
        for w in words:
            cand = (line + " " + w).strip()
            if pdfmetrics.stringWidth(cand, font, size) <= max_w:
                line = cand
            else:
                if line:
                    c.drawString(x, yv, line)
                    yv -= line_h
                line = w
        if line:
            c.drawString(x, yv, line)
            yv -= line_h
        return yv

    max_bar_w = 240
    for row in cr[:10]:
        if y < 120:
            c.showPage()
            y = height - 40
        concept = str(row.get("concept", ""))
        mastery = float(row.get("mastery_pct", 0.0))
        y = draw_wrapped(concept, 40, y, 150, "Helvetica", 9, 11)
        y += 11
        c.setFillColor(colors.HexColor("#dce7f9"))
        c.rect(200, y - 8, max_bar_w, 10, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#1f5fae"))
        c.rect(200, y - 8, max_bar_w * max(0.0, min(1.0, mastery / 100.0)), 10, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawString(450, y, f"{mastery:.1f}%")
        y -= 20

    y -= 6
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Question Breakdown")
    y -= 14
    c.setFont("Helvetica", 9)
    for q in a.get("question_rows", [])[:18]:
        if y < 50:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)
        line = f"{q.get('qid','')}: {q.get('concept','')} | {q.get('mark_scored',0)}/{q.get('max_marks',0)} | {'Attempted' if q.get('attempted') else 'Not attempted'}"
        y = draw_wrapped(line, 40, y, 510, "Helvetica", 9, 11)

    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    headers = {"Content-Disposition": f"attachment; filename={attempt_id}.pdf"}
    return Response(content=pdf, media_type="application/pdf", headers=headers)
