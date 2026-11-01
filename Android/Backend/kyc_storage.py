"""Private encrypted manual-review document storage with a quarantine gate."""
from __future__ import annotations

import hashlib
import os
import socket
import struct
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException


MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def fernet() -> Fernet:
    key = os.getenv("KYC_DOCUMENT_ENCRYPTION_KEY", "").strip().encode()
    if not key:
        raise HTTPException(503, detail={"code": "KYC_STORAGE_NOT_CONFIGURED", "message": "Secure manual document storage is not configured."})
    try:
        return Fernet(key)
    except Exception:
        raise HTTPException(503, detail={"code": "KYC_STORAGE_NOT_CONFIGURED", "message": "The manual document encryption key is invalid."}) from None


def storage_root() -> Path:
    raw = os.getenv("KYC_MANUAL_STORAGE_PATH", "").strip()
    if not raw:
        raise HTTPException(503, detail={"code": "KYC_STORAGE_NOT_CONFIGURED", "message": "Secure manual document storage is not configured."})
    root = Path(raw).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def validate_file(data: bytes, content_type: str) -> None:
    if not data or len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(413, detail={"code": "DOCUMENT_SIZE_INVALID", "message": "The selected file is empty or exceeds the 8 MB limit."})
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, detail={"code": "DOCUMENT_TYPE_INVALID", "message": "Upload a PDF, JPEG, or PNG document."})
    signature_ok = ((content_type == "application/pdf" and data.startswith(b"%PDF-"))
                    or (content_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
                    or (content_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n")))
    if not signature_ok:
        raise HTTPException(415, detail={"code": "DOCUMENT_CONTENT_INVALID", "message": "The file content does not match its declared type."})


def scan(data: bytes) -> str:
    mode = os.getenv("KYC_ANTIVIRUS_MODE", "quarantine").strip().lower()
    if mode == "test_clean" and os.getenv("APP_ENV", "").lower() == "test":
        return "CLEAN"
    if mode != "clamav":
        return "QUARANTINED"
    socket_path = os.getenv("KYC_CLAMAV_UNIX_SOCKET", "").strip()
    if not socket_path:
        return "ERROR"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(10)
            client.connect(socket_path)
            client.sendall(b"zINSTREAM\0")
            for start in range(0, len(data), 64 * 1024):
                chunk = data[start:start + 64 * 1024]
                client.sendall(struct.pack("!I", len(chunk)) + chunk)
            client.sendall(struct.pack("!I", 0))
            answer = client.recv(4096).decode("utf-8", "replace")
            if answer.endswith("OK\0") or answer.endswith("OK\n"):
                return "CLEAN"
            if "FOUND" in answer:
                return "INFECTED"
    except (OSError, TimeoutError):
        return "ERROR"
    return "ERROR"


def store(data: bytes, storage_key: str) -> str:
    root = storage_root()
    key = Path(storage_key)
    if key.name != storage_key or not storage_key.endswith(".enc"):
        raise ValueError("invalid internal storage key")
    destination = (root / key).resolve()
    if destination.parent != root:
        raise ValueError("invalid internal storage path")
    ciphertext = fernet().encrypt(data)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(ciphertext)
    return hashlib.sha256(data).hexdigest()


def read(storage_key: str) -> bytes:
    root = storage_root()
    key = Path(storage_key)
    if key.name != storage_key or not storage_key.endswith(".enc"):
        raise HTTPException(404, detail="Document not found")
    path = (root / key).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, detail="Document not found")
    try:
        return fernet().decrypt(path.read_bytes())
    except InvalidToken:
        raise HTTPException(500, detail="Encrypted document could not be opened") from None


def delete(storage_key: str) -> None:
    root = storage_root()
    key = Path(storage_key)
    if key.name != storage_key or not storage_key.endswith(".enc"):
        return
    path = (root / key).resolve()
    if path.parent == root:
        path.unlink(missing_ok=True)
