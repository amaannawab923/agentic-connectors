"""Health check endpoint."""

from fastapi import APIRouter

from labrynth import __version__

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check server health."""
    return {
        "status": "healthy",
        "version": __version__,
    }
