from __future__ import annotations

from typing import Any

from .firebase_backend import db


def _collection_get_all(name: str) -> list[dict[str, Any]]:
    rows = []
    for snap in db().collection(name).stream():
        item = snap.to_dict() or {}
        item.setdefault("id", snap.id)
        rows.append(item)
    return rows


def _collection_replace(name: str, rows: list[dict[str, Any]], id_field: str = "id") -> None:
    c = db().collection(name)
    existing = {d.id for d in c.stream()}
    keep = set()
    for row in rows:
        doc_id = str(row.get(id_field) or row.get("id") or "")
        if not doc_id:
            continue
        payload = dict(row)
        payload["id"] = doc_id
        c.document(doc_id).set(payload)
        keep.add(doc_id)
    for doc_id in (existing - keep):
        c.document(doc_id).delete()


def users() -> list[dict[str, Any]]:
    return _collection_get_all("users")


def save_users(rows: list[dict[str, Any]]) -> None:
    _collection_replace("users", rows, id_field="id")


def exams() -> list[dict[str, Any]]:
    return _collection_get_all("exams")


def save_exams(rows: list[dict[str, Any]]) -> None:
    _collection_replace("exams", rows, id_field="exam_id")


def attempts() -> list[dict[str, Any]]:
    return _collection_get_all("attempts")


def save_attempts(rows: list[dict[str, Any]]) -> None:
    _collection_replace("attempts", rows, id_field="attempt_id")


def list_banks_for_user(user_id: str) -> list[dict[str, Any]]:
    out = []
    for b in _collection_get_all("banks"):
        if b.get("user_id") == user_id:
            out.append(b)
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return out


def get_bank(bank_id: str) -> dict[str, Any] | None:
    snap = db().collection("banks").document(bank_id).get()
    if not snap.exists:
        return None
    item = snap.to_dict() or {}
    item.setdefault("bank_id", bank_id)
    return item


def save_bank(bank: dict[str, Any]) -> None:
    bank_id = str(bank.get("bank_id", "")).strip()
    if not bank_id:
        raise ValueError("bank_id required")
    payload = dict(bank)
    payload["bank_id"] = bank_id
    db().collection("banks").document(bank_id).set(payload)


def delete_bank(bank_id: str) -> None:
    db().collection("banks").document(bank_id).delete()
