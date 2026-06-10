import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from models.object_model import Base

_db_path = os.path.join(os.path.dirname(__file__), '..', 'objects.db')
_engine = create_engine(f'sqlite:///{_db_path}', echo=False)
SessionLocal = sessionmaker(bind=_engine)


def _get_or_create_region_id(conn, cache: dict[str, int], name: str | None) -> int | None:
    if not name or not str(name).strip():
        return None
    name = str(name).strip()
    if name in cache:
        return cache[name]
    row = conn.execute(
        text('SELECT id FROM regions WHERE name = :name'),
        {'name': name},
    ).fetchone()
    if row is None:
        result = conn.execute(text('INSERT INTO regions (name) VALUES (:name)'), {'name': name})
        region_id = result.lastrowid
    else:
        region_id = row[0]
    cache[name] = region_id
    return region_id


def _get_or_create_responsible_id(conn, cache: dict[str, int], name: str | None) -> int | None:
    if not name or not str(name).strip():
        return None
    name = str(name).strip()
    if name in cache:
        return cache[name]
    row = conn.execute(
        text('SELECT id FROM responsibles WHERE name = :name'),
        {'name': name},
    ).fetchone()
    if row is None:
        result = conn.execute(text('INSERT INTO responsibles (name) VALUES (:name)'), {'name': name})
        responsible_id = result.lastrowid
    else:
        responsible_id = row[0]
    cache[name] = responsible_id
    return responsible_id


def _migrate_to_reference_tables(engine) -> None:
    inspector = inspect(engine)
    if 'objects' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('objects')}
    if 'region_id' in columns or 'region' not in columns:
        return

    with engine.begin() as conn:
        Base.metadata.create_all(engine)

        rows = conn.execute(text('SELECT id, region, responsible FROM objects')).fetchall()
        region_cache: dict[str, int] = {}
        responsible_cache: dict[str, int] = {}

        conn.execute(text('ALTER TABLE objects ADD COLUMN region_id INTEGER'))
        conn.execute(text('ALTER TABLE objects ADD COLUMN responsible_id INTEGER'))

        for row in rows:
            conn.execute(
                text(
                    'UPDATE objects SET region_id = :region_id, responsible_id = :responsible_id '
                    'WHERE id = :id'
                ),
                {
                    'id': row.id,
                    'region_id': _get_or_create_region_id(conn, region_cache, row.region),
                    'responsible_id': _get_or_create_responsible_id(conn, responsible_cache, row.responsible),
                },
            )

        conn.execute(text('ALTER TABLE objects DROP COLUMN region'))
        conn.execute(text('ALTER TABLE objects DROP COLUMN responsible'))


Base.metadata.create_all(_engine)
_migrate_to_reference_tables(_engine)

def get_db() -> Session:
    return SessionLocal()
