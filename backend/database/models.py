from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime
from datetime import timezone
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

    mascotas = relationship(
        "Mascota",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )

    mensajes_enviados = relationship(
        "Mensaje",
        foreign_keys="Mensaje.emisor_id",
        back_populates="emisor",
        cascade="all, delete-orphan"
    )

    mensajes_recibidos = relationship(
        "Mensaje",
        foreign_keys="Mensaje.receptor_id",
        back_populates="receptor",
        cascade="all, delete-orphan"
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
    fechas_no_disponibles = Column(String, nullable=True)

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


class Mensaje(Base):
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True, index=True)

    emisor_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False
    )

    receptor_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False
    )

    contenido = Column(String, nullable=False)

    fecha_envio = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    leido = Column(Boolean, nullable=False, default=False)
    fecha_lectura = Column(DateTime, nullable=True)

    emisor = relationship(
        "Usuario",
        foreign_keys=[emisor_id],
        back_populates="mensajes_enviados"
    )

    receptor = relationship(
        "Usuario",
        foreign_keys=[receptor_id],
        back_populates="mensajes_recibidos"
    )


class Mascota(Base):
    __tablename__ = "mascotas"

    id = Column(Integer, primary_key=True, index=True)
    tipo_mascota = Column(String, nullable=True)
    nombre = Column(String, nullable=False)
    raza = Column(String, nullable=True)
    edad = Column(String, nullable=True)
    vacunas = Column(String, nullable=True)
    notas = Column(String, nullable=True)
    foto = Column(String, nullable=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False
    )

    usuario = relationship("Usuario", back_populates="mascotas")