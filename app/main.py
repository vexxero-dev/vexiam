from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.domains.identity.router import router as identity_router
from app.domains.identity.sync_router import router as identity_sync_router
from app.domains.organizations.router import router as organization_router
from app.domains.locations.router import router as location_router
from app.domains.applications.router import router as application_router
from app.domains.licensing.router import router as licensing_router
from app.core.security import get_public_key_pem, get_jwk
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.seeds import seed_vexxero_defaults
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically synchronize schema models on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure recently added schema columns exist in existing deployments
        from sqlalchemy import text
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS identity_version INTEGER NOT NULL DEFAULT 1;"))
        await conn.execute(text("ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE';"))
        await conn.execute(text("ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS membership_version INTEGER NOT NULL DEFAULT 1;"))
        await conn.execute(text("ALTER TABLE application_roles ADD COLUMN IF NOT EXISTS role_version INTEGER NOT NULL DEFAULT 1;"))
        await conn.execute(text("ALTER TABLE application_assignments ADD COLUMN IF NOT EXISTS assignment_version INTEGER NOT NULL DEFAULT 1;"))
        await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_sequence INTEGER NOT NULL DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS location_id UUID NULL;"))
    
    # Automatically seed official Vexxero ecosystem apps and default plans
    async with AsyncSessionLocal() as session:
        await seed_vexxero_defaults(session)
        
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

import secrets

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_origin_regex=r"^https:\/\/([a-zA-Z0-9-]+\.)*vexxero\.com$|^https:\/\/([a-zA-Z0-9-]+\.)*up\.railway\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(identity_router, prefix=settings.API_V1_STR)
app.include_router(identity_sync_router, prefix=settings.API_V1_STR)
app.include_router(organization_router, prefix=settings.API_V1_STR)
app.include_router(location_router, prefix=settings.API_V1_STR)
app.include_router(application_router, prefix=settings.API_V1_STR)
app.include_router(licensing_router, prefix=settings.API_V1_STR)


from app.domains.identity.models import User, UserProfile, UserCredential
from app.domains.organizations.models import Organization, OrganizationMember, OrganizationInvitation
from app.domains.locations.models import Location, LocationApplication
from app.domains.licensing.models import Device, DeviceLicense
from app.domains.subscriptions.models import Subscription
from sqlalchemy import delete
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Header, HTTPException, status


@app.post("/api/v1/system/reset-data", tags=["System"])
async def reset_system_data(
    x_secret_key: str = Header(..., alias="X-Secret-Key"),
    db: AsyncSession = Depends(get_db),
):
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System reset endpoint is disabled outside development mode.",
        )

    if not secrets.compare_digest(x_secret_key, settings.SECRET_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid administrative secret key.",
        )

    # Delete transactional and user data in order of foreign key dependency
    await db.execute(delete(DeviceLicense))
    await db.execute(delete(Device))
    await db.execute(delete(Subscription))
    await db.execute(delete(OrganizationInvitation))
    await db.execute(delete(OrganizationMember))
    await db.execute(delete(Organization))
    await db.execute(delete(UserCredential))
    await db.execute(delete(UserProfile))
    await db.execute(delete(User))
    await db.commit()

    # Re-seed default official ecosystem apps and plans
    await seed_vexxero_defaults(db)

    return {"status": "success", "message": "All VEX IAM user, organization, and device data has been reset."}


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.get("/.well-known/jwks.json", tags=["OAuth & OIDC"])
async def get_jwks():
    """Returns the RFC 8037 compliant OKP JWK set for verifying Ed25519 signatures."""
    return {"keys": [get_jwk()]}
