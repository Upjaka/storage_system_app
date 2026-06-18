from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Region(Base):
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(25), unique=True, nullable=False)

    objects = relationship('Object', back_populates='region')


class Responsible(Base):
    __tablename__ = 'responsibles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    objects = relationship('Object', back_populates='responsible')


class Object(Base):
    __tablename__ = 'objects'

    id = Column(Integer, primary_key=True, autoincrement=True)
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
