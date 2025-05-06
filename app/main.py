# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.routes import chat, documents, feedback, auth
from app.config import settings

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("hydrous")

# Inicializar aplicación
app = FastAPI(
    title="Hydrous AI Chatbot API",
    description="Backend para el chatbot de soluciones de agua Hydrous",
    version="1.0.0",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # Importante para las descargas
)

# Incluir rutas
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(
    documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["documents"]
)
app.include_router(
    feedback.router, prefix=f"{settings.API_V1_STR}/feedback", tags=["feedback"]
)
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])


@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return {"status": "ok", "version": app.version}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
