"""Parameter extraction utilities for Labrynth agents."""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, get_type_hints


@dataclass
class ParameterInfo:
    """Information about a function parameter."""

    name: str
    type: str
    required: bool
    default: Any
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "description": self.description,
        }


def extract_parameters(fn: Callable) -> Dict[str, ParameterInfo]:
    """
    Extract parameter schema from function signature.

    Args:
        fn: The function to extract parameters from.

    Returns:
        Dictionary mapping parameter names to ParameterInfo objects.
    """
    sig = inspect.signature(fn)

    # Get type hints safely
    try:
        hints = get_type_hints(fn)
    except Exception:
        hints = {}

    parameters = {}
    for param_name, param in sig.parameters.items():
        # Get type name
        type_hint = hints.get(param_name, Any)
        type_name = getattr(type_hint, "__name__", str(type_hint))

        # Check if required
        required = param.default is inspect.Parameter.empty

        # Get default value
        default = None if required else param.default

        parameters[param_name] = ParameterInfo(
            name=param_name,
            type=type_name,
            required=required,
            default=default,
        )

    return parameters
