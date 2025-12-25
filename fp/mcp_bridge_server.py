"""
HTTP/WebSocket bridge server for MCP browser tools.

This server exposes MCP browser tools via HTTP/WebSocket so that
Python code can call them remotely.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from aiohttp import web, WSMsgType
import aiohttp_cors

logger = logging.getLogger(__name__)

# Try to import aiohttp
AIOHTTP_AVAILABLE = False
try:
    import aiohttp
    import aiohttp_cors
    AIOHTTP_AVAILABLE = True
except ImportError:
    logger.warning("aiohttp not available. Install with: pip install aiohttp aiohttp-cors")


class MCPBridgeServer:
    """
    HTTP/WebSocket server that bridges MCP browser tools.
    
    This server allows Python code to call MCP tools via HTTP/WebSocket
    requests, which then calls the actual MCP tools.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize bridge server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.app = None
        self.runner = None
        self.site = None
        self.mcp_client = None  # Will be set to MCP client if available
    
    async def handle_tool_call(self, request: web.Request) -> web.Response:
        """
        Handle HTTP POST request to call an MCP tool.
        
        Expected JSON body:
        {
            "tool": "browser_navigate",
            "arguments": {"url": "http://example.com"}
        }
        """
        try:
            data = await request.json()
            tool_name = data.get("tool")
            arguments = data.get("arguments", {})
            
            if not tool_name:
                return web.json_response(
                    {"error": "Missing 'tool' field"},
                    status=400
                )
            
            # Call MCP tool
            result = await self._call_mcp_tool(tool_name, **arguments)
            
            return web.json_response({
                "success": True,
                "result": result
            })
        except Exception as e:
            logger.error(f"Error handling tool call: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """
        Handle WebSocket connection for real-time tool calls.
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        logger.info("WebSocket connection established")
        
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    tool_name = data.get("tool")
                    arguments = data.get("arguments", {})
                    request_id = data.get("id")
                    
                    if not tool_name:
                        await ws.send_json({
                            "id": request_id,
                            "error": "Missing 'tool' field"
                        })
                        continue
                    
                    # Call MCP tool
                    result = await self._call_mcp_tool(tool_name, **arguments)
                    
                    # Send result back
                    await ws.send_json({
                        "id": request_id,
                        "success": True,
                        "result": result
                    })
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    await ws.send_json({
                        "id": data.get("id"),
                        "error": str(e)
                    })
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"WebSocket error: {ws.exception()}")
        
        logger.info("WebSocket connection closed")
        return ws
    
    async def _call_mcp_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call an MCP tool (placeholder - needs actual MCP client).
        
        Args:
            tool_name: Name of the tool
            **kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        # This would call the actual MCP tool
        # For now, it's a placeholder
        logger.info(f"Calling MCP tool: {tool_name} with args: {kwargs}")
        
        # If we have an MCP client, use it
        if self.mcp_client:
            return await self.mcp_client.call_tool(tool_name, **kwargs)
        
        # Otherwise, return None (would need actual MCP tool implementation)
        return None
    
    async def start(self):
        """Start the bridge server."""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp not available. Install with: pip install aiohttp aiohttp-cors")
            return False
        
        self.app = web.Application()
        
        # Add CORS support
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add routes
        self.app.router.add_post("/tool", self.handle_tool_call)
        self.app.router.add_get("/ws", self.handle_websocket)
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        logger.info(f"MCP Bridge Server started on http://{self.host}:{self.port}")
        logger.info("Endpoints:")
        logger.info("  POST /tool - Call MCP tool via HTTP")
        logger.info("  GET /ws - WebSocket connection for real-time tool calls")
        return True
    
    async def stop(self):
        """Stop the bridge server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("MCP Bridge Server stopped")


async def start_bridge_server(host: str = "localhost", port: int = 8765) -> Optional[MCPBridgeServer]:
    """
    Start the MCP bridge server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        
    Returns:
        MCPBridgeServer instance or None if failed
    """
    if not AIOHTTP_AVAILABLE:
        logger.error("aiohttp not available")
        return None
    
    server = MCPBridgeServer(host, port)
    success = await server.start()
    
    if success:
        return server
    else:
        return None


# Client-side code to call the bridge server
class MCPBridgeClient:
    """
    Client for calling MCP tools via the bridge server.
    """
    
    def __init__(self, server_url: str = "http://localhost:8765"):
        """
        Initialize bridge client.
        
        Args:
            server_url: URL of the bridge server
        """
        self.server_url = server_url
        self.ws = None
        self.ws_connected = False
    
    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call an MCP tool via HTTP.
        
        Args:
            tool_name: Name of the tool
            **kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp not available")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/tool",
                    json={
                        "tool": tool_name,
                        "arguments": kwargs
                    }
                ) as response:
                    data = await response.json()
                    if data.get("success"):
                        return data.get("result")
                    else:
                        logger.error(f"Tool call failed: {data.get('error')}")
                        return None
        except Exception as e:
            logger.error(f"Error calling tool via bridge: {e}")
            return None
    
    async def connect_websocket(self):
        """Connect to WebSocket for real-time tool calls."""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp not available")
            return False
        
        try:
            ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
            self.ws = await aiohttp.ClientSession().ws_connect(f"{ws_url}/ws")
            self.ws_connected = True
            logger.info("WebSocket connected to bridge server")
            return True
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            return False
    
    async def call_tool_ws(self, tool_name: str, request_id: str = None, **kwargs) -> Any:
        """
        Call an MCP tool via WebSocket.
        
        Args:
            tool_name: Name of the tool
            request_id: Request ID (auto-generated if not provided)
            **kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        if not self.ws_connected or not self.ws:
            logger.error("WebSocket not connected")
            return None
        
        if request_id is None:
            import uuid
            request_id = str(uuid.uuid4())
        
        try:
            await self.ws.send_json({
                "id": request_id,
                "tool": tool_name,
                "arguments": kwargs
            })
            
            # Wait for response
            msg = await self.ws.receive()
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("id") == request_id:
                    if data.get("success"):
                        return data.get("result")
                    else:
                        logger.error(f"Tool call failed: {data.get('error')}")
                        return None
        except Exception as e:
            logger.error(f"Error calling tool via WebSocket: {e}")
            return None

