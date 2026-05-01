from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any


def hash_password(password: str, iterations: int = 600_000) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(password_hash).decode("utf-8"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iteration_text, encoded_salt, encoded_hash = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    iterations = int(iteration_text)
    salt = base64.b64decode(encoded_salt.encode("utf-8"))
    expected_hash = base64.b64decode(encoded_hash.encode("utf-8"))
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(password_hash, expected_hash)


def flash(request: Any, level: str, message: str) -> None:
    flashes = request.session.setdefault("_flash_messages", [])
    flashes.append({"level": level, "message": message})
    request.session["_flash_messages"] = flashes


def consume_flashes(request: Any) -> list[dict[str, str]]:
    return request.session.pop("_flash_messages", [])
