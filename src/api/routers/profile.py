"""User profile and file upload router."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.auth import _verify_token
from src.db.models import UserProfile
from src.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _require_auth(auth_token: str = Cookie(default="")) -> dict:
    data = _verify_token(auth_token)
    if not data:
        raise HTTPException(status_code=401, detail="Login required")
    return data


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === Profile CRUD ===

class ProfileData(BaseModel):
    full_name: str | None = None
    age: int | None = None
    career_type: str | None = None
    job_category: str | None = None
    tech_stack: str | None = None
    education: str | None = None
    major: str | None = None
    salary_range: str | None = None
    location_pref: str | None = None


@router.get("/me")
async def get_profile(
    user: dict = Depends(_require_auth),
    db: Session = Depends(_get_db),
) -> dict:
    """Get current user's profile from DB."""
    profile = db.get(UserProfile, user["email"])
    if not profile:
        return {"exists": False}

    return {
        "exists": True,
        "full_name": profile.full_name,
        "age": profile.age,
        "career_type": profile.career_type,
        "job_category": profile.job_category,
        "tech_stack": profile.tech_stack,
        "education": profile.education,
        "major": profile.major,
        "salary_range": profile.salary_range,
        "location_pref": profile.location_pref,
        "resume_text": profile.resume_text[:100] + "..." if profile.resume_text and len(profile.resume_text) > 100 else profile.resume_text,
        "has_resume": bool(profile.resume_text),
        "has_portfolio": bool(profile.portfolio_text),
    }


@router.post("/me")
async def save_profile(
    data: ProfileData,
    user: dict = Depends(_require_auth),
    db: Session = Depends(_get_db),
) -> dict:
    """Save or update user profile in DB."""
    profile = db.get(UserProfile, user["email"])
    if not profile:
        profile = UserProfile(id=user["email"])
        db.add(profile)

    profile.full_name = data.full_name
    profile.age = data.age
    profile.career_type = data.career_type
    profile.job_category = data.job_category
    profile.tech_stack = data.tech_stack
    profile.education = data.education
    profile.major = data.major
    profile.salary_range = data.salary_range
    profile.location_pref = data.location_pref

    db.commit()
    return {"status": "ok"}


# === File Upload ===

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    type: str = Form(...),
    user: dict = Depends(_require_auth),
    db: Session = Depends(_get_db),
) -> dict:
    """Upload resume/portfolio, extract text, save to DB."""
    if type not in ("resume", "portfolio"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    safe_name = f"{type}_{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / safe_name
    if not save_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    save_path.write_bytes(content)

    extracted_text = ""
    try:
        if ext == ".pdf":
            extracted_text = _extract_pdf_text(save_path)
    finally:
        save_path.unlink(missing_ok=True)  # Delete file after extraction

    # Save extracted text to user profile in DB
    profile = db.get(UserProfile, user["email"])
    if not profile:
        profile = UserProfile(id=user["email"])
        db.add(profile)

    if type == "resume":
        profile.resume_text = extracted_text
    else:
        profile.portfolio_text = extracted_text

    db.commit()
    logger.info(f"Uploaded {type}: {safe_name} ({len(content)} bytes, {len(extracted_text)} chars extracted)")

    return {
        "status": "ok",
        "filename": safe_name,
        "extracted_text": extracted_text,
        "extracted_length": len(extracted_text),
    }


def _extract_pdf_text(path: Path) -> str:
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
        logger.warning("PyPDF2 not installed")
        return ""
    except Exception as e:
        logger.warning(f"PDF extraction failed: {e}")
        return ""
