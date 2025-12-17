"""Agents API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from labrynth.database import AgentRepository, get_session


router = APIRouter()


class AgentResponse(BaseModel):
    """Response model for a single agent."""
    id: str
    project_id: str
    name: str
    description: str
    entrypoint: str
    tags: list[str]
    parameters: dict
    created_at: str
    updated_at: str


class AgentsListResponse(BaseModel):
    """Response model for listing agents."""
    agents: list[AgentResponse]
    count: int


@router.get(
    "/agents",
    response_model=AgentsListResponse,
    summary="List all agents",
    description="Retrieve all deployed agents, optionally filtered by project ID.",
)
async def list_agents(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    List all deployed agents.

    - **project_id**: Optional filter to get agents from a specific project
    """
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


@router.get(
    "/agents/{name}",
    response_model=AgentResponse,
    summary="Get agent by name",
    description="Retrieve a specific agent by its name.",
    responses={
        404: {"description": "Agent not found"},
    },
)
async def get_agent_by_name(
    name: str,
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    Get a specific agent by name.

    - **name**: The name of the agent to retrieve
    - **project_id**: Optional project ID to filter within
    """
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
