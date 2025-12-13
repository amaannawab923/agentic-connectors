"""Agent decorator and AgentInfo class for Labrynth."""

from dataclasses import dataclass, field
from functools import partial, update_wrapper
from typing import Any, Callable, Dict, List, Optional, Union

from labrynth.core.parameters import ParameterInfo, extract_parameters
from labrynth.core.registry import register_agent


@dataclass
class AgentInfo:
    """
    Information about a registered agent.

    This class wraps a function and provides metadata for UI display
    and API serialization. The wrapped function remains callable.

    Attributes:
        name: The display name of the agent.
        func: The wrapped function.
        description: A description of what the agent does.
        tags: A list of tags for categorization.
        parameters: Dictionary of parameter information.
    """

    name: str
    func: Callable
    description: str
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, ParameterInfo] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Copy function metadata to this wrapper."""
        update_wrapper(self, self.func)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the agent function.

        Args:
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The return value of the wrapped function.
        """
        return self.func(*args, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize agent info for API/UI.

        Returns:
            Dictionary representation of the agent.
        """
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "parameters": {
                name: param.to_dict() for name, param in self.parameters.items()
            },
        }


class AgentDecorator:
    """
    Decorator for creating Labrynth agents.

    Supports both bare and parameterized decorator syntax:

        @agent
        def my_agent():
            pass

        @agent(name="Custom Name", tags=["example"])
        def my_agent():
            pass
    """

    def __call__(
        self,
        __fn: Optional[Callable[..., Any]] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Union[AgentInfo, Callable[[Callable[..., Any]], AgentInfo]]:
        """
        Decorator to create a Labrynth agent.

        Can be used with or without arguments:

            @agent
            def my_agent():
                pass

            @agent(name="Custom Name")
            def my_agent():
                pass

        Args:
            __fn: The function being decorated (when used without parentheses).
            name: Custom name for the agent (defaults to function name).
            description: Description of the agent (defaults to docstring).
            tags: List of tags for categorization.

        Returns:
            AgentInfo when decorating directly, or a partial function
            when called with arguments.
        """
        if __fn is not None:
            # Bare decorator: @agent
            return self._create_agent(__fn, name, description, tags)
        else:
            # Parameterized: @agent(name="...")
            return partial(
                self._create_agent,
                name=name,
                description=description,
                tags=tags,
            )

    def _create_agent(
        self,
        fn: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> AgentInfo:
        """
        Create and register an agent.

        Args:
            fn: The function to wrap as an agent.
            name: Custom name for the agent.
            description: Description of the agent.
            tags: List of tags for categorization.

        Returns:
            The created AgentInfo object.
        """
        # Determine agent name (convert underscores to hyphens)
        agent_name = name or fn.__name__.replace("_", "-")

        # Get description from docstring if not provided
        agent_description = description or fn.__doc__ or "No description"
        # Clean up docstring (first line only)
        if agent_description:
            agent_description = agent_description.strip().split("\n")[0]

        # Extract parameters from function signature
        parameters = extract_parameters(fn)

        # Create agent info
        agent = AgentInfo(
            name=agent_name,
            func=fn,
            description=agent_description,
            tags=tags or [],
            parameters=parameters,
        )

        # Register globally
        register_agent(agent)

        return agent


# Singleton instance for use as decorator
agent = AgentDecorator()
