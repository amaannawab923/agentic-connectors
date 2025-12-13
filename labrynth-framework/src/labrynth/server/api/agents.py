"""Agents API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from labrynth.database import AgentRepository, get_session

router = APIRouter()


@router.get("/agents")
async def list_agents(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """List all deployed agents."""
    async with get_session() as session:
        repo = AgentRepository(session)

        if project_id:
            agents = await repo.get_by_project(project_id)
        else:
            agents = await repo.get_all()

        return {
            "agents": [agent.to_dict() for agent in agents],
            "count": len(agents),
        }


@router.get("/agents/{name}")
async def get_agent_by_name(
    name: str,
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """Get a specific agent by name."""
    async with get_session() as session:
        repo = AgentRepository(session)

        if project_id:
            agent = await repo.get_by_name_and_project(name, project_id)
        else:
            # If no project_id, get all agents with that name and return first
            all_agents = await repo.get_all()
            agent = next((a for a in all_agents if a.name == name), None)

        if agent is None:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{name}' not found",
            )

        return agent.to_dict()
