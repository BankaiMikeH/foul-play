"""
Script to start the MCP bridge server.

Run this script to start the HTTP/WebSocket bridge server that exposes
MCP browser tools for remote access.
"""
import asyncio
import logging
from fp.mcp_bridge_server import start_bridge_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Start the bridge server."""
    logger.info("Starting MCP Bridge Server...")
    logger.info("This server exposes MCP browser tools via HTTP/WebSocket")
    logger.info("Press Ctrl+C to stop the server")
    
    server = await start_bridge_server(host="localhost", port=8765)
    
    if not server:
        logger.error("Failed to start bridge server")
        return
    
    try:
        # Keep server running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("\nStopping bridge server...")
        await server.stop()
        logger.info("Bridge server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")

