"""Repository for database operations."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from labrynth.database.models import Agent


class AgentRepository:
    """Repository for Agent CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, agent: Agent) -> Agent:
        """Create a new agent."""
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def get_by_id(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent by ID."""
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project(self, project_id: str) -> list[Agent]:
        """Get all agents for a project."""
        result = await self.session.execute(
            select(Agent).where(Agent.project_id == project_id).order_by(Agent.name)
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[Agent]:
        """Get all agents."""
        result = await self.session.execute(select(Agent).order_by(Agent.name))
        return list(result.scalars().all())

    async def get_by_name_and_project(
        self, name: str, project_id: str
    ) -> Optional[Agent]:
        """Get agent by name within a project."""
        result = await self.session.execute(
            select(Agent).where(Agent.name == name, Agent.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        agent: Agent,
        description: Optional[str] = None,
        entrypoint: Optional[str] = None,
        tags: Optional[list[str]] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> Agent:
        """Update an existing agent."""
        if description is not None:
            agent.description = description
        if entrypoint is not None:
            agent.entrypoint = entrypoint
        if tags is not None:
            agent.tags = tags
        if parameters is not None:
            agent.parameters = parameters
        agent.updated_at = datetime.utcnow()

        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def upsert(
        self,
        project_id: str,
        name: str,
        description: str,
        entrypoint: str,
        tags: list[str],
        parameters: dict[str, Any],
    ) -> Agent:
        """Create or update an agent."""
        existing = await self.get_by_name_and_project(name, project_id)

        if existing:
            return await self.update(
                existing,
                description=description,
                entrypoint=entrypoint,
                tags=tags,
                parameters=parameters,
            )
        else:
            agent = Agent.from_agent_info(
                project_id=project_id,
                name=name,
                description=description,
                entrypoint=entrypoint,
                tags=tags,
                parameters=parameters,
            )
            return await self.create(agent)

    async def delete(self, agent_id: UUID) -> bool:
        """Delete an agent by ID."""
        result = await self.session.execute(
            delete(Agent).where(Agent.id == agent_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def delete_by_project(self, project_id: str) -> int:
        """Delete all agents for a project."""
        result = await self.session.execute(
            delete(Agent).where(Agent.project_id == project_id)
        )
        await self.session.commit()
        return result.rowcount
