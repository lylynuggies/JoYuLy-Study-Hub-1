from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .db import attempts, exams
from .security import me
from .services import concept_rows
from .state import APP_NAME

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def render(request: Request, template_name: str, title: str, **context):
    user = me(request)
    theme = (user or {}).get("theme", "light")
    palette = {
        "light": {"bg": "#f6f8fb", "fg": "#1f2937", "card": "#ffffff", "heading": "#102a43", "muted": "#5d6b7c"},
        "dark": {"bg": "#0b1220", "fg": "#e7edf5", "card": "#152238", "heading": "#f2f7ff", "muted": "#c0cfdf"},
        "ocean": {"bg": "#0c3554", "fg": "#eef7ff", "card": "#123f62", "heading": "#f2fbff", "muted": "#c6e1f2"},
    }[theme if theme in {"light", "dark", "ocean"} else "light"]

    bg_presets = {
        "light": {
            "gradient": "linear-gradient(180deg, #f5f7fb 0%, var(--bg) 220px)",
            "image": "none",
            "overlay": "none",
        },
        "dark": {
            "gradient": "linear-gradient(180deg, #0a111d 0%, #101a2d 46%, #111f34 100%)",
            "image": "none",
            "overlay": "none",
        },
        "ocean": {
            "gradient": "linear-gradient(145deg, #95b9cf 0%, #4c7ea0 45%, #0d4e72 100%)",
            "image": "url('/static/backgrounds/ocean.jpg')",
            "overlay": "linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.16))",
        },
    }
    bg_preset = bg_presets.get(theme if theme in bg_presets else "light", bg_presets["light"])

    mascot_messages = [
        "You can do this. One focused session today will move you forward.",
        "Small progress still counts. Keep your momentum going.",
        "Stay steady. Your consistency builds mastery over time.",
    ]
    if user:
        mine = [a for a in attempts() if a.get("user_id") == user.get("id")]
        user_exams = [e for e in exams() if e.get("user_id") == user.get("id")]
        rows = concept_rows([q for a in mine for q in a.get("question_rows", []) if q.get("attempted")])
        low_mastery = min((r.get("mastery_pct", 100.0) for r in rows), default=100.0)
        if mine:
            mine.sort(key=lambda x: x.get("submitted_at") or x.get("started_at") or "")
            last = mine[-1]
            last_raw = last.get("submitted_at") or last.get("started_at")
            if last_raw:
                try:
                    last_dt = datetime.fromisoformat(last_raw)
                    days_away = (datetime.utcnow().date() - last_dt.date()).days
                    if days_away >= 3:
                        mascot_messages = [
                            f"We haven't seen you in {days_away} days. Let's restart with one short session today.",
                            "A 20-minute restart is enough to get back on track.",
                            "You are not behind forever. Start now and recover step by step.",
                        ]
                except Exception:
                    pass

            week_hours: dict[str, float] = {}
            for a in mine:
                started = a.get("started_at") or a.get("submitted_at")
                if not started:
                    continue
                try:
                    dt = datetime.fromisoformat(started)
                except Exception:
                    continue
                y, w, _ = dt.isocalendar()
                key = f"{y}-W{w:02d}"
                week_hours[key] = week_hours.get(key, 0.0) + float(a.get("duration_seconds", 0)) / 3600.0
            if week_hours:
                sorted_weeks = sorted(week_hours.items(), key=lambda x: x[0])
                _, current_hours = sorted_weeks[-1]
                prev_max = max((h for _, h in sorted_weeks[:-1]), default=0.0)
                if current_hours > prev_max and current_hours >= 1.0:
                    mascot_messages = [
                        f"You reached a new productivity max at {current_hours:.1f} hours this week. Good job!",
                        "Excellent consistency. Keep this pace and protect your revision blocks.",
                        "You are building exam fitness. Keep showing up.",
                    ]

        today = datetime.utcnow().date()
        nearest_days = None
        for e in user_exams:
            try:
                d = datetime.strptime(e.get("date", ""), "%Y-%m-%d").date()
            except Exception:
                continue
            days = (d - today).days
            if days >= 0 and (nearest_days is None or days < nearest_days):
                nearest_days = days
        if nearest_days is not None and nearest_days <= 7 and low_mastery < 60:
            mascot_messages = [
                f"Exam in {nearest_days} day(s) and mastery is low ({low_mastery:.0f}%). Focus on priority concepts now.",
                "Prioritize weak concepts first, then run one timed practice set.",
                "You still have time if you execute the plan today.",
            ]

    mascot_dir = Path(__file__).resolve().parent.parent / "static" / "mascots"
    preferred = ["joyuly_hi.png", "joyuly_happy.png", "joyuly_sleep.png"]
    mascot_images = [f"/static/mascots/{name}" for name in preferred if (mascot_dir / name).exists()]
    if not mascot_images:
        mascot_images = ["/static/mascots/placeholder.svg"]

    payload = {
        "request": request,
        "app_name": APP_NAME,
        "title": title,
        "current_user": user,
        "current_theme": theme,
        "palette": palette,
        "bg_preset": bg_preset,
        "mascot_messages": mascot_messages,
        "mascot_images": mascot_images,
        "mascot_rotate_ms": 3600000,
        **context,
    }
    return TEMPLATES.TemplateResponse(template_name, payload)
