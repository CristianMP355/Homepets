import re
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func
from backend.database.database import get_db, engine, Base
from backend.database.models import Anfitrion, Usuario, FotoEspacio
from backend.utils.jwt_config import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from backend.schemas import (
    AnfitrionRead,
    AnfitrionListItem,
    AnfitrionDetalle,
    FotoEspacioRead,
)
from backend.routers import usuarios
from backend.routers import mascotas
from backend.routers import mensajes
from backend.routers import solicitudes


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

UPLOAD_DIR_ANFITRIONES = Path("static/uploads/anfitriones")
UPLOAD_DIR_ESPACIOS = Path("static/uploads/espacios")

UPLOAD_DIR_ANFITRIONES.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR_ESPACIOS.mkdir(parents=True, exist_ok=True)


_CON_TILDE = "áàäâãéèëêíìïîóòöôõúùüûñç"
_SIN_TILDE = "aaaaaeeeeiiiiooooouuuunc"


def normalizar_texto(texto: str) -> str:
    """minúsculas y sin tildes (Bogotá -> bogota)."""
    texto = (texto or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def sql_normalizado(columna):
    """Equivalente SQL de normalizar_texto() usando funciones nativas (lower + translate)."""
    return func.translate(func.lower(func.coalesce(columna, "")), _CON_TILDE, _SIN_TILDE)


def eliminar_archivo_si_existe(ruta_relativa: str | None):
    if not ruta_relativa:
        return

    ruta_limpia = ruta_relativa.lstrip("/")
    ruta_archivo = Path(ruta_limpia)

    if ruta_archivo.exists() and ruta_archivo.is_file():
        ruta_archivo.unlink()


def validar_imagen(foto: UploadFile):
    if not foto.filename:
        raise HTTPException(status_code=400, detail="Debes seleccionar una imagen")

    content_type = foto.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen válida")

    extension = Path(foto.filename).suffix.lower()
    if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagen no permitido. Usa JPG, JPEG, PNG o WEBP"
        )
    return extension


async def guardar_archivo_imagen(upload: UploadFile, carpeta: Path, prefijo: str) -> str:
    extension = validar_imagen(upload)
    nombre_archivo = f"{prefijo}_{uuid4().hex}{extension}"
    ruta_archivo = carpeta / nombre_archivo

    contenido = await upload.read()
    with open(ruta_archivo, "wb") as f:
        f.write(contenido)

    if carpeta.name == "anfitriones":
        return f"/static/uploads/anfitriones/{nombre_archivo}"
    return f"/static/uploads/espacios/{nombre_archivo}"


