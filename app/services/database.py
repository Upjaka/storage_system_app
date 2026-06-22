from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from models.object_model import Base
import models.catalog_model  # noqa: F401 — register catalog tables
import models.operations_model  # noqa: F401 — register operations tables
from paths import app_dir

_db_path = str(app_dir() / 'objects.db')
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


def _add_column_if_missing(
    inspector,
    conn,
    table: str,
    column: str,
    column_def: str,
) -> None:
    if table not in inspector.get_table_names():
        return
    columns = {col['name'] for col in inspector.get_columns(table)}
    if column not in columns:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {column_def}'))


def _backfill_system_flags(conn) -> None:
    rows = conn.execute(
        text('SELECT id, system_type FROM objects WHERE system_type IS NOT NULL'),
    ).fetchall()
    for row in rows:
        existing = conn.execute(
            text('SELECT COUNT(*) FROM object_system_flags WHERE object_id = :object_id'),
            {'object_id': row.id},
        ).scalar()
        if existing:
            continue
        conn.execute(
            text(
                'INSERT INTO object_system_flags (object_id, system_code) '
                'VALUES (:object_id, :system_code)'
            ),
            {'object_id': row.id, 'system_code': row.system_type},
        )


def _migrate_phase1_schema(engine) -> None:
    inspector = inspect(engine)
    if 'objects' not in inspector.get_table_names():
        return

    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        _add_column_if_missing(inspector, conn, 'objects', 'access_code', 'INTEGER')
        if 'responsibles' in inspector.get_table_names():
            for column, column_def in (
                ('access_code', 'INTEGER'),
                ('department', 'VARCHAR(100)'),
                ('position', 'VARCHAR(100)'),
                ('email', 'VARCHAR(100)'),
                ('phone', 'VARCHAR(50)'),
            ):
                _add_column_if_missing(inspector, conn, 'responsibles', column, column_def)

    inspector = inspect(engine)
    if 'object_system_flags' not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        _backfill_system_flags(conn)


Base.metadata.create_all(_engine)
_migrate_to_reference_tables(_engine)
_migrate_phase1_schema(_engine)

def get_database_path() -> str:
    return _db_path


def get_db() -> Session:
    return SessionLocal()
