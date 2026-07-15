from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Load(Base):
    __tablename__ = "loads"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True, nullable=False)
    name = Column(String, nullable=True)
    weight = Column(Float, nullable=False)
    is_imo = Column(Boolean, default=False, nullable=False)
    allocated_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamento de volta para o Slot
    slot = relationship("Slot", back_populates="load", uselist=False)


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    aisle = Column(Integer, nullable=False)  # Corredor
    column = Column(Integer, nullable=False)  # Coluna
    level = Column(Integer, nullable=False)  # Nível (1 a 7)
    is_occupied = Column(Boolean, default=False, nullable=False)
    is_imo_restricted = Column(Boolean, default=False, nullable=False)  # Apenas para cargas IMO
    
    # ID da carga associada
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=True)
    load = relationship("Load", back_populates="slot")
