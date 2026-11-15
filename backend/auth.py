import hmac
import hashlib
import os
import json
import base64
import time
import uuid
import secrets
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import HTTPException, Header, Query, Depends, status

from backend.database import get_connection, current_timestamp

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _load_secret_key() -> str:
    """
    Loads and validates the persistent SECRET_KEY.
    1. If ZORIN_SECRET_KEY is configured in env or .env, validates that it is sufficiently strong (>= 32 chars).
    2. Otherwise, loads from data/secret.key (never overwriting an existing valid key).
    3. If data/secret.key does not exist, generates a 256-bit secure hex key and writes it.
    4. If loading or saving data/secret.key fails, raises a clear RuntimeError startup error.
    """
    env_key = os.getenv("ZORIN_SECRET_KEY")
    if env_key:
        env_key = env_key.strip()
        if len(env_key) < 32:
            raise ValueError(
                f"ZORIN_SECRET_KEY is too weak ({len(env_key)} chars). It must be at least 32 characters long."
            )
        insecure_patterns = ["zorin-multi-device", "secret", "password", "123456", "admin", "default", "changeme"]
        if any(pattern in env_key.lower() for pattern in insecure_patterns):
            raise ValueError(
                "ZORIN_SECRET_KEY is insecure. Do not use known default or trivial secrets."
            )
        return env_key

    secret_file = BASE_DIR / "data" / "secret.key"
    try:
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        if secret_file.exists():
            saved_key = secret_file.read_text(encoding="utf-8").strip()
            if saved_key and len(saved_key) >= 32:
                # Existing valid secret key: NEVER overwrite
                return saved_key

        # File does not exist or was empty: generate new 32-byte (256-bit) persistent key
        new_key = secrets.token_hex(32)
        secret_file.write_text(new_key, encoding="utf-8")
        return new_key
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load or initialize persistent secret key at '{secret_file}': {exc}. "
            "A persistent SECRET_KEY is required for secure authentication."
        ) from exc


SECRET_KEY = _load_secret_key()

TOKEN_EXPIRY_SECONDS = 60 * 60 * 24 * 30  # 30 days session validity


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return hmac.compare_digest(key.hex(), password_hash)


def create_access_token(user_id: str, email: str, expires_in: Optional[int] = None) -> str:
    valid_duration = expires_in if expires_in is not None else TOKEN_EXPIRY_SECONDS
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": int(time.time()) + valid_duration,
        "nonce": uuid.uuid4().hex[:8]
    }
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')
    
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    
    return f"{payload_b64}.{sig_b64}"


def decode_token(token: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) != 2:
            raise ValueError("Malformed token format.")
        
        payload_b64, sig_b64 = parts
        
        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode('utf-8').rstrip('=')
        
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            raise ValueError("Invalid token signature.")
        
        # Add padding back if necessary
        padded_b64 = payload_b64 + '=' * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_b64).decode('utf-8'))
        
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token has expired.")
            
        return payload
    except Exception as e:
        raise ValueError(f"Token decoding error: {e}")


def get_user_by_id(user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, email, display_name, voice_preference, theme, created_at, last_login FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
            (email.strip(),)
        ).fetchone()
        return dict(row) if row else None


def register_user(email: str, password: str, display_name: str, voice_preference: str = "Puck") -> dict:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if not display_name or not display_name.strip():
        display_name = email.split("@")[0].capitalize()

    existing = get_user_by_email(email)
    if existing:
        raise ValueError("An account with this email already exists.")

    user_id = str(uuid.uuid4())
    pwd_hash, salt = hash_password(password)
    now = current_timestamp()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (user_id, email, password_hash, salt, display_name, voice_preference, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, email, pwd_hash, salt, display_name.strip(), voice_preference, now, now))
        conn.commit()

    user = get_user_by_id(user_id)
    token = create_access_token(user_id, email)
    return {"user": user, "token": token}


def authenticate_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    user = get_user_by_email(email)
    if not user:
        raise ValueError("Invalid email or password.")

    if not verify_password(password, user["password_hash"], user["salt"]):
        raise ValueError("Invalid email or password.")

    now = current_timestamp()
    with get_connection() as conn:
        conn.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (now, user["user_id"]))
        conn.commit()

    safe_user = get_user_by_id(user["user_id"])
    token = create_access_token(user["user_id"], user["email"])
    return {"user": safe_user, "token": token}


def seed_default_user_if_needed():
    """Deprecated: Automatic creation of default account has been removed for security."""
    pass


async def get_current_user(
    authorization: Optional[str] = Header(None),
    token_param: Optional[str] = Query(None, alias="token")
) -> dict:
    """
    FastAPI dependency that extracts and strictly validates the current user from Bearer header or token query param.
    Rejects any unauthenticated or invalid request with HTTP 401 Unauthorized.
    """
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif token_param:
        token = token_param.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = decode_token(token)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or token invalid.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def get_current_user_or_default(
    authorization: Optional[str] = Header(None),
    token_param: Optional[str] = Query(None, alias="token")
) -> dict:
    """
    Extracts user from token if present; otherwise seamlessly falls back to default local user.
    Enables frictionless chat on web and mobile companions without auth failures.
    """
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif token_param:
        token = token_param.strip()

    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("user_id")
            if user_id:
                user = get_user_by_id(user_id)
                if user:
                    return user
        except Exception:
            pass

    try:
        from memory.database import get_default_user_id
        default_uid = get_default_user_id()
        user = get_user_by_id(default_uid)
        if user:
            return user
    except Exception:
        pass

    return {
        "user_id": "default-zorin-user",
        "email": "default@zorin.ai",
        "display_name": "ZORIN User",
        "voice_preference": "Aoede"
    }

