from typing import Optional
from pydantic import BaseModel, EmailStr, Field


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


class AnfitrionRead(BaseModel):
    id: int
    usuario_id: int
    descripcion: Optional[str] = None
    direccion: Optional[str] = None
    foto: Optional[str] = None

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
    fotos_espacio: list[FotoEspacioRead] = Field(default_factory=list)