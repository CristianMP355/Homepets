from typing import Optional
from sqlmodel import SQLModel, Field

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    rol: str = "cliente"   # "admin" o "cliente" (Clave)
    foto_user: Optional[str] = None  # dataURL o URL en futuro
