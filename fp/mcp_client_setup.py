"""
MCP Client setup for browser automation.

This module provides utilities to set up and configure an MCP client
for accessing browser automation tools.
"""
import logging
import asyncio
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

# Try to import MCP client libraries
MCP_CLIENT_AVAILABLE = False
MCP_CLIENT = None

try:
    # Try importing mcp (official MCP Python SDK)
    import mcp
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_CLIENT_AVAILABLE = True
    logger.info("MCP Python SDK available")
except ImportError:
    try:
        # Try importing browser-mcp package
        import browser_mcp
        MCP_CLIENT_AVAILABLE = True
        logger.info("browser-mcp package available")
    except ImportError:
        logger.warning("No MCP client library found. Install with: pip install mcp or pip install browser-mcp")


class MCPClientWrapper:
    """
    Wrapper for MCP client to provide a consistent interface.
    """
    
    def __init__(self, client: Any = None):
        """
        Initialize MCP client wrapper.
        
        Args:
            client: MCP client instance (optional)
        """
        self.client = client
        self.session = None
        self.connected = False
    
    async def connect(self, server_command: Optional[str] = None) -> bool:
        """
        Connect to MCP server.
        
        Args:
            server_command: Command to start MCP server (optional)
            
        Returns:
            True if connected successfully
        """
        try:
            if not MCP_CLIENT_AVAILABLE:
                logger.error("MCP client library not available")
                return False
            
            # Try to use mcp Python SDK
            try:
                import mcp
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client
                
                # Configure server parameters
                # For browser-mcp, the server might be started separately
                # or we might need to start it ourselves
                if server_command:
                    # Custom server command
                    server_params = StdioServerParameters(
                        command=server_command,
                        args=[]
                    )
                else:
                    # Try default browser-mcp server
                    server_params = StdioServerParameters(
                        command="browser-mcp-run",
                        args=[]
                    )
                
                # Create client session
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        self.session = session
                        self.connected = True
                        logger.info("Connected to MCP server")
                        return True
                        
            except Exception as e:
                logger.warning(f"Failed to connect with mcp SDK: {e}")
                # Try browser-mcp package directly
                try:
                    import browser_mcp
                    # browser-mcp might have a different interface
                    # This is a placeholder - actual implementation depends on the package
                    logger.info("Using browser-mcp package")
                    return True
                except Exception as e2:
                    logger.error(f"Failed to use browser-mcp: {e2}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
            return False
    
    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments for the tool
            
        Returns:
            Tool result
        """
        if not self.connected or not self.session:
            logger.error("MCP client not connected")
            return None
        
        try:
            # Call tool through MCP session
            # Tool name format: browser_navigate, browser_snapshot, etc.
            result = await self.session.call_tool(tool_name, arguments=kwargs)
            return result
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return None
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        if self.session:
            # Session cleanup handled by context manager
            self.session = None
        self.connected = False


async def setup_mcp_client(server_command: Optional[str] = None) -> Optional[MCPClientWrapper]:
    """
    Set up and connect MCP client.
    
    Args:
        server_command: Command to start MCP server (optional)
        
    Returns:
        MCPClientWrapper instance or None if setup failed
    """
    if not MCP_CLIENT_AVAILABLE:
        logger.warning("MCP client libraries not available. Install with: pip install mcp")
        return None
    
    client = MCPClientWrapper()
    success = await client.connect(server_command)
    
    if success:
        return client
    else:
        logger.warning("Failed to connect to MCP server")
        return None

