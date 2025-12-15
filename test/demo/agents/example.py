"""Example agents demonstrating Labrynth usage."""

from labrynth import agent


@agent(
    name="Hello World",
    description="A simple example agent that greets the world",
    tags=["example", "demo"]
)
def hello_world():
    """Say hello to the world."""
    print("Hello from Agent!")
    return {"message": "Hello, World!"}


@agent(
    name="Greeter",
    description="An agent that greets someone by name",
    tags=["example", "greeting"]
)
def greeter(name: str = "Friend"):
    """Greet someone by name.

    Args:
        name: The name of the person to greet
    """
    greeting = f"Hello, {name}!"
    print(greeting)
    return {"greeting": greeting}


@agent
def simple_agent():
    """A minimal agent using the bare decorator."""
    print("I am a simple agent!")
    return {"status": "executed"}
