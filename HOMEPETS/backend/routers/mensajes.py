from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, and_, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from backend.database.database import get_db
from backend.database.models import Mensaje, Usuario
from schemas import MensajeCreate, MensajeRead, ChatResumen, NoLeidosOut
from utils.jwt_config import get_current_user

router = APIRouter(tags=["Mensajes"])


@router.post("/mensajes", response_model=MensajeRead)
async def enviar_mensaje(
    payload: MensajeCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    emisor_id = current_user.get("id")

    if emisor_id is None:
        raise HTTPException(status_code=401, detail="Token inválido: no contiene id")

    try:
        emisor_id = int(emisor_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido: id no válido")

    if emisor_id == payload.receptor_id:
        raise HTTPException(status_code=400, detail="No puedes enviarte mensajes a ti mismo")

    contenido = payload.contenido.strip()
    if not contenido:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    result_receptor = await db.execute(
        select(Usuario).where(Usuario.id == payload.receptor_id)
    )
    receptor = result_receptor.scalar_one_or_none()

    if not receptor:
        raise HTTPException(status_code=404, detail="El usuario receptor no existe")

    nuevo = Mensaje(
        emisor_id=emisor_id,
        receptor_id=payload.receptor_id,
        contenido=contenido,
        leido=False
    )

    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)

    return nuevo


@router.get("/mensajes/conversacion/{otro_usuario_id}", response_model=list[MensajeRead])
async def obtener_conversacion(
    otro_usuario_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    usuario_id = current_user.get("id")

    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Token inválido: no contiene id")

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido: id no válido")

    # Verificar que el otro usuario exista
    result_otro = await db.execute(
        select(Usuario).where(Usuario.id == otro_usuario_id)
    )
    otro_usuario = result_otro.scalar_one_or_none()

    if not otro_usuario:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    # Marcar como leídos los mensajes que el otro usuario le envió al actual
    await db.execute(
        update(Mensaje)
        .where(
            Mensaje.emisor_id == otro_usuario_id,
            Mensaje.receptor_id == usuario_id,
            Mensaje.leido == False
        )
        .values(
            leido=True,
            fecha_lectura=datetime.utcnow()
        )
    )
    await db.commit()

    # Obtener conversación completa
    result = await db.execute(
        select(Mensaje)
        .where(
            or_(
                and_(Mensaje.emisor_id == usuario_id, Mensaje.receptor_id == otro_usuario_id),
                and_(Mensaje.emisor_id == otro_usuario_id, Mensaje.receptor_id == usuario_id)
            )
        )
        .order_by(Mensaje.fecha_envio.asc(), Mensaje.id.asc())
    )

    mensajes = result.scalars().all()
    return mensajes


@router.get("/mensajes/mis-chats", response_model=list[ChatResumen])
async def obtener_mis_chats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    usuario_id = current_user.get("id")

    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Token inválido: no contiene id")

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido: id no válido")

    # Todos los mensajes en los que participa el usuario, del más reciente al más antiguo
    result = await db.execute(
        select(Mensaje)
        .where(
            or_(
                Mensaje.emisor_id == usuario_id,
                Mensaje.receptor_id == usuario_id
            )
        )
        .order_by(desc(Mensaje.fecha_envio), desc(Mensaje.id))
    )
    mensajes = result.scalars().all()

    chats_dict = {}

    for mensaje in mensajes:
        otro_usuario_id = mensaje.receptor_id if mensaje.emisor_id == usuario_id else mensaje.emisor_id

        if otro_usuario_id in chats_dict:
            continue

        result_usuario = await db.execute(
            select(Usuario).where(Usuario.id == otro_usuario_id)
        )
        otro_usuario = result_usuario.scalar_one_or_none()

        if not otro_usuario:
            continue

        # Contar mensajes no leídos que ese usuario le ha enviado al usuario actual
        result_no_leidos = await db.execute(
            select(func.count(Mensaje.id))
            .where(
                Mensaje.emisor_id == otro_usuario_id,
                Mensaje.receptor_id == usuario_id,
                Mensaje.leido == False
            )
        )
        no_leidos = result_no_leidos.scalar() or 0

        chats_dict[otro_usuario_id] = ChatResumen(
            usuario_id=otro_usuario.id,
            nombre=otro_usuario.nombre,
            email=otro_usuario.email,
            foto_user=otro_usuario.foto_user,
            ultimo_mensaje=mensaje.contenido,
            fecha_envio=mensaje.fecha_envio,
            no_leidos=no_leidos
        )

    return list(chats_dict.values())


@router.get("/mensajes/no-leidos", response_model=NoLeidosOut)
async def contar_no_leidos(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    usuario_id = current_user.get("id")

    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Token inválido: no contiene id")

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido: id no válido")

    result = await db.execute(
        select(func.count(Mensaje.id))
        .where(
            Mensaje.receptor_id == usuario_id,
            Mensaje.leido == False
        )
    )
    total_no_leidos = result.scalar() or 0

    return NoLeidosOut(total_no_leidos=total_no_leidos)