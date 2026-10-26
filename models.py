from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), nullable=False)
    
    cuentas = relationship("Cuenta", back_populates="propietario")

class Cuenta(Base):
    __tablename__ = "cuentas"

    id = Column(Integer, primary_key=True, index=True)
    numero_cuenta = Column(String(20), unique=True, nullable=False)
    saldo = Column(Float, default=0.0)
    propietario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    propietario = relationship("Usuario", back_populates="cuentas")