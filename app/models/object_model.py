from sqlalchemy import Column, Integer, String, Float, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Object(Base):
    __tablename__ = 'objects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    number_in_db = Column(Integer, unique=True, nullable=False)      # Номер в базе (уникальный)
    inv_number = Column(String(25), unique=True, nullable=False)     # Инвентарный номер (уникальный)
    address = Column(String, nullable=False)                         # Адрес
    region = Column(String(25))                                      # Регион (справочник)
    object_type = Column(String(50))                                 # Тип объекта
    ownership = Column(Enum('Собственность', 'Аренда', name='ownership_types'), nullable=False)
    cost = Column(Float, default=0.0)                                # Стоимость
    responsible = Column(String(50))                                 # Ответственный (справочник)
    maintenance_mode = Column(Enum('ежемесячное', 'квартальное', name='maintenance_modes'), nullable=False)
    system_type = Column(Enum('АПС', 'СОУЭ', 'АУГПТ', 'ВПВ', name='system_types'), nullable=False)