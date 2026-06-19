from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

SYSTEM_CODES = ('АПС', 'СОУЭ', 'АУГПТ', 'ВПВ')


class Region(Base):
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(25), unique=True, nullable=False)

    objects = relationship('Object', back_populates='region')


class Responsible(Base):
    __tablename__ = 'responsibles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    name = Column(String(50), unique=True, nullable=False)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)

    objects = relationship('Object', back_populates='responsible')


class ObjectSystemFlag(Base):
    __tablename__ = 'object_system_flags'
    __table_args__ = (
        UniqueConstraint('object_id', 'system_code', name='uq_object_system_code'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    object_id = Column(Integer, ForeignKey('objects.id', ondelete='CASCADE'), nullable=False)
    system_code = Column(String(10), nullable=False)

    object = relationship('Object', back_populates='system_flags')


class ObjectComposition(Base):
    __tablename__ = 'object_compositions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    object_id = Column(
        Integer,
        ForeignKey('objects.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
    )
    counts = Column(JSON, nullable=False, default=dict)

    object = relationship('Object', back_populates='composition')


class Object(Base):
    __tablename__ = 'objects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    number_in_db = Column(Integer, unique=True, nullable=False)
    inv_number = Column(String(25), unique=True, nullable=False)
    address = Column(String, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)
    object_type = Column(String(50))
    ownership = Column(Enum('Собственность', 'Аренда', 'н/д', name='ownership_types'), nullable=False)
    cost = Column(Float, default=0.0)
    responsible_id = Column(Integer, ForeignKey('responsibles.id'), nullable=True)
    maintenance_mode = Column(Enum('ежемесячное', 'квартальное', name='maintenance_modes'), nullable=False)
    system_type = Column(Enum('АПС', 'СОУЭ', 'АУГПТ', 'ВПВ', name='system_types'), nullable=False)

    region = relationship('Region', back_populates='objects')
    responsible = relationship('Responsible', back_populates='objects')
    system_flags = relationship(
        'ObjectSystemFlag',
        back_populates='object',
        cascade='all, delete-orphan',
    )
    composition = relationship(
        'ObjectComposition',
        back_populates='object',
        uselist=False,
        cascade='all, delete-orphan',
    )
    maintenance_records = relationship(
        'MaintenanceRecord',
        back_populates='object',
        cascade='all, delete-orphan',
    )
    extra_works = relationship(
        'ExtraWork',
        back_populates='object',
        cascade='all, delete-orphan',
    )
    documents = relationship(
        'ObjectDocuments',
        back_populates='object',
        uselist=False,
        cascade='all, delete-orphan',
    )
