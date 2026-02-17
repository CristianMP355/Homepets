from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine, Base
from routers import usuarios

def create_app() -> FastAPI:
    app = FastAPI(title="HuellaHome API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(usuarios.router)

    @app.on_event("startup")
    async def startup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @app.get("/")
    async def root():
        return {"message": "HuellaHome API con PostgreSQL funcionando"}

    return app


app = create_app()