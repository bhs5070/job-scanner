"""User profile and file upload router."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, UploadFile

from src.api.routers.auth import _verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _require_auth(auth_token: str = Cookie(default="")) -> dict:
    """Dependency: require authenticated user."""
    data = _verify_token(auth_token)
    if not data:
        raise HTTPException(status_code=401, detail="Login required")
    return data


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    type: str = Form(...),
    user: dict = Depends(_require_auth),
) -> dict:
    """Upload a resume or portfolio file."""
    if type not in ("resume", "portfolio"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Validate file extension
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Save with UUID filename to prevent path traversal
    safe_name = f"{type}_{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / safe_name

    # Extra safety: verify path is inside UPLOAD_DIR
    if not save_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    save_path.write_bytes(content)

    # Extract text (basic)
    extracted_text = ""
    if ext == ".pdf":
        extracted_text = _extract_pdf_text(save_path)

    logger.info(f"Uploaded {type}: {safe_name} ({len(content)} bytes)")

    return {
        "status": "ok",
        "filename": safe_name,
        "size": len(content),
        "extracted_text": extracted_text,
        "extracted_length": len(extracted_text),
    }


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        import PyPDF2

        text_parts = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("PyPDF2 not installed, skipping PDF extraction")
        return ""
    except Exception as e:
        logger.warning(f"PDF extraction failed: {e}")
        return ""
