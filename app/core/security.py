from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timezone, timedelta
import jwt
import base64
import uuid
from typing import Optional, Dict, Any
from app.core.config import settings

DEFAULT_KEY_ID = "vex-iam-ed25519-v1"

ph = PasswordHasher()

# Generate or manage Ed25519 signing keys
def _init_keys() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    if settings.JWT_PRIVATE_KEY_PEM:
        try:
            pem_bytes = settings.JWT_PRIVATE_KEY_PEM.encode("utf-8")
            # Handle escaped newlines in env variables
            if b"\\n" in pem_bytes:
                pem_bytes = pem_bytes.replace(b"\\n", b"\n")
            priv = serialization.load_pem_private_key(pem_bytes, password=None)
            if isinstance(priv, ed25519.Ed25519PrivateKey):
                return priv, priv.public_key()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to load configured JWT_PRIVATE_KEY_PEM: {e}. Falling back.")
    
    # Fallback to deterministic key derived from SECRET_KEY if provided
    if settings.SECRET_KEY and len(settings.SECRET_KEY) >= 32:
        import hashlib
        seed = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        return priv, priv.public_key()

    if settings.ENVIRONMENT != "development":
        raise RuntimeError(
            "Production deployment must configure JWT_PRIVATE_KEY_PEM or a custom SECRET_KEY (minimum 32 characters)."
        )

    priv = ed25519.Ed25519PrivateKey.generate()
    return priv, priv.public_key()

_private_key, _public_key = _init_keys()


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
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "vex-iam",
    }
    if claims:
        payload.update(claims)
        
    return jwt.encode(
        payload,
        get_private_key_pem(),
        algorithm=settings.ALGORITHM,
        headers={"kid": DEFAULT_KEY_ID},
    )


def create_refresh_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates an Ed25519-signed refresh token valid for REFRESH_TOKEN_EXPIRE_DAYS."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "vex-iam",
    }
    if claims:
        payload.update(claims)

    return jwt.encode(
        payload,
        get_private_key_pem(),
        algorithm=settings.ALGORITHM,
        headers={"kid": DEFAULT_KEY_ID},
    )


def sign_payload(payload_bytes: bytes) -> str:
    """Signs bytes using the Ed25519 private key and returns base64url-encoded signature."""
    signature = _private_key.sign(payload_bytes)
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


def verify_payload_signature(payload_bytes: bytes, signature_b64url: str) -> bool:
    """Verifies an Ed25519 base64url-encoded signature against payload bytes."""
    try:
        padding = (4 - len(signature_b64url) % 4) % 4
        sig_bytes = base64.urlsafe_b64decode(signature_b64url + ("=" * padding))
        _public_key.verify(sig_bytes, payload_bytes)
        return True
    except Exception:
        return False


def get_jwk() -> Dict[str, Any]:
    """Returns the RFC 8037 compliant OKP JWK for Ed25519 public key."""
    raw_bytes = _public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    x_b64url = base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "use": "sig",
        "alg": "EdDSA",
        "kid": DEFAULT_KEY_ID,
        "x": x_b64url,
    }


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
