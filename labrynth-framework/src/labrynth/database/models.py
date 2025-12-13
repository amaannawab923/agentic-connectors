"""Database models for Labrynth."""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlmodel import Column, Field, SQLModel, Text


class Agent(SQLModel, table=True):
    """Agent database model."""

    __tablename__ = "agents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: str = Field(index=True)
    name: str = Field(index=True)
    description: str = Field(default="")
    entrypoint: str = Field()  # e.g., "agents.example:send_email"

    # JSON-serialized fields stored as TEXT
    tags_json: str = Field(default="[]", sa_column=Column(Text))
    parameters_json: str = Field(default="{}", sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def tags(self) -> list[str]:
        """Get tags as a list."""
        return json.loads(self.tags_json)

    @tags.setter
    def tags(self, value: list[str]) -> None:
        """Set tags from a list."""
        self.tags_json = json.dumps(value)

    @property
    def parameters(self) -> dict[str, Any]:
        """Get parameters as a dict."""
        return json.loads(self.parameters_json)

    @parameters.setter
    def parameters(self, value: dict[str, Any]) -> None:
        """Set parameters from a dict."""
        self.parameters_json = json.dumps(value)

    def to_dict(self) -> dict[str, Any]:
        """Convert to API-friendly dictionary."""
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "entrypoint": self.entrypoint,
            "tags": self.tags,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_agent_info(
        cls,
        project_id: str,
        name: str,
        description: str,
        entrypoint: str,
        tags: list[str],
        parameters: dict[str, Any],
        agent_id: Optional[UUID] = None,
    ) -> "Agent":
        """Create Agent from discovered agent info."""
        agent = cls(
            project_id=project_id,
            name=name,
            description=description,
            entrypoint=entrypoint,
        )
        if agent_id:
            agent.id = agent_id
        agent.tags = tags
        agent.parameters = parameters
        return agent
