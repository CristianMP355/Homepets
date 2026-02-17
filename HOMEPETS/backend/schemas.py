from typing import Optional
from pydantic import BaseModel, EmailStr

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
