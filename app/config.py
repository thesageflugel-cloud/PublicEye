from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "PublicEye"
SECRET_KEY = os.environ.get("PUBLICEYE_SECRET_KEY", "publiceye-dev-secret-key")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
DATABASE_URL = f"sqlite:///{(STORAGE_DIR / 'publiceye.db').as_posix()}"
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

COMPLAINT_CATEGORIES = [
    "Road Damage",
    "Garbage Overflow",
    "Water Leakage",
    "Drainage Blockage",
    "Streetlight Failure",
    "Public Safety",
    "Encroachment",
    "Other",
]
