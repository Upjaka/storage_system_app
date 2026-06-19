from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from models.object_model import Base

DOCUMENT_FIELD_LABELS: dict[str, str] = {
    'passport': 'Паспорт',
    'acceptance_act': 'Акт приемки',
    'performance_check_act': 'Акт проверки работоспособности',
    'defect_list': 'Дефектная ведомость',
    'commercial_proposal': 'КП',
    'installation_act': 'Акт по установке оборудования',
    'journal': 'Журнал',
    'photo_bank': 'Фотобанк',
}


class MaintenanceRecord(Base):
    __tablename__ = 'maintenance_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    object_id = Column(Integer, ForeignKey('objects.id', ondelete='CASCADE'), nullable=False)
    date = Column(DateTime, nullable=True)
    act_to = Column(Boolean, nullable=False, default=False)
    extra_works_flag = Column(Boolean, nullable=False, default=False)

    object = relationship('Object', back_populates='maintenance_records')


class ExtraWork(Base):
    __tablename__ = 'extra_works'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    object_id = Column(Integer, ForeignKey('objects.id', ondelete='CASCADE'), nullable=False)
    date = Column(DateTime, nullable=True)
    document_number = Column(Integer, nullable=True)
    work_type_id = Column(Integer, ForeignKey('work_types.id'), nullable=True)
    quantity = Column(Integer, nullable=True)
    unit_cost = Column(Float, default=0.0)
    unit_vat = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    price_vat = Column(Float, default=0.0)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=True)
    unit_id = Column(Integer, ForeignKey('units.id'), nullable=True)
    material_quantity = Column(Integer, nullable=True)
    material_unit_cost = Column(Float, default=0.0)
    material_unit_vat = Column(Float, default=0.0)
    material_price = Column(Float, default=0.0)
    material_price_vat = Column(Float, default=0.0)
    material_system = Column(String(10), nullable=True)

    object = relationship('Object', back_populates='extra_works')
    work_type = relationship('WorkType')
    material = relationship('Material')
    unit = relationship('Unit')


class ObjectDocuments(Base):
    __tablename__ = 'object_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    object_id = Column(
        Integer,
        ForeignKey('objects.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
    )
    passport = Column(Text, nullable=True)
    acceptance_act = Column(Text, nullable=True)
    performance_check_act = Column(Text, nullable=True)
    defect_list = Column(Text, nullable=True)
    commercial_proposal = Column(Text, nullable=True)
    installation_act = Column(Text, nullable=True)
    journal = Column(Text, nullable=True)
    photo_bank = Column(Text, nullable=True)

    object = relationship('Object', back_populates='documents')
