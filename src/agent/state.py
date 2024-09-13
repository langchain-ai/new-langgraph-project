"""Define the state structures for the agent."""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Sequence

from typing_extensions import Annotated


@dataclass
class State:
    """Defines the input state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    """

    messages: Annotated[Sequence[dict], operator.add] = field(default_factory=list)
    """
    Messages tracking the primary execution state of the agent.

    Typically accumulates a pattern of user, assistant, user, ... etc. messages.
    """
