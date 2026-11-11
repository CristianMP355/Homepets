from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.database import get_db
from backend.database.models import Mascota
from backend.schemas import (
    MascotaCreate,
    MascotaRead,
    MascotaDetalle,
    ResponsableMascotaRead,
    MascotaComunidadRead,
)
from backend.utils.jwt_config import get_current_user


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


@router.get("/mascotas", response_model=list[MascotaRead])
async def listar_todas_mascotas(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede ver todas las mascotas")

    result = await db.execute(select(Mascota).order_by(Mascota.id.asc()))
    return result.scalars().all()


@router.get("/mascotas/comunidad", response_model=list[MascotaComunidadRead])
async def listar_mascotas_comunidad(db: AsyncSession = Depends(get_db)):
    """Mascotas publicadas en el sistema (público). Solo expone el nombre del dueño."""
    result = await db.execute(
        select(Mascota).options(selectinload(Mascota.usuario)).order_by(Mascota.id.desc())
    )
    return [
        MascotaComunidadRead(
            id=m.id,
            tipo_mascota=m.tipo_mascota,
            nombre=m.nombre,
            raza=m.raza,
            edad=m.edad,
            foto=m.foto,
            usuario_id=m.usuario_id,
            dueno_nombre=m.usuario.nombre if m.usuario else "Sin responsable",
        )
        for m in result.scalars().all()
    ]


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


@router.delete("/mascotas/{mascota_id}", status_code=200)
async def eliminar_mascota(
    mascota_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    mascota = await db.get(Mascota, mascota_id)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    try:
        user_id = int(current_user.get("id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido: id no válido")

    if current_user.get("rol") != "admin" and user_id != mascota.usuario_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta mascota")

    await db.delete(mascota)
    await db.commit()
    return {"mensaje": "Mascota eliminada correctamente"}


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