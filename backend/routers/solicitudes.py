import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.database import get_db
from backend.database.models import Anfitrion, SolicitudReserva, Mensaje
from backend.schemas import (
    FechasOcupadasRead,
    SolicitudCreate,
    SolicitudRead,
    SolicitudRecibidaRead,
    SolicitudEstadoUpdate,
)
from backend.utils.jwt_config import get_current_user

router = APIRouter(tags=["Solicitudes"])


def _expandir_rango(inicio: date, fin: date) -> list[str]:
    fechas: list[str] = []
    actual = inicio
    while actual <= fin:
        fechas.append(actual.strftime("%Y-%m-%d"))
        actual += timedelta(days=1)
    return fechas


def _parsear_fechas_no_disponibles(valor: str | None) -> list[str]:
    if not valor:
        return []
    valor = valor.strip()
    if not valor:
        return []
    try:
        parsed = json.loads(valor)
        if isinstance(parsed, list):
            return [str(f).strip() for f in parsed if f]
    except Exception:
        pass
    # Acepta separadores por coma o espacios (formato antiguo escrito a mano)
    return [f.strip() for f in valor.replace(",", " ").split() if f.strip()]


@router.get("/anfitriones/{anfitrion_id}/fechas-ocupadas", response_model=FechasOcupadasRead)
async def obtener_fechas_ocupadas(
    anfitrion_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Anfitrion).where(Anfitrion.id == anfitrion_id)
    )
    anfitrion = result.scalar_one_or_none()

    if not anfitrion:
        raise HTTPException(status_code=404, detail="Anfitrión no encontrado")

    fechas_no_disponibles = _parsear_fechas_no_disponibles(anfitrion.fechas_no_disponibles)

    result_sols = await db.execute(
        select(SolicitudReserva).where(
            SolicitudReserva.anfitrion_id == anfitrion_id,
            SolicitudReserva.estado.in_(["pendiente", "aceptada"])
        )
    )
    solicitudes = result_sols.scalars().all()

    pendientes: set[str] = set()
    confirmadas: set[str] = set()
    for sol in solicitudes:
        destino = confirmadas if sol.estado == "aceptada" else pendientes
        destino.update(_expandir_rango(sol.fecha_inicio, sol.fecha_fin))

    return FechasOcupadasRead(
        fechas_no_disponibles=fechas_no_disponibles,
        fechas_solicitadas=sorted(pendientes - confirmadas),
        fechas_confirmadas=sorted(confirmadas)
    )


_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _rango_legible(inicio: date, fin: date) -> str:
    """'del 10 al 12 de diciembre de 2026' / 'del 30 de diciembre de 2026 al 2 de enero de 2027'."""
    if inicio.year == fin.year and inicio.month == fin.month:
        return f"del {inicio.day} al {fin.day} de {_MESES[fin.month - 1]} de {fin.year}"
    if inicio.year == fin.year:
        return (f"del {inicio.day} de {_MESES[inicio.month - 1]} al "
                f"{fin.day} de {_MESES[fin.month - 1]} de {fin.year}")
    return (f"del {inicio.day} de {_MESES[inicio.month - 1]} de {inicio.year} al "
            f"{fin.day} de {_MESES[fin.month - 1]} de {fin.year}")


def _mensaje_solicitud(nombre_anfitrion: str, inicio: date, fin: date) -> str:
    noches = (fin - inicio).days
    duracion = f"{noches} noche{'s' if noches != 1 else ''}" if noches else "1 día"
    primer_nombre = (nombre_anfitrion or "").split(" ")[0] or "anfitrión"
    return (
        f"Hola {primer_nombre}, acabo de solicitar las fechas {_rango_legible(inicio, fin)} "
        f"({duracion}) para el cuidado de mi mascota. La solicitud queda pendiente de tu "
        f"confirmación. ¿Te gustaría saber algo sobre mi mascota?"
    )


