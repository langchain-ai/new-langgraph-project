from typing import List
from langchain_core.tools import tool

@tool
def dpc_tool(dpc_input: str) -> str:
    """A custom tool that processes the input string in a specific way."""
    return f"Processed: {dpc_input}"


class DPCToolkit:
    @staticmethod
    def get_tools() -> List:
        """Return a list of tools provided by this toolkit."""
        return [dpc_tool]