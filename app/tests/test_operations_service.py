from datetime import datetime

from models.operations_model import MaintenanceRecord, ObjectDocuments
from services.documents_service import get_documents, upsert_documents
from services.maintenance_service import (
    create_maintenance_record,
    delete_maintenance_record,
    get_maintenance_records,
)
from services.object_service import create_object
from conftest import object_payload


def test_create_maintenance_record_for_object(db):
    obj = create_object(db, object_payload(inv_number='INV-MNT'))
    record = create_maintenance_record(
        db,
        object_id=obj.id,
        date=datetime(2026, 3, 26),
        act_to=True,
        extra_works_flag=False,
    )
    db.commit()

    records = get_maintenance_records(db, object_id=obj.id)
    assert len(records) == 1
    assert records[0].id == record.id
    assert records[0].act_to is True


def test_delete_maintenance_record(db):
    obj = create_object(db, object_payload(inv_number='INV-MNT-DEL'))
    record = create_maintenance_record(db, object_id=obj.id, date=None)
    db.commit()

    delete_maintenance_record(db, record.id)
    db.commit()

    assert db.query(MaintenanceRecord).count() == 0


def test_upsert_documents_creates_and_updates(db):
    obj = create_object(db, object_payload(inv_number='INV-DOC'))

    upsert_documents(db, obj.id, {'passport': 'path/to/passport.pdf'})
    db.commit()

    docs = get_documents(db, obj.id)
    assert docs['passport'] == 'path/to/passport.pdf'

    upsert_documents(db, obj.id, {'passport': 'updated.pdf', 'journal': 'journal.pdf'})
    db.commit()

    docs = get_documents(db, obj.id)
    assert docs['passport'] == 'updated.pdf'
    assert docs['journal'] == 'journal.pdf'
    assert db.query(ObjectDocuments).filter_by(object_id=obj.id).count() == 1