def _usuario_id(current_user: dict) -> int:
    try:
        return int(current_user.get("id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido: id no válido")


@router.get("/anfitriones/{anfitrion_id}/solicitudes", response_model=list[SolicitudRecibidaRead])
async def listar_solicitudes_recibidas(
    anfitrion_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Solicitudes recibidas por un anfitrión. Solo el propio anfitrión o un admin."""
    anfitrion = await db.get(Anfitrion, anfitrion_id)
    if not anfitrion:
        raise HTTPException(status_code=404, detail="Anfitrión no encontrado")

    if current_user.get("rol") != "admin" and _usuario_id(current_user) != anfitrion.usuario_id:
        raise HTTPException(status_code=403, detail="No puedes ver las solicitudes de otro anfitrión")

    result = await db.execute(
        select(SolicitudReserva)
        .options(selectinload(SolicitudReserva.solicitante))
        .where(SolicitudReserva.anfitrion_id == anfitrion_id)
        .order_by(SolicitudReserva.fecha_inicio.asc())
    )

    return [
        SolicitudRecibidaRead(
            id=s.id,
            anfitrion_id=s.anfitrion_id,
            solicitante_id=s.solicitante_id,
            fecha_inicio=s.fecha_inicio,
            fecha_fin=s.fecha_fin,
            estado=s.estado,
            fecha_solicitud=s.fecha_solicitud,
            solicitante_nombre=s.solicitante.nombre if s.solicitante else "Usuario",
            solicitante_email=s.solicitante.email if s.solicitante else None,
            solicitante_telefono=s.solicitante.telefono if s.solicitante else None,
        )
        for s in result.scalars().all()
    ]


@router.patch("/solicitudes/{solicitud_id}/estado", response_model=SolicitudRead)
async def cambiar_estado_solicitud(
    solicitud_id: int,
    payload: SolicitudEstadoUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """El anfitrión (o un admin) confirma o rechaza una solicitud pendiente."""
    nuevo_estado = payload.estado.strip().lower()
    if nuevo_estado not in ("aceptada", "rechazada"):
        raise HTTPException(status_code=400, detail="Estado inválido. Usa 'aceptada' o 'rechazada'")

    solicitud = await db.get(SolicitudReserva, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    anfitrion = await db.get(Anfitrion, solicitud.anfitrion_id)
    if current_user.get("rol") != "admin" and _usuario_id(current_user) != anfitrion.usuario_id:
        raise HTTPException(status_code=403, detail="Solo el anfitrión puede responder esta solicitud")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"La solicitud ya fue {solicitud.estado}")

    if nuevo_estado == "aceptada":
        rango = set(_expandir_rango(solicitud.fecha_inicio, solicitud.fecha_fin))
        result = await db.execute(
            select(SolicitudReserva).where(
                SolicitudReserva.anfitrion_id == solicitud.anfitrion_id,
                SolicitudReserva.estado == "aceptada",
                SolicitudReserva.id != solicitud.id
            )
        )
        for otra in result.scalars().all():
            if rango & set(_expandir_rango(otra.fecha_inicio, otra.fecha_fin)):
                raise HTTPException(status_code=400, detail="Esas fechas se cruzan con otra reserva ya confirmada")

    solicitud.estado = nuevo_estado
    await db.commit()
    await db.refresh(solicitud)
    return solicitud


@router.post("/solicitudes", response_model=SolicitudRead, status_code=201)
async def crear_solicitud(
    payload: SolicitudCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    solicitante_id = int(current_user.get("id"))

    hoy = date.today()
    if payload.fecha_inicio < hoy:
        raise HTTPException(status_code=400, detail="La fecha de inicio no puede ser en el pasado")

    if payload.fecha_fin < payload.fecha_inicio:
        raise HTTPException(status_code=400, detail="La fecha de fin debe ser igual o posterior a la de inicio")

    result = await db.execute(
        select(Anfitrion).where(Anfitrion.id == payload.anfitrion_id)
    )
    anfitrion = result.scalar_one_or_none()

    if not anfitrion:
        raise HTTPException(status_code=404, detail="Anfitrión no encontrado")

    if anfitrion.usuario_id == solicitante_id:
        raise HTTPException(status_code=400, detail="No puedes solicitar tu propio perfil de anfitrión")

    # Impedir más de una solicitud pendiente del mismo usuario al mismo anfitrión
    result_dup = await db.execute(
        select(SolicitudReserva).where(
            SolicitudReserva.anfitrion_id == payload.anfitrion_id,
            SolicitudReserva.solicitante_id == solicitante_id,
            SolicitudReserva.estado == "pendiente"
        )
    )
    if result_dup.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Ya tienes una solicitud pendiente con este anfitrión. Espera a que sea respondida."
        )

    # Verificar solapamiento con fechas_no_disponibles del anfitrión
    fechas_no_disp = set(_parsear_fechas_no_disponibles(anfitrion.fechas_no_disponibles))
    rango = set(_expandir_rango(payload.fecha_inicio, payload.fecha_fin))

    if rango & fechas_no_disp:
        raise HTTPException(
            status_code=400,
            detail="El rango incluye fechas marcadas como no disponibles por el anfitrión"
        )

    # Verificar solapamiento con solicitudes pendientes o aceptadas existentes
    result_sols = await db.execute(
        select(SolicitudReserva).where(
            SolicitudReserva.anfitrion_id == payload.anfitrion_id,
            SolicitudReserva.estado.in_(["pendiente", "aceptada"])
        )
    )
    ocupadas: set[str] = set()
    for sol in result_sols.scalars().all():
        ocupadas.update(_expandir_rango(sol.fecha_inicio, sol.fecha_fin))

    if rango & ocupadas:
        raise HTTPException(
            status_code=400,
            detail="El rango incluye fechas ya solicitadas o reservadas"
        )

    nueva = SolicitudReserva(
        anfitrion_id=payload.anfitrion_id,
        solicitante_id=solicitante_id,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        estado="pendiente"
    )
    db.add(nueva)

    # Primer mensaje automático en el chat con el resumen de la solicitud
    await db.refresh(anfitrion, attribute_names=["usuario"])
    db.add(Mensaje(
        emisor_id=solicitante_id,
        receptor_id=anfitrion.usuario_id,
        contenido=_mensaje_solicitud(
            anfitrion.usuario.nombre if anfitrion.usuario else "",
            payload.fecha_inicio,
            payload.fecha_fin,
        ),
    ))

    await db.commit()
    await db.refresh(nueva)

    return nueva
