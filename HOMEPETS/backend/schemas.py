from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# =========================
# USUARIOS
# =========================

class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioRead(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    rol: str
    foto_user: Optional[str] = None

    class Config:
        from_attributes = True


# =========================
# ANFITRIONES
# =========================

class AnfitrionRead(BaseModel):
    id: int
    usuario_id: int
    descripcion: Optional[str] = None
    direccion: Optional[str] = None
    foto: Optional[str] = None
    fechas_no_disponibles: Optional[str] = None

    class Config:
        from_attributes = True


class AnfitrionListItem(BaseModel):
    id: int
    usuario_id: int
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    descripcion: Optional[str] = None
    direccion: Optional[str] = None
    foto: Optional[str] = None
    foto_user: Optional[str] = None
    fechas_no_disponibles: Optional[str] = None

    class Config:
        from_attributes = True


class FotoEspacioRead(BaseModel):
    id: int
    ruta_foto: str

    class Config:
        from_attributes = True


class AnfitrionDetalle(BaseModel):
    id: int
    usuario_id: int
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    descripcion: Optional[str] = None
    direccion: Optional[str] = None
    foto: Optional[str] = None
    foto_user: Optional[str] = None
    fechas_no_disponibles: Optional[str] = None
    fotos_espacio: list[FotoEspacioRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


# =========================
# MASCOTAS
# =========================

class MascotaCreate(BaseModel):
    tipo_mascota: Optional[str] = None
    nombre: str
    raza: Optional[str] = None
    edad: Optional[str] = None
    vacunas: Optional[str] = None
    notas: Optional[str] = None
    foto: Optional[str] = None
    usuario_id: int


class ResponsableMascotaRead(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None

    class Config:
        from_attributes = True


class MascotaDetalle(BaseModel):
    id: int
    tipo_mascota: Optional[str] = None
    nombre: str
    raza: Optional[str] = None
    edad: Optional[str] = None
    vacunas: Optional[str] = None
    notas: Optional[str] = None
    foto: Optional[str] = None
    usuario_id: int
    responsable: ResponsableMascotaRead

    class Config:
        from_attributes = True


class MascotaRead(BaseModel):
    id: int
    tipo_mascota: Optional[str] = None
    nombre: str
    raza: Optional[str] = None
    edad: Optional[str] = None
    vacunas: Optional[str] = None
    notas: Optional[str] = None
    foto: Optional[str] = None
    usuario_id: int

    class Config:
        from_attributes = True


# =========================
# MENSAJES / CHAT
# =========================

class MensajeCreate(BaseModel):
    receptor_id: int
    contenido: str


class MensajeRead(BaseModel):
    id: int
    emisor_id: int
    receptor_id: int
    contenido: str
    fecha_envio: datetime
    leido: bool
    fecha_lectura: Optional[datetime] = None

    class Config:
        from_attributes = True


class MensajeOut(BaseModel):
    id: int
    emisor_id: int
    receptor_id: int
    contenido: str
    fecha_envio: datetime
    leido: bool
    fecha_lectura: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatResumen(BaseModel):
    usuario_id: int
    nombre: str
    email: EmailStr
    foto_user: Optional[str] = None
    ultimo_mensaje: str
    fecha_envio: datetime
    no_leidos: int = 0

    class Config:
        from_attributes = True


class ChatResumenOut(BaseModel):
    usuario_id: int
    otro_usuario_id: int
    otro_usuario_nombre: str
    otro_usuario_email: EmailStr
    otro_usuario_foto: Optional[str] = None
    ultimo_mensaje: Optional[str] = None
    fecha_ultimo_mensaje: Optional[datetime] = None
    no_leidos: int = 0

    class Config:
        from_attributes = True


class NoLeidosOut(BaseModel):
    total_no_leidos: int