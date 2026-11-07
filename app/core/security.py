from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timezone, timedelta
import jwt
from typing import Optional, Dict, Any
from app.core.config import settings

ph = PasswordHasher()

# Generate or manage Ed25519 signing keys
_private_key = ed25519.Ed25519PrivateKey.generate()
_public_key = _private_key.public_key()


def hash_password(password: str) -> str:
    """Hashes a password with Argon2id."""
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verifies a plain password against an Argon2id hash."""
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False


def get_private_key_pem() -> bytes:
    return _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_public_key_pem() -> bytes:
    return _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "vex-iam",
    }
    if claims:
        payload.update(claims)
        
    return jwt.encode(payload, get_private_key_pem(), algorithm=settings.ALGORITHM)


def create_email_verification_token(user_id: str, email: str) -> str:
    """Generates a signed Ed25519 token for email verification valid for 24 hours."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=24)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "email_verification",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "vex-iam",
    }
    return jwt.encode(payload, get_private_key_pem(), algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        get_public_key_pem(),
        algorithms=[settings.ALGORITHM],
        issuer="vex-iam"
    )