def create_app() -> FastAPI:
    app = FastAPI(title="HuellaHome API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    templates = Jinja2Templates(directory="backend/templates")
    # Las fotos subidas se guardan en ./static/uploads; se montan antes que /static para que tengan prioridad.
    app.mount("/static/uploads", StaticFiles(directory="static/uploads"), name="uploads")
    app.mount("/static", StaticFiles(directory="backend/static"), name="static")

    app.include_router(usuarios.router)
    app.include_router(mascotas.router)
    app.include_router(mensajes.router)
    app.include_router(solicitudes.router)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/auth", response_class=HTMLResponse)
    async def auth(request: Request):
        return templates.TemplateResponse("auth.html", {"request": request})

    @app.get("/perfil-usuario", response_class=HTMLResponse)
    async def perfil_usuario(request: Request):
        return templates.TemplateResponse("perfil-usuario.html", {"request": request})

    @app.get("/perfil-mascota", response_class=HTMLResponse)
    async def perfil_mascota(request: Request):
        return templates.TemplateResponse("perfil-mascota.html", {"request": request})

    @app.get("/detalle-mascota", response_class=HTMLResponse)
    async def detalle_mascota(request: Request):
        return templates.TemplateResponse("detalle-mascota.html", {"request": request})

    @app.get("/perfil-anfitrion", response_class=HTMLResponse)
    async def perfil_anfitrion(request: Request):
        return templates.TemplateResponse("perfil-anfitrion.html", {"request": request})

    @app.get("/detalle-anfitrion", response_class=HTMLResponse)
    async def detalle_anfitrion(request: Request):
        return templates.TemplateResponse("detalle-anfitrion.html", {"request": request})

    @app.get("/tips", response_class=HTMLResponse)
    async def tips(request: Request):
        return templates.TemplateResponse("tips.html", {"request": request})
    
    @app.get("/perfil-publico", response_class=HTMLResponse)
    async def perfil_publico_page(request: Request):
        return templates.TemplateResponse("perfil-publico.html", {"request": request})

    @app.get("/chat", response_class=HTMLResponse)
    async def chat(request: Request):
        return templates.TemplateResponse("chat.html", {"request": request})
        

    @app.get("/api/status")
    async def api_status():
        return {"message": "HuellaHome API con PostgreSQL funcionando"}

    @app.post("/anfitriones", response_model=AnfitrionRead, status_code=201)
    async def crear_anfitrion(
        usuario_id: int = Form(...),
        descripcion: str = Form(...),
        direccion: str = Form(...),
        fechas_no_disponibles: str = Form(""),
        foto: UploadFile = File(...),
        fotos_espacio: list[UploadFile] | None = File(default=None),
        db: AsyncSession = Depends(get_db)
    ):
        result_usuario = await db.execute(
            select(Usuario).where(Usuario.id == usuario_id)
        )
        usuario = result_usuario.scalar_one_or_none()

        if not usuario:
            raise HTTPException(status_code=404, detail="El usuario no existe")

        result_anfitrion = await db.execute(
            select(Anfitrion).where(Anfitrion.usuario_id == usuario_id)
        )
        anfitrion_existente = result_anfitrion.scalar_one_or_none()

        if anfitrion_existente:
            raise HTTPException(status_code=400, detail="Este usuario ya tiene perfil de anfitrión")

        fotos_validas = [f for f in (fotos_espacio or []) if f and f.filename]
        if not fotos_validas:
            raise HTTPException(
                status_code=400,
                detail="Debes subir al menos 1 foto de tu hogar/espacio para crear el perfil de anfitrión"
            )
        if len(fotos_validas) > 5:
            raise HTTPException(status_code=400, detail="Solo puedes subir máximo 5 fotos del espacio")
        for f in fotos_validas:
            validar_imagen(f)

        ruta_foto_principal = await guardar_archivo_imagen(
            foto,
            UPLOAD_DIR_ANFITRIONES,
            f"anfitrion_{usuario_id}"
        )

        nuevo = Anfitrion(
            usuario_id=usuario_id,
            descripcion=descripcion,
            direccion=direccion,
            foto=ruta_foto_principal,
            fechas_no_disponibles=fechas_no_disponibles
        )

        if usuario.rol != "admin":  # no degradar al administrador
            usuario.rol = "anfitrion"

        db.add(nuevo)
        await db.flush()

        for foto_item in fotos_validas:
            ruta_foto_espacio = await guardar_archivo_imagen(
                foto_item,
                UPLOAD_DIR_ESPACIOS,
                f"espacio_{usuario_id}"
            )
            db.add(FotoEspacio(anfitrion_id=nuevo.id, ruta_foto=ruta_foto_espacio))

        await db.commit()
        await db.refresh(nuevo)

        return nuevo

    @app.patch("/anfitriones/{anfitrion_id}", response_model=AnfitrionRead)
    async def actualizar_anfitrion(
        anfitrion_id: int,
        descripcion: str = Form(...),
        direccion: str = Form(...),
        fechas_no_disponibles: str | None = Form(None),
        foto: UploadFile | None = File(None),
        fotos_espacio: list[UploadFile] | None = File(default=None),
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        result = await db.execute(
            select(Anfitrion)
            .options(selectinload(Anfitrion.fotos_espacio))
            .where(Anfitrion.id == anfitrion_id)
        )
        anfitrion = result.scalar_one_or_none()

        if not anfitrion:
            raise HTTPException(status_code=404, detail="Anfitrión no encontrado")

        user_role = current_user.get("rol")
        user_id_raw = current_user.get("id")

        if user_id_raw is None:
            raise HTTPException(status_code=401, detail="Token inválido: no contiene id")

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Token inválido: id no válido")

        if user_role != "admin" and user_id != anfitrion.usuario_id:
            raise HTTPException(status_code=403, detail="No tienes permiso para editar este perfil")

        nuevas_fotos = [f for f in (fotos_espacio or []) if f and f.filename]
        total_fotos = len(anfitrion.fotos_espacio) + len(nuevas_fotos)
        if total_fotos == 0:
            raise HTTPException(
                status_code=400,
                detail="Debes tener al menos 1 foto de tu hogar/espacio en el perfil de anfitrión"
            )
        if total_fotos > 5:
            raise HTTPException(
                status_code=400,
                detail=f"Máximo 5 fotos del espacio (ya tienes {len(anfitrion.fotos_espacio)})"
            )
        for f in nuevas_fotos:
            validar_imagen(f)

        anfitrion.descripcion = descripcion.strip()
        anfitrion.direccion = direccion.strip()
        anfitrion.fechas_no_disponibles = (
            fechas_no_disponibles.strip()
            if fechas_no_disponibles and fechas_no_disponibles.strip()
            else None
        )

        if foto and foto.filename:
            nueva_ruta_foto = await guardar_archivo_imagen(
                foto,
                UPLOAD_DIR_ANFITRIONES,
                f"anfitrion_{anfitrion.usuario_id}"
            )
            eliminar_archivo_si_existe(anfitrion.foto)
            anfitrion.foto = nueva_ruta_foto

        for foto_item in nuevas_fotos:
            ruta = await guardar_archivo_imagen(
                foto_item, UPLOAD_DIR_ESPACIOS, f"espacio_{anfitrion.usuario_id}"
            )
            db.add(FotoEspacio(anfitrion_id=anfitrion.id, ruta_foto=ruta))

        await db.commit()
        await db.refresh(anfitrion)

        return anfitrion

    @app.get("/usuarios/{usuario_id}/anfitrion", response_model=AnfitrionRead)
    async def obtener_anfitrion_por_usuario(usuario_id: int, db: AsyncSession = Depends(get_db)):
        result = await db.execute(
            select(Anfitrion).where(Anfitrion.usuario_id == usuario_id)
        )
        anfitrion = result.scalar_one_or_none()

        if not anfitrion:
            raise HTTPException(status_code=404, detail="Este usuario no tiene perfil de anfitrión")

        return anfitrion

    @app.get("/anfitriones", response_model=list[AnfitrionListItem])
    async def listar_anfitriones(
        ciudad: str | None = None,
        db: AsyncSession = Depends(get_db)
    ):
        query = (
            select(Anfitrion)
            .options(selectinload(Anfitrion.usuario))
        )

        if ciudad and ciudad.strip():
            # Búsqueda insensible a mayúsculas y tildes sin depender de la extensión "unaccent"
            termino = normalizar_texto(ciudad)
            termino = termino.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
            query = query.where(
                sql_normalizado(Anfitrion.direccion).like(f"%{termino}%")
            )

        query = query.order_by(Anfitrion.id.asc())

        result = await db.execute(query)
        anfitriones = result.scalars().all()

        respuesta = []
        for anfitrion in anfitriones:
            respuesta.append(
                AnfitrionListItem(
                    id=anfitrion.id,
                    usuario_id=anfitrion.usuario_id,
                    nombre=anfitrion.usuario.nombre if anfitrion.usuario else "Anfitrión",
                    email=anfitrion.usuario.email if anfitrion.usuario else "sincorreo@homepets.com",
                    telefono=anfitrion.usuario.telefono if anfitrion.usuario else None,
                    descripcion=anfitrion.descripcion,
                    direccion=anfitrion.direccion,
                    foto=anfitrion.foto,
                    foto_user=anfitrion.usuario.foto_user if anfitrion.usuario else None,
                    fechas_no_disponibles=anfitrion.fechas_no_disponibles
                )
            )

        return respuesta

    @app.delete("/anfitriones/{anfitrion_id}", status_code=200)
    async def eliminar_anfitrion(
        anfitrion_id: int,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if current_user.get("rol") != "admin":
            raise HTTPException(status_code=403, detail="Solo el administrador puede eliminar anfitriones")

        result = await db.execute(
            select(Anfitrion)
            .options(selectinload(Anfitrion.fotos_espacio))
            .where(Anfitrion.id == anfitrion_id)
        )
        anfitrion = result.scalar_one_or_none()

        if not anfitrion:
            raise HTTPException(status_code=404, detail="Anfitrión no encontrado")

        eliminar_archivo_si_existe(anfitrion.foto)

        for foto in anfitrion.fotos_espacio:
            eliminar_archivo_si_existe(foto.ruta_foto)

        await db.delete(anfitrion)
        await db.commit()

        return {"message": "Anfitrión eliminado correctamente"}
    

    
    @app.get("/ciudades-sugeridas")
    async def sugerir_ciudades(
        q: str,
        db: AsyncSession = Depends(get_db)
    ):
        normalizar = normalizar_texto
        texto_busqueda = q.strip()

        if not texto_busqueda:
            return []

        result = await db.execute(
            select(Anfitrion.direccion).limit(100)
        )
        direcciones = result.scalars().all()

        ciudades = set()

        for direccion in direcciones:
            if not direccion:
                continue

            # "Calle 1 #2-3, Barrio, Ciudad (Depto)" -> se sugieren barrio y ciudad (sin la calle)
            partes = [p.strip() for p in direccion.split(",") if p.strip()]
            candidatas = partes[1:] if len(partes) > 1 else partes[-1:]
            for parte in candidatas:
                ciudad = re.sub(r"\s*\(.*?\)\s*", "", parte).strip()
                if len(partes) == 1 and re.search(r"[#\d]", ciudad):
                    # Dirección sin comas ("Calle 25C #35-52 Olimpico Palmira"): usar la última palabra
                    ciudad = ciudad.split()[-1]
                if ciudad and not re.search(r"[#\d]", ciudad):
                    ciudades.add(ciudad)

        q_normalizada = normalizar(texto_busqueda)

        ciudades_filtradas = [
            ciudad for ciudad in ciudades
            if q_normalizada in normalizar(ciudad)
        ]

        ciudades_filtradas.sort()

        return ciudades_filtradas[:5]

    @app.get("/anfitriones/{anfitrion_id}/detalle", response_model=AnfitrionDetalle)
    async def obtener_detalle_anfitrion(anfitrion_id: int, db: AsyncSession = Depends(get_db)):
        result = await db.execute(
            select(Anfitrion)
            .options(
                selectinload(Anfitrion.usuario),
                selectinload(Anfitrion.fotos_espacio)
            )
            .where(Anfitrion.id == anfitrion_id)
        )
        anfitrion = result.scalar_one_or_none()

        if not anfitrion:
            raise HTTPException(status_code=404, detail="Anfitrión no encontrado")

        return AnfitrionDetalle(
            id=anfitrion.id,
            usuario_id=anfitrion.usuario_id,
            nombre=anfitrion.usuario.nombre if anfitrion.usuario else "Anfitrión",
            email=anfitrion.usuario.email if anfitrion.usuario else "sincorreo@homepets.com",
            telefono=anfitrion.usuario.telefono if anfitrion.usuario else None,
            descripcion=anfitrion.descripcion,
            direccion=anfitrion.direccion,
            foto=anfitrion.foto,
            foto_user=anfitrion.usuario.foto_user if anfitrion.usuario else None,
            fechas_no_disponibles=anfitrion.fechas_no_disponibles,
            fotos_espacio=[
                FotoEspacioRead(id=f.id, ruta_foto=f.ruta_foto)
                for f in anfitrion.fotos_espacio
            ]
        )

    return app


app = create_app()
