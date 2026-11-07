from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.domains.identity.router import router as identity_router
from app.domains.organizations.router import router as organization_router
from app.domains.applications.router import router as application_router
from app.domains.licensing.router import router as licensing_router
from app.core.security import get_public_key_pem
from app.core.database import engine, Base
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create missing database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Vexxero Identity & Access Management (VEX IAM) API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(identity_router, prefix=settings.API_V1_STR)
app.include_router(organization_router, prefix=settings.API_V1_STR)
app.include_router(application_router, prefix=settings.API_V1_STR)
app.include_router(licensing_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.get("/.well-known/jwks.json", tags=["OAuth & OIDC"])
async def get_jwks():
    """Returns the public key for verifying Ed25519 signatures."""
    pub_pem = get_public_key_pem().decode("utf-8")
    return {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "use": "sig",
                "alg": settings.ALGORITHM,
                "x5c": [pub_pem],
            }
        ]
    }
