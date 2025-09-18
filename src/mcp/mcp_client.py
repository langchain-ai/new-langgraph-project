import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Any
from langchain_mcp_adapters.client import MultiServerMCPClient


class MCPClient:
    def __init__(self, config_path: Optional[str] = None):
        """Initialize MCP client with optional configuration file path."""
        if config_path is None:
            config_path = Path(__file__).parent / "mcp_config.json"
        
        self.config_path = Path(config_path)
        self.client = None
        self._tools = None
    
    def _load_config(self) -> dict:
        """Load configuration from JSON file with environment variable substitution."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"MCP config file not found: {self.config_path}")
        
        with open(self.config_path) as f:
            config = json.load(f)
        
        # Substitute environment variables
        config_str = json.dumps(config)
        for key, value in os.environ.items():
            config_str = config_str.replace(f"${{{key}}}", value)
        
        return json.loads(config_str)
    
    def _create_client(self) -> MultiServerMCPClient:
        """Create MCP client from configuration."""
        config = self._load_config()
        return MultiServerMCPClient(config["servers"])
    
    async def get_tools_async(self) -> List[Any]:
        """Get MCP tools asynchronously."""
        if self.client is None:
            self.client = self._create_client()
        
        if self._tools is None:
            self._tools = await self.client.get_tools()
        
        return self._tools
    
    def get_tools_sync(self) -> List[Any]:
        """Get MCP tools synchronously."""
        return asyncio.run(self.get_tools_async())


# Default instance for easy importing
_default_client = None

def get_mcp_tools(config_path: Optional[str] = None) -> List[Any]:
    """Get MCP tools using default or custom configuration."""
    global _default_client
    
    if _default_client is None or config_path is not None:
        _default_client = MCPClient(config_path)
    
    return _default_client.get_tools_sync()

def get_mcp_tools_optional(config_path: Optional[str] = None, fallback_to_empty: bool = True) -> List[Any]:
    """Get MCP tools with optional fallback to empty list if configuration fails."""
    try:
        return get_mcp_tools(config_path)
    except Exception as e:
        if fallback_to_empty:
            logging.warning(f"Failed to load MCP tools: {e}")
            return []
        raise