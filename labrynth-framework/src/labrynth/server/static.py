"""Static file serving for Labrynth UI."""

from typing import Any

from fastapi import HTTPException, Response
from starlette.staticfiles import StaticFiles


# Paths that should NOT be handled by SPA routing
EXCLUDED_PATHS = {
    "docs",
    "redoc",
    "openapi.json",
    "api",
}


class SPAStaticFiles(StaticFiles):
    """
    StaticFiles handler for Single Page Applications.

    Returns index.html for any unknown routes, enabling
    client-side routing in React/Vite applications.

    Excludes API and documentation paths from SPA routing.

    This follows the same pattern as Prefect's UI serving.
    """

    async def get_response(self, path: str, scope: Any) -> Response:
        """
        Get response for a static file request.

        Falls back to index.html for unknown paths to support
        client-side routing, except for API and docs paths.

        Adds no-cache headers to index.html to ensure fresh content.
        """
        # Check if this is an excluded path (API, docs, etc.)
        first_segment = path.split("/")[0] if path else ""
        if first_segment in EXCLUDED_PATHS:
            # Let FastAPI handle this - raise 404 to pass through
            raise HTTPException(status_code=404, detail="Not found")

        try:
            response = await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code == 404:
                # Return index.html for SPA routing
                response = await super().get_response("index.html", scope)
                # Always prevent caching of index.html (SPA entry point)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
            raise

        # Prevent caching of index.html but allow caching of hashed assets
        if path == "" or path == "index.html":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response
