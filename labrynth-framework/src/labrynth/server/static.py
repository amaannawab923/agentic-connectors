"""Static file serving for Labrynth UI."""

from typing import Any

from fastapi import HTTPException, Response
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """
    StaticFiles handler for Single Page Applications.

    Returns index.html for any unknown routes, enabling
    client-side routing in React/Vite applications.

    This follows the same pattern as Prefect's UI serving.
    """

    async def get_response(self, path: str, scope: Any) -> Response:
        """
        Get response for a static file request.

        Falls back to index.html for unknown paths to support
        client-side routing.
        """
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code == 404:
                # Return index.html for SPA routing
                return await super().get_response("index.html", scope)
            raise
