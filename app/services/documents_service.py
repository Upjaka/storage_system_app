from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.orm import Session

from models.operations_model import DOCUMENT_FIELD_LABELS, ObjectDocuments

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / 'uploads'


def get_documents(db: Session, object_id: int) -> dict[str, str | None]:
    row = db.query(ObjectDocuments).filter(ObjectDocuments.object_id == object_id).first()
    if row is None:
        return {field: None for field in DOCUMENT_FIELD_LABELS}
    return {field: getattr(row, field) for field in DOCUMENT_FIELD_LABELS}


def upsert_documents(db: Session, object_id: int, data: dict[str, str | None]) -> ObjectDocuments:
    row = db.query(ObjectDocuments).filter(ObjectDocuments.object_id == object_id).first()
    normalized = {
        field: (str(value).strip() if value else None)
        for field, value in data.items()
        if field in DOCUMENT_FIELD_LABELS
    }
    if row is None:
        row = ObjectDocuments(object_id=object_id, **normalized)
        db.add(row)
    else:
        for field, value in normalized.items():
            setattr(row, field, value)
    db.flush()
    return row


def save_uploaded_file(inv_number: str, field_name: str, source_path: str, filename: str) -> str:
    safe_inv = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in inv_number)
    target_dir = UPLOAD_ROOT / safe_inv / field_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / Path(filename).name
    if os.path.abspath(source_path) != os.path.abspath(target_path):
        Path(source_path).replace(target_path)
    return str(target_path.relative_to(UPLOAD_ROOT.parent))
