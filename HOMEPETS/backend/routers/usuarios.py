from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import List
from database.database import get_db
from database.models import User

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

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

    class Config:
        from_attributes = True

@router.get("/", response_model=List[UserResponse])
async def read_usuarios(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()

@router.post("/", response_model=UserResponse, status_code=201)
async def create_usuario(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await db.execute(select(User).where(User.email == user.email))
    if db_user.scalar_one_or_none():
        raise HTTPException(400, "Email ya registrado")
    
    db_user = User(
        nombre=user.nombre,
        email=user.email,
        telefono=user.telefono,
        password_hash=User.hash_password(user.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login")
async def login_usuario(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    if not user or user.password_hash != User.hash_password(credentials.password):
        raise HTTPException(401, "Credenciales inválidas")
    return {"message": "Login exitoso", "user": {"id": user.id, "nombre": user.nombre, "email": user.email}}
