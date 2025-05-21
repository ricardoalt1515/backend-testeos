# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.routes import chat, documents, feedback, auth
from app.config import settings

# Importar middlewares
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware

# Configuración de logging
from app.core.logging_config import get_logger

# Configurar logging
logger = get_logger("hydrous")

# Asegurarse de que el directorio de uploads existe
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

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
    expose_headers=["Content-Disposition"],
    allow_origin_regex=r"https://.*\.hostingersite\.com$|https://ricardoalt1515\.github\.io$|http://localhost:.*$|https://(www\.)?h2oassistant\.com$",
)

# Middleware de autenticación
app.add_middleware(AuthMiddleware)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware, requests_per_minute=60, burst_size=10, per_user=True
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
