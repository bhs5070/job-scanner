"""Section-based chunking for JD documents.

Splits a JD into semantic sections (overview, requirements, preferred, benefits)
rather than fixed-size chunks, because JD sections carry distinct meaning
for resume matching and search.
"""

from dataclasses import dataclass

from src.db.models import JobPosting


@dataclass
class JDChunk:
    """A single chunk of a JD document."""

    job_id: str
    chunk_type: str  # "overview" | "requirements" | "preferred" | "full"
    text: str
    metadata: dict


def build_overview(job: JobPosting) -> str:
    """Build overview text from title, company, and description."""
    parts = [
        f"직무: {job.title}",
        f"회사: {job.company}",
    ]
    if job.description:
        # Take first 500 chars as overview summary
        parts.append(f"주요 업무: {job.description[:500]}")
    return "\n".join(parts)


def build_requirements(job: JobPosting) -> str | None:
    """Build requirements text."""
    if not job.requirements:
        return None
    return f"자격 요건:\n{job.requirements}"


def build_full_document(job: JobPosting) -> str:
    """Build a composite document combining key fields."""
    parts = [
        f"직무: {job.title}",
        f"회사: {job.company}",
    ]
    if job.description:
        parts.append(f"주요 업무: {job.description}")
    if job.requirements:
        parts.append(f"자격 요건: {job.requirements}")
    if job.tech_stack:
        tech_str = ", ".join(job.tech_stack) if isinstance(job.tech_stack, list) else str(job.tech_stack)
        parts.append(f"요구 기술: {tech_str}")
    return "\n".join(parts)


def _build_metadata(job: JobPosting, chunk_type: str) -> dict:
    """Build metadata dict for a chunk."""
    return {
        "job_id": str(job.id),
        "company": job.company,
        "title": job.title,
        "source_site": job.source_site,
        "source_url": job.source_url,
        "chunk_type": chunk_type,
        "is_active": job.is_active,
    }


def chunk_job_posting(job: JobPosting) -> list[JDChunk]:
    """Split a job posting into semantic chunks.

    Strategy:
    - Always produce a "full" composite document (for general search)
    - If requirements exist, produce a separate "requirements" chunk
      (for precise skill matching)
    """
    job_id = str(job.id)
    chunks: list[JDChunk] = []

    # Full composite document — always present
    full_text = build_full_document(job)
    chunks.append(JDChunk(
        job_id=job_id,
        chunk_type="full",
        text=full_text,
        metadata=_build_metadata(job, "full"),
    ))

    # Requirements chunk — only if available
    req_text = build_requirements(job)
    if req_text:
        chunks.append(JDChunk(
            job_id=job_id,
            chunk_type="requirements",
            text=req_text,
            metadata=_build_metadata(job, "requirements"),
        ))

    return chunks
