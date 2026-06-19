from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship

from models.object_model import Base


class Unit(Base):
    __tablename__ = 'units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    name = Column(String(20), unique=True, nullable=False)

    materials = relationship('Material', back_populates='unit')


class Material(Base):
    __tablename__ = 'materials'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    unit_id = Column(Integer, ForeignKey('units.id'), nullable=True)
    cost = Column(Float, default=0.0)
    defect = Column(String(255), nullable=True)
    link = Column(Text, nullable=True)

    unit = relationship('Unit', back_populates='materials')
    work_types = relationship('WorkType', back_populates='material')


class WorkType(Base):
    __tablename__ = 'work_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    cost = Column(Float, default=0.0)
    section = Column(String(50), nullable=True)
    output_text = Column(String(255), nullable=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=True)

    material = relationship('Material', back_populates='work_types')


class MaintenancePrice(Base):
    __tablename__ = 'maintenance_prices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_code = Column(Integer, unique=True, nullable=True)
    equipment_name = Column(String(255), nullable=False)
    unit_price = Column(Float, default=0.0)
