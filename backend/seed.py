"""
Poblado de datos de prueba para HomePets / HuellaHome.

Uso (desde la raíz del proyecto):
    .venv\\Scripts\\python.exe -m backend.seed

Es idempotente: si un usuario de prueba (por email) ya existe, se omite.
Todos los usuarios de prueba tienen la contraseña: homepets123
"""
import asyncio

from sqlalchemy import select

from backend.database.database import SessionLocal
from backend.database.models import Usuario, Anfitrion, FotoEspacio, Mascota

PASSWORD_PRUEBA = "homepets123"
IMG = "/static/img"
FOTOS = "/static/FOTOS%20PRUEBAS"

DATOS = [
    {
        "usuario": {
            "nombre": "Valentina Rojas",
            "email": "valentina.rojas@example.com",
            "telefono": "+57 300 111 2201",
            "direccion": "Cra. 5 #12-40, Cali",
        },
        "anfitrion": {
            "descripcion": "Veterinaria de profesión y amante de los perros grandes. "
                           "Tengo un patio amplio con césped y paseo a tu peludo dos veces al día.",
            "direccion": "Cra. 5 #12-40, San Antonio, Cali",
            "foto": f"{IMG}/anfitrion.jpg",
            "espacios": [f"{IMG}/registro-mascotas.png"],
        },
        "mascota": {
            "tipo_mascota": "Perro", "nombre": "Kalan", "raza": "Golden Retriever",
            "edad": "3 años", "vacunas": "Rabia, parvovirus, moquillo",
            "notas": "Muy juguetón, ama el agua y las pelotas.",
            "foto": f"{FOTOS}/Kalan.jpg",
        },
    },
    {
        "usuario": {
            "nombre": "Andrés Gómez",
            "email": "andres.gomez@example.com",
            "telefono": "+57 300 111 2202",
            "direccion": "Cl. 10 #43-15, Medellín",
        },
        "anfitrion": {
            "descripcion": "Trabajo desde casa, así que tu gato nunca estará solo. "
                           "Apartamento tranquilo, con mallas de seguridad en todas las ventanas.",
            "direccion": "Cl. 10 #43-15, El Poblado, Medellín",
            "foto": f"{IMG}/usuario1.jpg",
            "espacios": [],
        },
        "mascota": {
            "tipo_mascota": "Gato", "nombre": "Mompi", "raza": "Criollo",
            "edad": "2 años", "vacunas": "Triple felina",
            "notas": "Tímido al principio, luego muy cariñoso.",
            "foto": f"{FOTOS}/mompi.jpg",
        },
    },
    {
        "usuario": {
            "nombre": "Mónica Herrera",
            "email": "monica.herrera@example.com",
            "telefono": "+57 300 111 2203",
            "direccion": "Av. 3N #25-60, Palmira",
        },
        "anfitrion": {
            "descripcion": "Pensionada con todo el día libre y mucho amor para dar. "
                           "Cuido perros y gatos como si fueran míos, con comida casera si lo autorizas.",
            "direccion": "Av. 3N #25-60, Palmira (Valle)",
            "foto": f"{IMG}/monica-anfitriona.jpg",
            "espacios": [],
        },
        "mascota": {
            "tipo_mascota": "Perro", "nombre": "Tara", "raza": "Beagle",
            "edad": "6 años", "vacunas": "Al día",
            "notas": "Le encanta olfatear todo; necesita correa en los paseos.",
            "foto": f"{FOTOS}/tara.jpg",
        },
    },
    {
        "usuario": {
            "nombre": "Santiago Ruiz",
            "email": "santiago.ruiz@example.com",
            "telefono": "+57 300 111 2204",
            "direccion": "Cl. 72 #11-20, Bogotá",
        },
        "anfitrion": {
            "descripcion": "Estudiante de zootecnia. Disponible noches y fines de semana; "
                           "experiencia con conejos, hámsters y peces además de perros.",
            "direccion": "Cl. 72 #11-20, Chapinero, Bogotá",
            "foto": f"{IMG}/usuario2.png",
            "espacios": [],
        },
        "mascota": {
            "tipo_mascota": "Perro", "nombre": "Fama", "raza": "French Poodle",
            "edad": "4 años", "vacunas": "Rabia y polivalente",
            "notas": "Muy sociable con otros perros.",
            "foto": f"{FOTOS}/fama121.jpg",
        },
    },
    {
        "usuario": {
            "nombre": "Laura Castaño",
            "email": "laura.castano@example.com",
            "telefono": "+57 300 111 2205",
            "direccion": "Cra. 9 #4-30, Popayán",
        },
        "anfitrion": {
            "descripcion": "Casa campestre con jardín cerrado, ideal para perros con mucha energía. "
                           "Te envío fotos y videos diarios de tu mascota.",
            "direccion": "Cra. 9 #4-30, Centro, Popayán (Cauca)",
            "foto": f"{IMG}/anfitrion.jpg",
            "espacios": [],
        },
        "mascota": {
            "tipo_mascota": "Gato", "nombre": "Luna", "raza": "Siamés",
            "edad": "1 año", "vacunas": "Primera dosis triple felina",
            "notas": "Curiosa y conversadora; no le gustan los perros.",
            "foto": f"{FOTOS}/mascota%20alejandra%20gomez.jpg",
        },
    },
]


async def seed() -> None:
    creados = 0
    async with SessionLocal() as db:
        for item in DATOS:
            u = item["usuario"]
            existe = await db.scalar(select(Usuario).where(Usuario.email == u["email"]))
            if existe:
                print(f"  = ya existe: {u['email']} (omitido)")
                continue

            usuario = Usuario(
                **u,
                password_hash=Usuario.hash_password(PASSWORD_PRUEBA),
                rol="anfitrion",
            )
            db.add(usuario)
            await db.flush()

            a = item["anfitrion"]
            anfitrion = Anfitrion(
                usuario_id=usuario.id,
                descripcion=a["descripcion"],
                direccion=a["direccion"],
                foto=a["foto"],
            )
            db.add(anfitrion)
            await db.flush()
            for ruta in a["espacios"]:
                db.add(FotoEspacio(anfitrion_id=anfitrion.id, ruta_foto=ruta))

            db.add(Mascota(**item["mascota"], usuario_id=usuario.id))
            creados += 1
            print(f"  + {u['nombre']} <{u['email']}> con anfitrión y mascota {item['mascota']['nombre']}")

        await db.commit()
    print(f"Listo: {creados} usuarios nuevos. Contraseña de prueba: {PASSWORD_PRUEBA}")


if __name__ == "__main__":
    asyncio.run(seed())
