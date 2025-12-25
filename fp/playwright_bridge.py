"""
Playwright bridge for browser automation.

This module provides a Playwright-based implementation of browser automation
as a fallback when MCP tools are not available.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import Playwright
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
    logger.info("Playwright available")
except ImportError:
    logger.warning("Playwright not available. Install with: pip install playwright && playwright install")


class PlaywrightBridge:
    """
    Playwright-based browser automation bridge.
    
    This provides the same interface as MCPBrowserBridge but uses Playwright
    for actual browser control.
    """
    
    def __init__(self):
        """Initialize Playwright bridge."""
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.initialized = False
    
    async def initialize(self, headless: bool = False):
        """
        Initialize Playwright browser.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            self.initialized = True
            logger.info("Playwright browser initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False
    
    async def navigate(self, url: str) -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if navigation succeeded
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return False
        
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            logger.info(f"Navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False
    
    async def snapshot(self) -> Dict[str, Any]:
        """
        Get browser accessibility snapshot.
        
        Returns:
            Accessibility snapshot dictionary
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return {}
        
        try:
            # Playwright doesn't have built-in accessibility snapshot
            # We'll create a simplified version using page content
            content = await self.page.content()
            title = await self.page.title()
            url = self.page.url
            
            # Get all elements with their properties
            elements = await self.page.evaluate("""
                () => {
                    const result = [];
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const elem = node;
                            result.push({
                                tag: elem.tagName.toLowerCase(),
                                text: elem.textContent?.trim() || '',
                                role: elem.getAttribute('role') || '',
                                type: elem.type || '',
                                name: elem.name || '',
                                id: elem.id || '',
                                className: elem.className || '',
                                href: elem.href || '',
                                disabled: elem.disabled || false,
                                editable: elem.contentEditable === 'true' || elem.isContentEditable
                            });
                        }
                    }
                    return result;
                }
            """)
            
            return {
                "url": url,
                "title": title,
                "elements": elements,
                "content": content[:1000]  # First 1000 chars
            }
        except Exception as e:
            logger.error(f"Error getting snapshot: {e}")
            return {}
    
    async def click(self, element_ref: str, description: str) -> bool:
        """
        Click an element.
        
        Args:
            element_ref: Element reference (CSS selector, XPath, or text)
            description: Human-readable description
            
        Returns:
            True if click succeeded
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return False
        
        try:
            # Try different selector strategies
            # First, try as CSS selector
            try:
                await self.page.click(element_ref)
                logger.debug(f"Clicked {description} using CSS selector")
                return True
            except Exception:
                pass
            
            # Try as XPath
            try:
                await self.page.click(f"xpath={element_ref}")
                logger.debug(f"Clicked {description} using XPath")
                return True
            except Exception:
                pass
            
            # Try as text content
            try:
                await self.page.click(f"text={element_ref}")
                logger.debug(f"Clicked {description} using text")
                return True
            except Exception:
                pass
            
            logger.warning(f"Could not click {description} with ref: {element_ref}")
            return False
        except Exception as e:
            logger.error(f"Error clicking {description}: {e}")
            return False
    
    async def type_text(self, element_ref: str, text: str, description: str) -> bool:
        """
        Type text into an element.
        
        Args:
            element_ref: Element reference
            text: Text to type
            description: Human-readable description
            
        Returns:
            True if typing succeeded
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return False
        
        try:
            # Try to find and type into element
            # First, try as CSS selector
            try:
                await self.page.fill(element_ref, text)
                logger.debug(f"Typed into {description}")
                return True
            except Exception:
                pass
            
            # Try as XPath
            try:
                await self.page.fill(f"xpath={element_ref}", text)
                logger.debug(f"Typed into {description} using XPath")
                return True
            except Exception:
                pass
            
            logger.warning(f"Could not type into {description} with ref: {element_ref}")
            return False
        except Exception as e:
            logger.error(f"Error typing into {description}: {e}")
            return False
    
    async def wait_for_text(self, text: str, timeout: int = 10) -> bool:
        """
        Wait for text to appear.
        
        Args:
            text: Text to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if text appeared
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return False
        
        try:
            # Playwright uses milliseconds for timeout
            await self.page.wait_for_selector(f"text={text}", timeout=timeout * 1000)
            return True
        except Exception as e:
            logger.debug(f"Text '{text}' did not appear within {timeout}s: {e}")
            return False
    
    async def wait_for_text_gone(self, text: str, timeout: int = 10) -> bool:
        """
        Wait for text to disappear.
        
        Args:
            text: Text to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if text disappeared
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return False
        
        try:
            # Wait for element with text to be removed
            await self.page.wait_for_selector(f"text={text}", state="hidden", timeout=timeout * 1000)
            return True
        except Exception:
            # If element doesn't exist, consider it "gone"
            return True
    
    async def select_option(self, element_ref: str, values: list, description: str) -> bool:
        """
        Select option(s) in a dropdown.
        
        Args:
            element_ref: Element reference
            values: List of values to select
            description: Human-readable description
            
        Returns:
            True if selection succeeded
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return False
        
        try:
            await self.page.select_option(element_ref, values)
            logger.debug(f"Selected option in {description}")
            return True
        except Exception as e:
            logger.error(f"Error selecting option in {description}: {e}")
            return False
    
    async def create_new_tab(self) -> bool:
        """
        Create a new browser tab.
        
        Returns:
            True if new tab was created
        """
        if not self.initialized or not self.context:
            logger.error("Playwright not initialized")
            return False
        
        try:
            self.page = await self.context.new_page()
            logger.info("Created new tab")
            return True
        except Exception as e:
            logger.error(f"Error creating new tab: {e}")
            return False
    
    async def close_tab(self) -> bool:
        """
        Close the current browser tab.
        
        Returns:
            True if tab was closed
        """
        if not self.initialized or not self.page:
            logger.error("Playwright not initialized")
            return False
        
        try:
            await self.page.close()
            # Get a new page from context
            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = await self.context.new_page()
            logger.info("Closed tab")
            return True
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
            return False
    
    async def cleanup(self):
        """Clean up Playwright resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.initialized = False
            logger.info("Playwright cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up Playwright: {e}")


# Global Playwright bridge instance
_playwright_bridge: Optional[PlaywrightBridge] = None


async def get_playwright_bridge(headless: bool = False) -> Optional[PlaywrightBridge]:
    """
    Get or create Playwright bridge instance.
    
    Args:
        headless: Whether to run browser in headless mode
        
    Returns:
        PlaywrightBridge instance or None if Playwright not available
    """
    global _playwright_bridge
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("Playwright not available. Install with: pip install playwright && playwright install")
        return None
    
    if _playwright_bridge is None:
        _playwright_bridge = PlaywrightBridge()
        await _playwright_bridge.initialize(headless=headless)
    
    return _playwright_bridge

