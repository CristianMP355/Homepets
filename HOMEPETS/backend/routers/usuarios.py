from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import List

from backend.database.database import get_db
from backend.database.models import Usuario
from utils.jwt_config import create_access_token, get_current_user
from schemas import UsuarioRead


router = APIRouter(prefix="/usuarios", tags=["usuarios"])

UPLOAD_DIR_USERS = Path("static/uploads/usuarios")
UPLOAD_DIR_USERS.mkdir(parents=True, exist_ok=True)


def eliminar_archivo_si_existe(ruta_relativa: str | None):
    if not ruta_relativa:
        return

    ruta_limpia = ruta_relativa.lstrip("/")
    ruta_archivo = Path(ruta_limpia)

    if ruta_archivo.exists() and ruta_archivo.is_file():
        ruta_archivo.unlink()


class UserCreate(BaseModel):
    nombre: str
    email: EmailStr
    telefono: str | None = None
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    telefono: str | None = None
    direccion: str | None = None
    rol: str
    foto_user: str | None = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[UserResponse])
async def read_usuarios(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Usuario))
    return result.scalars().all()


@router.post("/", response_model=UserResponse, status_code=201)
async def create_usuario(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await db.execute(select(Usuario).where(Usuario.email == user.email))

    if db_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    db_user = Usuario(
        nombre=user.nombre,
        email=user.email,
        telefono=user.telefono,
        password_hash=Usuario.hash_password(user.password)
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.post("/login")
async def login_usuario(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Usuario).where(Usuario.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if user.password_hash != Usuario.hash_password(credentials.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "rol": user.rol
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nombre": user.nombre,
            "email": user.email,
            "telefono": user.telefono,
            "direccion": user.direccion,
            "rol": user.rol,
            "foto_user": user.foto_user
        }
    }


@router.get("/{usuario_id}", response_model=UsuarioRead)
async def obtener_usuario(usuario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id)
    )
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario


@router.patch("/{usuario_id}/perfil", response_model=UsuarioRead)
async def actualizar_perfil_usuario(
    usuario_id: int,
    nombre: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(...),
    direccion: str = Form(""),
    foto_user: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id)
    )
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    email = email.strip().lower()

    email_existente = await db.execute(
        select(Usuario).where(Usuario.email == email, Usuario.id != usuario_id)
    )
    if email_existente.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe otra cuenta con ese correo electrónico")

    usuario.nombre = nombre.strip()
    usuario.email = email
    usuario.telefono = telefono.strip()
    usuario.direccion = direccion.strip() if direccion else ""

    if foto_user and foto_user.filename:
        content_type = foto_user.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen válida")

        extension = Path(foto_user.filename).suffix.lower()
        if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(
                status_code=400,
                detail="Formato de imagen no permitido. Usa JPG, JPEG, PNG o WEBP"
            )

        nombre_archivo = f"usuario_{usuario_id}_{uuid4().hex}{extension}"
        ruta_archivo = UPLOAD_DIR_USERS / nombre_archivo

        contenido = await foto_user.read()
        with open(ruta_archivo, "wb") as f:
            f.write(contenido)

        eliminar_archivo_si_existe(usuario.foto_user)
        usuario.foto_user = f"/static/uploads/usuarios/{nombre_archivo}"

    await db.commit()
    await db.refresh(usuario)

    return usuario