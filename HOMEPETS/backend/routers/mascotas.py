from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.database import get_db
from database.models import Mascota
from schemas import MascotaCreate, MascotaRead, MascotaDetalle, ResponsableMascotaRead
from utils.jwt_config import get_current_user


router = APIRouter(tags=["Mascotas"])


@router.post("/mascotas", response_model=MascotaRead)
async def crear_mascota(
    mascota: MascotaCreate,
    db: AsyncSession = Depends(get_db)
):
    nueva = Mascota(
        tipo_mascota=mascota.tipo_mascota,
        nombre=mascota.nombre,
        raza=mascota.raza,
        edad=mascota.edad,
        vacunas=mascota.vacunas,
        notas=mascota.notas,
        foto=mascota.foto,
        usuario_id=mascota.usuario_id
    )

    db.add(nueva)
    await db.commit()
    await db.refresh(nueva)

    return nueva


@router.get("/mascotas/mis-mascotas", response_model=list[MascotaRead])
async def obtener_mis_mascotas(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.get("id")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido: no contiene id")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido: id no válido")

    result = await db.execute(
        select(Mascota).where(Mascota.usuario_id == user_id).order_by(Mascota.id.asc())
    )
    mascotas = result.scalars().all()

    return mascotas


@router.get("/mascotas/{mascota_id}", response_model=MascotaDetalle)
async def obtener_detalle_mascota(
    mascota_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Mascota)
        .options(selectinload(Mascota.usuario))
        .where(Mascota.id == mascota_id)
    )
    mascota = result.scalar_one_or_none()

    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    return MascotaDetalle(
        id=mascota.id,
        tipo_mascota=mascota.tipo_mascota,
        nombre=mascota.nombre,
        raza=mascota.raza,
        edad=mascota.edad,
        vacunas=mascota.vacunas,
        notas=mascota.notas,
        foto=mascota.foto,
        usuario_id=mascota.usuario_id,
        responsable=ResponsableMascotaRead(
            id=mascota.usuario.id,
            nombre=mascota.usuario.nombre,
            email=mascota.usuario.email,
            telefono=mascota.usuario.telefono
        )
    )