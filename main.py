from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import tecnicos, clientes, ordenes, contratos, estadisticas, webhooks, usuarios, configuracion
from auth import router as auth_router

app = FastAPI(title="TecnoOP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tecnicos.router, prefix="/tecnicos", tags=["tecnicos"])
app.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
app.include_router(ordenes.router, prefix="/ordenes", tags=["ordenes"])
app.include_router(contratos.router, prefix="/contratos", tags=["contratos"])
app.include_router(estadisticas.router, prefix="/estadisticas", tags=["estadisticas"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
app.include_router(configuracion.router, prefix="/configuracion", tags=["configuracion"])


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"status": "ok", "app": "TecnoOP API v1.0"}
