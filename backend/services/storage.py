"""
CursorCode AI - Object Storage Service
Wraps the Emergent Object Storage API for file hosting.
Used to host deployed project files as static websites.
"""

import logging
import requests

from core.config import EMERGENT_LLM_KEY, STORAGE_URL, APP_NAME

logger = logging.getLogger("storage")

_storage_key = None

MIME_TYPES = {
    "html": "text/html", "htm": "text/html",
    "css": "text/css",
    "js": "application/javascript", "jsx": "application/javascript",
    "mjs": "application/javascript",
    "ts": "application/typescript", "tsx": "application/typescript",
    "json": "application/json",
    "xml": "application/xml",
    "md": "text/markdown",
    "txt": "text/plain",
    "py": "text/x-python",
    "yaml": "text/yaml", "yml": "text/yaml",
    "svg": "image/svg+xml",
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "gif": "image/gif", "webp": "image/webp", "ico": "image/x-icon",
    "pdf": "application/pdf",
    "woff": "font/woff", "woff2": "font/woff2",
    "ttf": "font/ttf", "eot": "application/vnd.ms-fontobject",
    "zip": "application/zip",
}


def _get_content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return MIME_TYPES.get(ext, "application/octet-stream")


def is_storage_available() -> bool:
    return bool(EMERGENT_LLM_KEY)


def init_storage() -> str:
    """Initialize storage session. Call once at startup."""
    global _storage_key
    if _storage_key:
        return _storage_key

    if not EMERGENT_LLM_KEY:
        logger.warning("EMERGENT_LLM_KEY not set — storage unavailable")
        return ""

    try:
        resp = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": EMERGENT_LLM_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        logger.info("Object storage initialized")
        return _storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return ""


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload a file to storage. Returns {"path": ..., "size": ...}."""
    key = init_storage()
    if not key:
        raise RuntimeError("Storage not initialized")

    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple:
    """Download a file. Returns (bytes, content_type)."""
    key = init_storage()
    if not key:
        raise RuntimeError("Storage not initialized")

    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def upload_deployment_files(deployment_id: str, files: dict) -> dict:
    """Upload all project files for a deployment. Returns upload summary."""
    uploaded = []
    errors = []

    for filename, content in files.items():
        if filename.startswith("_docs/"):
            continue
        storage_path = f"{APP_NAME}/deployments/{deployment_id}/{filename}"
        content_type = _get_content_type(filename)

        try:
            result = put_object(storage_path, content.encode("utf-8"), content_type)
            uploaded.append({
                "filename": filename,
                "storage_path": result.get("path", storage_path),
                "size": result.get("size", len(content)),
                "content_type": content_type,
            })
        except Exception as e:
            errors.append({"filename": filename, "error": str(e)})
            logger.error(f"Failed to upload {filename}: {e}")

    return {
        "uploaded": len(uploaded),
        "errors": len(errors),
        "files": uploaded,
        "error_details": errors,
    }


def get_deployment_file(deployment_id: str, filepath: str) -> tuple:
    """Get a file from a deployment. Returns (bytes, content_type)."""
    storage_path = f"{APP_NAME}/deployments/{deployment_id}/{filepath}"
    content_type = _get_content_type(filepath)

    data, stored_type = get_object(storage_path)
    # Prefer our MIME type over storage's generic one
    return data, content_type
