"""
Browser-based client for Pokemon Showdown using MCP browser automation tools.

This module replaces the WebSocket client with browser automation,
allowing the bot to interact with Pokemon Showdown through a visible browser.
"""
import asyncio
import logging
import json
import time
from typing import Optional, Dict, List, Any

from fp.browser_battle_parser import BrowserBattleParser
from fp.browser_move_mapper import BrowserMoveMapper
from fp.mcp_browser_bridge import MCPBrowserBridge

logger = logging.getLogger(__name__)


class BrowserClient:
    """
    Browser automation client for Pokemon Showdown.
    
    Uses MCP browser tools to navigate, interact with, and read state from
    the Pokemon Showdown web interface.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", wait_timeout: int = 10):
        """
        Initialize browser client.
        
        Args:
            base_url: Base URL for Pokemon Showdown (default: localhost for testing)
            wait_timeout: Timeout for waiting for UI elements (default: 10 seconds)
        """
        self.base_url = base_url
        self.current_url = None
        self.battle_tag = None
        self.opponent_name = None
        self.logged_in = False
        self.wait_timeout = wait_timeout
        
        # Initialize parser and mapper
        self.parser = BrowserBattleParser()
        self.mapper = BrowserMoveMapper()
        
    @classmethod
    async def create(cls, username: str, password: str, base_url: str = None, wait_timeout: int = 10, new_window: bool = True):
        """
        Create and initialize browser client.
        
        Args:
            username: Pokemon Showdown username
            password: Pokemon Showdown password (or empty for guest)
            base_url: Base URL (defaults to localhost:8000 or play.pokemonshowdown.com)
            wait_timeout: Timeout for waiting for UI elements
            new_window: If True, create a new browser window/tab (default: True)
        """
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:48','message':'BrowserClient.create called','data':{'username':username,'base_url':base_url,'wait_timeout':wait_timeout,'new_window':new_window},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        if base_url is None:
            # Default to localhost if it looks like local, otherwise use live server
            base_url = "http://localhost:8000"
        
        # Create new browser window/tab if requested
        if new_window:
            logger.info("Creating new browser window/tab")
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'browser_client.py:66','message':'Creating new browser tab','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
            except Exception as e:
                pass
            # #endregion
            await MCPBrowserBridge.create_new_tab()
        
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:73','message':'Creating BrowserClient instance','data':{'base_url':base_url},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        self = cls(base_url, wait_timeout)
        self.username = username
        self.password = password
        
        # Navigate to Pokemon Showdown
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:82','message':'Calling navigate_to_showdown','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        try:
            await self.navigate_to_showdown()
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'browser_client.py:89','message':'navigate_to_showdown completed','data':{'current_url':self.current_url},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
            except Exception as e:
                pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'browser_client.py:95','message':'navigate_to_showdown failed','data':{'error':str(e),'error_type':type(e).__name__},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
            except Exception as e2:
                pass
            # #endregion
            raise
        
        return self
    
    async def navigate_to_showdown(self, path: str = ""):
        """
        Navigate to Pokemon Showdown URL.
        
        Args:
            path: Optional path to append to base URL
        """
        url = f"{self.base_url}/{path}" if path else self.base_url
        logger.info(f"Navigating to {url}")
        
        # Initialize bridge if not already done
        await MCPBrowserBridge._initialize_bridge(headless=False)
        
        # Use MCP bridge to navigate
        success = await MCPBrowserBridge.navigate(url)
        if success:
            self.current_url = url
            logger.info(f"Successfully navigated to {url}")
        else:
            logger.error(f"Failed to navigate to {url}")
        
        return url
    
    async def login(self) -> str:
        """
        Log in to Pokemon Showdown via browser.
        
        Returns:
            User ID after successful login
        """
        logger.info(f"Logging in as {self.username}")
        
        # Take snapshot to see current page state
        snapshot = await self._get_snapshot()
        
        # Look for login button or username field
        # For guest login (local server), we might just need to enter username
        # For account login, we need username and password fields
        
        # Check if already logged in
        if self._check_logged_in(snapshot):
            logger.info("Already logged in")
            self.logged_in = True
            return self.username.lower()
        
        # Find and click login/username input
        # This is a placeholder - actual implementation will use MCP browser tools
        # to find and interact with login elements
        
        # For now, assume we're using guest login on local server
        # In production, we'd need to handle actual login flow
        self.logged_in = True
        return self.username.lower()
    
    async def search_for_battle(self, battle_format: str):
        """
        Search for a ladder battle in the specified format.
        
        Args:
            battle_format: Battle format (e.g., "gen9vgc2026regfbo3")
        """
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:187','message':'search_for_battle called','data':{'battle_format':battle_format},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        logger.info(f"Searching for {battle_format} battle")
        
        # Navigate to ladder/search page
        await self.navigate_to_showdown("ladder")
        await asyncio.sleep(1)  # Wait for page to load
        
        # Take snapshot to find format selector
        snapshot = await self._get_snapshot()
        
        # Find format dropdown/selector
        format_selector = self._find_format_selector(snapshot)
        
        if format_selector:
            # Select the format
            element_ref = format_selector.get("ref", "")
            if element_ref:
                # For ref bo3 battles, select "gen9vgc2026regfbo3"
                success = await MCPBrowserBridge.select_option(
                    element_ref,
                    [battle_format],
                    "Format selector"
                )
                if success:
                    logger.info(f"Selected format: {battle_format}")
                else:
                    logger.warning("Failed to select format")
            else:
                logger.warning("Format selector found but no ref available")
        else:
            logger.warning("Could not find format selector")
        
        # Find and click search/ladder button
        search_button = self._find_search_button(snapshot)
        
        if search_button:
            element_ref = search_button.get("ref", "")
            if element_ref:
                success = await MCPBrowserBridge.click(element_ref, "Search/Ladder button")
                if success:
                    logger.info("Clicked search/ladder button")
                else:
                    logger.warning("Failed to click search button")
            else:
                logger.warning("Search button found but no ref available")
        else:
            logger.warning("Could not find search/ladder button")
        
        # Wait for match to be found
        await self._wait_for_battle_start()
    
    async def challenge_user(self, username: str, battle_format: str):
        """
        Challenge a specific user to a battle.
        
        Args:
            username: Username to challenge
            battle_format: Battle format
        """
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:201','message':'challenge_user called','data':{'username':username,'battle_format':battle_format},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        logger.info(f"Challenging {username} to {battle_format}")
        
        # Get current snapshot to see the page state
        snapshot = await self._get_snapshot()
        
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:216','message':'Got snapshot for challenge','data':{'snapshot_keys':list(snapshot.keys()) if isinstance(snapshot,dict) else 'not_dict'},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        # Try to find and click challenge button or use chat command
        # Method 1: Look for user in lobby and click challenge button
        # Method 2: Use chat command: /challenge username, format
        
        # For now, try using chat command approach
        # Navigate to lobby if not already there
        if not self.current_url or "lobby" not in self.current_url.lower():
            await self.navigate_to_showdown("lobby")
        
        # Try to find chat input and send challenge command
        # Format: /challenge username, format
        challenge_command = f"/challenge {username}, {battle_format}"
        logger.info(f"Sending challenge command: {challenge_command}")
        
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:232','message':'Attempting to send challenge command','data':{'command':challenge_command},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        # Find chat input field and type the command
        snapshot = await self._get_snapshot()
        
        # Look for chat input field
        chat_input = self._find_chat_input(snapshot)
        
        if chat_input:
            # Type the challenge command
            element_ref = chat_input.get("ref", "")
            if element_ref:
                success = await MCPBrowserBridge.type_text(
                    element_ref,
                    challenge_command,
                    "Chat input"
                )
                if success:
                    # Press Enter to send
                    # Some MCP tools support submit parameter
                    await asyncio.sleep(0.5)  # Wait for typing to complete
                    logger.info(f"Challenge command sent: {challenge_command}")
                else:
                    logger.warning("Failed to type challenge command")
            else:
                logger.warning("Chat input found but no ref available")
        else:
            logger.warning("Could not find chat input field - challenge not sent")
        
        # Wait for battle to start
        await self._wait_for_battle_start()
    
    async def accept_challenge(self, battle_format: str, room_name: str = "lobby", timeout: int = 60):
        """
        Wait for and accept a challenge.
        
        Args:
            battle_format: Expected battle format
            room_name: Room to wait in (default: lobby)
            timeout: Maximum time to wait in seconds
        """
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:194','message':'accept_challenge called','data':{'battle_format':battle_format,'room_name':room_name,'timeout':timeout},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        logger.info(f"Waiting for {battle_format} challenge in {room_name}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            snapshot = await self._get_snapshot()
            
            # Look for challenge notification/button
            challenge_element = self._find_challenge_notification(snapshot, battle_format)
            
            if challenge_element:
                # Click accept button
                accept_button = self._find_accept_challenge_button(snapshot)
                
                if accept_button:
                    element_ref = accept_button.get("ref", "")
                    if element_ref:
                        success = await MCPBrowserBridge.click(element_ref, "Accept challenge button")
                        if success:
                            logger.info("Accepted challenge")
                            await self._wait_for_battle_start()
                            return
                        else:
                            logger.warning("Failed to click accept challenge button")
                    else:
                        logger.warning("Accept button found but no ref available")
                else:
                    logger.warning("Challenge found but no accept button")
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"No challenge received within {timeout} seconds")
    
    async def get_battle_state(self) -> Dict[str, Any]:
        """
        Get current battle state from browser.
        
        Returns:
            Dictionary containing battle state information
        """
        snapshot = await self._get_snapshot()
        
        # Parse battle state from snapshot using parser
        return self.parser.parse_battle_state(snapshot)
    
    async def select_move(self, decision: List[str], is_doubles: bool = False):
        """
        Select a move based on AI decision.
        
        Args:
            decision: Decision from AI (e.g., ["/choose move 1 2", "rqid"])
            is_doubles: Whether this is a doubles battle
        """
        logger.info(f"Selecting move: {decision[0]}")
        
        # Get current snapshot
        snapshot = await self._get_snapshot()
        
        # Use mapper to execute the decision
        success = await self.mapper.execute_decision(decision, snapshot, is_doubles)
        
        if not success:
            logger.error(f"Failed to execute decision: {decision[0]}")
        
        # Wait a bit for move to register
        await asyncio.sleep(0.5)
        return success
    
    async def select_team_preview(self, team_selection: str):
        """
        Select team during team preview.
        
        Args:
            team_selection: Team selection string (e.g., "1234" or "switch 1")
        """
        logger.info(f"Selecting team: {team_selection}")
        
        # Get current snapshot
        snapshot = await self._get_snapshot()
        
        # Use mapper to execute team preview selection
        success = await self.mapper.execute_team_preview(team_selection, snapshot)
        
        if not success:
            logger.error(f"Failed to execute team preview selection: {team_selection}")
        
        # Wait for battle to start
        await asyncio.sleep(1)
        return success
    
    async def _wait_for_battle_start(self):
        """Wait for battle to start after search/challenge."""
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:140','message':'wait_for_battle_start called','data':{},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        logger.info("Waiting for battle to start...")
        
        max_wait = 60  # 60 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            snapshot = await self._get_snapshot()
            
            # Check if battle has started (look for battle UI elements)
            if self._is_battle_active(snapshot):
                # Extract battle tag from URL or DOM
                self.battle_tag = self._extract_battle_tag(snapshot)
                self.opponent_name = self._extract_opponent_name(snapshot)
                logger.info(f"Battle started: {self.battle_tag} vs {self.opponent_name}")
                # #region agent log
                try:
                    with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({'location':'browser_client.py:155','message':'Battle started','data':{'battle_tag':self.battle_tag,'opponent_name':self.opponent_name},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
                except Exception as e:
                    pass
                # #endregion
                return
            
            await asyncio.sleep(0.5)
        
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:165','message':'Battle start timeout','data':{'elapsed':time.time()-start_time},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        raise TimeoutError("Battle did not start within timeout")
    
    async def check_battle_finished(self) -> Optional[str]:
        """
        Check if battle is finished and return winner if so.
        
        Returns:
            Winner username if battle finished, None otherwise
        """
        snapshot = await self._get_snapshot()
        
        # Look for win/loss messages
        winner = self._extract_winner(snapshot)
        return winner
    
    async def leave_battle(self, battle_tag: str):
        """Leave the battle room."""
        logger.info(f"Leaving battle {battle_tag}")
        
        # Look for leave/close button and click it
        snapshot = await self._get_snapshot()
        # Click leave button if found
        
        await asyncio.sleep(1)
    
    async def save_replay(self, battle_tag: str):
        """Save the battle replay."""
        logger.info(f"Saving replay for {battle_tag}")
        
        # Look for save replay button and click it
        snapshot = await self._get_snapshot()
        # Click save replay button if found
        
        await asyncio.sleep(1)
    
    # Internal helper methods
    
    async def _get_snapshot(self) -> Dict[str, Any]:
        """
        Get browser accessibility snapshot.
        
        Returns:
            Browser accessibility snapshot
        """
        return await MCPBrowserBridge.snapshot()
    
    async def _click_element(self, element_ref: str, description: str):
        """
        Click an element in the browser.
        
        Args:
            element_ref: Element reference from snapshot
            description: Human-readable description for logging
        """
        logger.debug(f"Clicking {description}")
        return await MCPBrowserBridge.click(element_ref, description)
    
    async def _wait_for_text(self, text: str, timeout: int = 10):
        """
        Wait for specific text to appear in the page.
        
        Args:
            text: Text to wait for
            timeout: Maximum time to wait
        """
        return await MCPBrowserBridge.wait_for_text(text, timeout)
    
    def _check_logged_in(self, snapshot: Dict[str, Any]) -> bool:
        """Check if user is logged in based on snapshot."""
        # Look for username in snapshot or logged-in indicators
        # Placeholder
        return self.logged_in
    
    def _has_challenge(self, snapshot: Dict[str, Any], battle_format: str) -> bool:
        """Check if there's a challenge notification."""
        return self._find_challenge_notification(snapshot, battle_format) is not None
    
    def _find_challenge_notification(self, snapshot: Dict[str, Any], battle_format: str) -> Optional[Dict[str, Any]]:
        """
        Find challenge notification in snapshot.
        
        Args:
            snapshot: Browser snapshot
            battle_format: Expected battle format
            
        Returns:
            Challenge notification element or None
        """
        if not snapshot:
            return None
        
        # Look for challenge text
        def search_for_challenge(node: Any, depth: int = 0) -> Optional[Dict[str, Any]]:
            if depth > 20:
                return None
            
            if not isinstance(node, dict):
                return None
            
            text = self._extract_text_content(node).lower()
            
            # Look for challenge indicators
            challenge_keywords = ["challenge", "wants to battle", "challenged you"]
            if any(keyword in text for keyword in challenge_keywords):
                # Check if format matches
                if battle_format.lower() in text or "bo3" in text:
                    return node
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    result = search_for_challenge(child, depth + 1)
                    if result:
                        return result
            
            return None
        
        return search_for_challenge(snapshot)
    
    def _find_accept_challenge_button(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find accept challenge button.
        
        Args:
            snapshot: Browser snapshot
            
        Returns:
            Accept button element or None
        """
        if not snapshot:
            return None
        
        # Look for accept button
        def search_for_accept_button(node: Any, depth: int = 0) -> Optional[Dict[str, Any]]:
            if depth > 20:
                return None
            
            if not isinstance(node, dict):
                return None
            
            role = node.get("role", "").lower()
            if "button" in role or node.get("type") == "button":
                text = self._extract_text_content(node).lower()
                if any(keyword in text for keyword in ["accept", "yes", "battle"]):
                    return node
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    result = search_for_accept_button(child, depth + 1)
                    if result:
                        return result
            
            return None
        
        return search_for_accept_button(snapshot)
    
    def _is_battle_active(self, snapshot: Dict[str, Any]) -> bool:
        """Check if battle is currently active."""
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'browser_client.py:449','message':'Checking if battle active','data':{'snapshot_type':type(snapshot).__name__,'snapshot_keys':list(snapshot.keys()) if isinstance(snapshot,dict) else 'not_dict'},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
        except Exception as e:
            pass
        # #endregion
        
        # Look for battle UI elements (Pokemon sprites, move buttons, etc.)
        # Check URL for battle room pattern: /battle-*
        if self.current_url and "/battle-" in self.current_url:
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'browser_client.py:460','message':'Battle URL detected','data':{'url':self.current_url},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'E'})+'\n')
            except Exception as e:
                pass
            # #endregion
            return True
        
        # Check snapshot for battle UI elements (requires parser implementation)
        # For now, return False if URL doesn't indicate battle
        return False
    
    def _extract_battle_tag(self, snapshot: Dict[str, Any]) -> Optional[str]:
        """Extract battle tag from URL or DOM."""
        battle_tag = self.parser.extract_battle_tag(snapshot)
        if battle_tag:
            self.battle_tag = battle_tag
        return self.battle_tag
    
    def _extract_opponent_name(self, snapshot: Dict[str, Any]) -> Optional[str]:
        """Extract opponent name from battle UI."""
        opponent_name = self.parser.extract_opponent_name(snapshot)
        if opponent_name:
            self.opponent_name = opponent_name
        return self.opponent_name
    
    def _extract_winner(self, snapshot: Dict[str, Any]) -> Optional[str]:
        """Extract winner from battle end message."""
        return self.parser.parse_winner(snapshot)
    
    def _find_chat_input(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find chat input field in snapshot.
        
        Args:
            snapshot: Browser snapshot
            
        Returns:
            Chat input element or None
        """
        if not snapshot:
            return None
        
        # Look for text input fields
        def search_for_input(node: Any, depth: int = 0) -> Optional[Dict[str, Any]]:
            if depth > 20:
                return None
            
            if not isinstance(node, dict):
                return None
            
            # Check if this is a text input
            role = node.get("role", "").lower()
            input_type = node.get("type", "").lower()
            
            if "textbox" in role or "text" in input_type or node.get("editable", False):
                # Check if it looks like a chat input
                # Chat inputs are typically in the lobby or battle room
                text = self._extract_text_content(node).lower()
                if "chat" in text or "message" in text or node.get("placeholder", "").lower():
                    return node
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    result = search_for_input(child, depth + 1)
                    if result:
                        return result
            
            return None
        
        return search_for_input(snapshot)
    
    def _extract_text_content(self, element: Dict[str, Any]) -> str:
        """Extract text content from an element."""
        if not isinstance(element, dict):
            return ""
        
        text = element.get("text", "") or element.get("name", "") or element.get("label", "")
        
        children = element.get("children", [])
        if isinstance(children, list):
            child_texts = [self._extract_text_content(child) for child in children]
            text += " " + " ".join(filter(None, child_texts))
        
        return text.strip()
    
    def _find_format_selector(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find format selector dropdown.
        
        Args:
            snapshot: Browser snapshot
            
        Returns:
            Format selector element or None
        """
        if not snapshot:
            return None
        
        # Look for dropdown/combobox elements
        def search_for_selector(node: Any, depth: int = 0) -> Optional[Dict[str, Any]]:
            if depth > 20:
                return None
            
            if not isinstance(node, dict):
                return None
            
            role = node.get("role", "").lower()
            input_type = node.get("type", "").lower()
            
            # Look for combobox or select elements
            if "combobox" in role or "listbox" in role or "select" in input_type:
                # Check if it might be format selector
                text = self._extract_text_content(node).lower()
                if any(keyword in text for keyword in ["format", "battle", "ladder", "vgc"]):
                    return node
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    result = search_for_selector(child, depth + 1)
                    if result:
                        return result
            
            return None
        
        return search_for_selector(snapshot)
    
    def _find_search_button(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find search/ladder button.
        
        Args:
            snapshot: Browser snapshot
            
        Returns:
            Search button element or None
        """
        if not snapshot:
            return None
        
        # Look for buttons with search/ladder text
        def search_for_button(node: Any, depth: int = 0) -> Optional[Dict[str, Any]]:
            if depth > 20:
                return None
            
            if not isinstance(node, dict):
                return None
            
            role = node.get("role", "").lower()
            if "button" in role or node.get("type") == "button":
                text = self._extract_text_content(node).lower()
                if any(keyword in text for keyword in ["search", "ladder", "find battle", "battle"]):
                    return node
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    result = search_for_button(child, depth + 1)
                    if result:
                        return result
            
            return None
        
        return search_for_button(snapshot)

