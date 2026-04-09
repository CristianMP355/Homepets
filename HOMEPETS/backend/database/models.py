from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database.database import Base
import hashlib


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    foto_user = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)

    rol = Column(String, nullable=False, default="cliente")

    perfil_anfitrion = relationship(
        "Anfitrion",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete"
    )

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()


class Anfitrion(Base):
    __tablename__ = "anfitriones"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    descripcion = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    foto = Column(String, nullable=True)

    usuario = relationship("Usuario", back_populates="perfil_anfitrion")

    fotos_espacio = relationship(
        "FotoEspacio",
        back_populates="anfitrion",
        cascade="all, delete-orphan"
    )


class FotoEspacio(Base):
    __tablename__ = "fotos_espacios"

    id = Column(Integer, primary_key=True, index=True)
    anfitrion_id = Column(
        Integer,
        ForeignKey("anfitriones.id", ondelete="CASCADE"),
        nullable=False
    )
    ruta_foto = Column(String, nullable=False)

    anfitrion = relationship("Anfitrion", back_populates="fotos_espacio")