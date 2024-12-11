"""Define the state structures for the agent."""

from __future__ import annotations

from langgraph.graph.message import AnyMessage
from pydantic import BaseModel


class Bar(BaseModel):
    baz: str
    messages: list[AnyMessage]


class Foo(BaseModel):
    bar: Bar


class State(BaseModel):
    """Defines the input state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    See: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
    for more information.
    """

    changeme: str = "example"
    foo: Foo
