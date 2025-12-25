"""
Bridge module for calling MCP browser tools.

This module provides an interface to MCP browser automation tools.
Supports three methods:
1. Direct MCP client connection
2. Playwright fallback
3. HTTP/WebSocket bridge server
"""
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import bridge implementations
try:
    from fp.mcp_client_setup import setup_mcp_client, MCPClientWrapper
    MCP_CLIENT_AVAILABLE = True
except ImportError:
    MCP_CLIENT_AVAILABLE = False
    MCPClientWrapper = None

try:
    from fp.playwright_bridge import get_playwright_bridge, PlaywrightBridge, PLAYWRIGHT_AVAILABLE as PW_AVAILABLE
    PLAYWRIGHT_AVAILABLE = PW_AVAILABLE  # Use the actual availability from playwright_bridge
except ImportError as e:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightBridge = None
    logger.debug(f"Could not import playwright_bridge: {e}")

try:
    from fp.mcp_bridge_server import MCPBridgeClient
    BRIDGE_CLIENT_AVAILABLE = True
except ImportError:
    BRIDGE_CLIENT_AVAILABLE = False
    MCPBridgeClient = None


class MCPBrowserBridge:
    """
    Bridge to MCP browser automation tools.
    
    This class provides methods that call MCP browser tools.
    Tries multiple methods in order:
    1. Direct MCP client
    2. Playwright fallback
    3. HTTP/WebSocket bridge
    """
    
    # Store references to available bridges
    _mcp_client: Optional[MCPClientWrapper] = None
    _playwright_bridge: Optional[PlaywrightBridge] = None
    _bridge_client: Optional[MCPBridgeClient] = None
    _active_method: Optional[str] = None  # "mcp", "playwright", "bridge", or None
    _initializing = False  # Lock to prevent concurrent initialization
    
    _initializing = False  # Lock to prevent concurrent initialization
    
    @classmethod
    async def _initialize_bridge(cls, headless: bool = False, bridge_server_url: Optional[str] = None):
        """
        Initialize the bridge with available methods.
        
        Tries methods in order:
        1. MCP client
        2. Playwright
        3. HTTP/WebSocket bridge
        
        Args:
            headless: Whether to run Playwright in headless mode
            bridge_server_url: URL of bridge server (if using bridge method)
        """
        # Prevent concurrent initialization
        if cls._initializing:
            # Wait a bit for initialization to complete
            await asyncio.sleep(0.1)
            if cls._active_method is not None:
                return
            # If still initializing after wait, proceed anyway
        
        # If already initialized, don't re-initialize
        if cls._active_method is not None:
            return
        
        cls._initializing = True
        try:
            # Try MCP client first
            if MCP_CLIENT_AVAILABLE and not cls._mcp_client:
                try:
                    cls._mcp_client = await setup_mcp_client()
                    if cls._mcp_client and cls._mcp_client.connected:
                        cls._active_method = "mcp"
                        logger.info("Using MCP client for browser automation")
                        return
                except Exception as e:
                    logger.debug(f"MCP client setup failed: {e}")
            
            # Try Playwright fallback
            if PLAYWRIGHT_AVAILABLE and not cls._playwright_bridge:
                try:
                    cls._playwright_bridge = await get_playwright_bridge(headless=headless)
                    if cls._playwright_bridge and cls._playwright_bridge.initialized:
                        cls._active_method = "playwright"
                        logger.info("Using Playwright for browser automation")
                        return
                except Exception as e:
                    logger.error(f"Playwright setup failed: {e}", exc_info=True)
            
            # Try HTTP/WebSocket bridge
            if BRIDGE_CLIENT_AVAILABLE:
                try:
                    server_url = bridge_server_url or "http://localhost:8765"
                    cls._bridge_client = MCPBridgeClient(server_url)
                    # Try to connect (non-blocking test)
                    cls._active_method = "bridge"
                    logger.info(f"Using HTTP/WebSocket bridge for browser automation (server: {server_url})")
                    return
                except Exception as e:
                    logger.debug(f"Bridge client setup failed: {e}")
            
            logger.warning("No browser automation method available. Install one of:")
            logger.warning("  - MCP client: pip install mcp")
            logger.warning("  - Playwright: pip install playwright && playwright install")
            logger.warning("  - Bridge server: pip install aiohttp aiohttp-cors")
            cls._active_method = None
        finally:
            cls._initializing = False
    
    @classmethod
    async def _call_mcp_tool(cls, tool_name: str, **kwargs) -> Any:
        """
        Call an MCP browser tool using the best available method.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments for the tool
            
        Returns:
            Tool result
        """
        # Initialize if not already done (use a lock to prevent concurrent initialization)
        if cls._active_method is None:
            await cls._initialize_bridge(headless=False)
        
        # If still None after initialization, something went wrong
        if cls._active_method is None:
            logger.warning(f"Cannot call {tool_name} - no browser automation method available")
            return None
        
        # Try MCP client
        if cls._active_method == "mcp" and cls._mcp_client:
            try:
                result = await cls._mcp_client.call_tool(tool_name, **kwargs)
                if result is not None:
                    return result
            except Exception as e:
                logger.debug(f"MCP client call failed: {e}")
        
        # Try Playwright
        if cls._active_method == "playwright" and cls._playwright_bridge:
            try:
                # Map MCP tool names to Playwright methods
                if tool_name == "browser_navigate":
                    result = await cls._playwright_bridge.navigate(kwargs.get("url", ""))
                    return result
                elif tool_name == "browser_snapshot":
                    result = await cls._playwright_bridge.snapshot()
                    return result
                elif tool_name == "browser_click":
                    result = await cls._playwright_bridge.click(
                        kwargs.get("ref", ""),
                        kwargs.get("element", "")
                    )
                    return result
                elif tool_name == "browser_type":
                    result = await cls._playwright_bridge.type_text(
                        kwargs.get("ref", ""),
                        kwargs.get("text", ""),
                        kwargs.get("element", "")
                    )
                    return result
                elif tool_name == "browser_wait_for":
                    if "textGone" in kwargs:
                        result = await cls._playwright_bridge.wait_for_text_gone(
                            kwargs.get("textGone", ""),
                            kwargs.get("time", 10)
                        )
                    else:
                        result = await cls._playwright_bridge.wait_for_text(
                            kwargs.get("text", ""),
                            kwargs.get("time", 10)
                        )
                    return result
                elif tool_name == "browser_select_option":
                    result = await cls._playwright_bridge.select_option(
                        kwargs.get("ref", ""),
                        kwargs.get("values", []),
                        kwargs.get("element", "")
                    )
                    return result
                elif tool_name == "browser_tabs":
                    if kwargs.get("action") == "new":
                        result = await cls._playwright_bridge.create_new_tab()
                    else:
                        result = await cls._playwright_bridge.close_tab()
                    return result
            except Exception as e:
                logger.debug(f"Playwright call failed: {e}")
        
        # Try bridge client
        if cls._active_method == "bridge" and cls._bridge_client:
            try:
                result = await cls._bridge_client.call_tool(tool_name, **kwargs)
                if result is not None:
                    return result
            except Exception as e:
                logger.debug(f"Bridge client call failed: {e}")
        
        logger.warning(f"Tool {tool_name} not available through any method")
        return None
    
    @staticmethod
    async def navigate(url: str) -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if navigation succeeded
        """
        logger.info(f"Navigating to: {url}")
        try:
            result = await MCPBrowserBridge._call_mcp_tool("browser_navigate", url=url)
            if result is not None:
                return True
            
            logger.warning("Navigation not available through any method")
            return False
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False
    
    @staticmethod
    async def snapshot() -> Dict[str, Any]:
        """
        Get browser accessibility snapshot.
        
        Returns:
            Accessibility snapshot dictionary
        """
        logger.debug("Getting browser snapshot")
        try:
            result = await MCPBrowserBridge._call_mcp_tool("browser_snapshot")
            if result is not None:
                return result if isinstance(result, dict) else {}
            
            logger.warning("Snapshot not available through any method")
            return {}
        except Exception as e:
            logger.error(f"Error getting snapshot: {e}")
            return {}
    
    @staticmethod
    async def click(element_ref: str, description: str) -> bool:
        """
        Click an element.
        
        Args:
            element_ref: Element reference from snapshot
            description: Human-readable description
            
        Returns:
            True if click succeeded
        """
        logger.debug(f"Clicking: {description} (ref: {element_ref})")
        try:
            result = await MCPBrowserBridge._call_mcp_tool(
                "browser_click",
                element=description,
                ref=element_ref
            )
            if result is not None:
                return True
            
            logger.warning(f"Click not available for {description}")
            return False
        except Exception as e:
            logger.error(f"Error clicking {description}: {e}")
            return False
    
    @staticmethod
    async def type_text(element_ref: str, text: str, description: str) -> bool:
        """
        Type text into an element.
        
        Args:
            element_ref: Element reference
            text: Text to type
            description: Human-readable description
            
        Returns:
            True if typing succeeded
        """
        logger.debug(f"Typing into {description}: {text[:50]}...")
        try:
            result = await MCPBrowserBridge._call_mcp_tool(
                "browser_type",
                element=description,
                ref=element_ref,
                text=text
            )
            if result is not None:
                return True
            
            logger.warning(f"Type not available for {description}")
            return False
        except Exception as e:
            logger.error(f"Error typing into {description}: {e}")
            return False
    
    @staticmethod
    async def wait_for_text(text: str, timeout: int = 10) -> bool:
        """
        Wait for text to appear.
        
        Args:
            text: Text to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if text appeared
        """
        logger.debug(f"Waiting for text: {text} (timeout: {timeout}s)")
        try:
            result = await MCPBrowserBridge._call_mcp_tool(
                "browser_wait_for",
                text=text,
                time=timeout
            )
            if result is not None:
                return True
            
            # Fallback: Simple sleep-based wait
            logger.warning("Wait for text not available - using fallback wait")
            await asyncio.sleep(min(timeout, 1.0))
            return False
        except Exception as e:
            logger.error(f"Error waiting for text {text}: {e}")
            await asyncio.sleep(min(timeout, 1.0))
            return False
    
    @staticmethod
    async def wait_for_text_gone(text: str, timeout: int = 10) -> bool:
        """
        Wait for text to disappear.
        
        Args:
            text: Text to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if text disappeared
        """
        logger.debug(f"Waiting for text to disappear: {text} (timeout: {timeout}s)")
        try:
            result = await MCPBrowserBridge._call_mcp_tool(
                "browser_wait_for",
                textGone=text,
                time=timeout
            )
            if result is not None:
                return True
            
            # Fallback
            logger.warning("Wait for text gone not available - using fallback wait")
            await asyncio.sleep(min(timeout, 1.0))
            return False
        except Exception as e:
            logger.error(f"Error waiting for text to disappear {text}: {e}")
            await asyncio.sleep(min(timeout, 1.0))
            return False
    
    @staticmethod
    async def select_option(element_ref: str, values: list, description: str) -> bool:
        """
        Select option(s) in a dropdown.
        
        Args:
            element_ref: Element reference
            values: List of values to select
            description: Human-readable description
            
        Returns:
            True if selection succeeded
        """
        logger.debug(f"Selecting option in {description}: {values}")
        try:
            result = await MCPBrowserBridge._call_mcp_tool(
                "browser_select_option",
                element=description,
                ref=element_ref,
                values=values
            )
            if result is not None:
                return True
            
            logger.warning(f"Select option not available for {description}")
            return False
        except Exception as e:
            logger.error(f"Error selecting option in {description}: {e}")
            return False
    
    @staticmethod
    async def create_new_tab() -> bool:
        """
        Create a new browser tab/window.
        
        Returns:
            True if new tab was created
        """
        logger.info("Creating new browser tab")
        try:
            result = await MCPBrowserBridge._call_mcp_tool("browser_tabs", action="new")
            if result is not None:
                return True
            
            logger.warning("Create new tab not available")
            return False
        except Exception as e:
            logger.error(f"Error creating new tab: {e}")
            return False
    
    @staticmethod
    async def close_tab() -> bool:
        """
        Close the current browser tab.
        
        Returns:
            True if tab was closed
        """
        logger.info("Closing browser tab")
        try:
            result = await MCPBrowserBridge._call_mcp_tool("browser_tabs", action="close")
            if result is not None:
                return True
            
            logger.warning("Close tab not available")
            return False
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
            return False
