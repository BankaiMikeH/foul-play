"""
Map AI decisions to browser button clicks.

This module converts AI move decisions (like "move 1 2" or "switch pokemonname")
into actual browser interactions (clicking buttons, selecting targets, etc.).
"""
import logging
import re
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class BrowserMoveMapper:
    """
    Maps AI decisions to browser button clicks.
    """
    
    def __init__(self):
        """Initialize the mapper."""
        pass
    
    async def execute_decision(
        self, 
        decision: List[str], 
        snapshot: Dict[str, Any],
        is_doubles: bool = False
    ) -> bool:
        """
        Execute an AI decision by clicking appropriate browser buttons.
        
        Args:
            decision: Decision from AI (e.g., ["/choose move 1 2", "rqid"])
            snapshot: Current browser snapshot
            is_doubles: Whether this is a doubles battle
            
        Returns:
            True if decision was executed successfully
        """
        if not decision or len(decision) < 1:
            logger.error("Empty decision provided")
            return False
        
        command = decision[0]
        logger.info(f"Executing decision: {command}")
        
        # Parse the command
        if command.startswith("/choose"):
            # Remove "/choose" prefix
            command = command[7:].strip()
        
        # Handle doubles vs singles
        if is_doubles:
            return await self._execute_doubles_decision(command, snapshot)
        else:
            return await self._execute_singles_decision(command, snapshot)
    
    async def _execute_singles_decision(
        self, 
        command: str, 
        snapshot: Dict[str, Any]
    ) -> bool:
        """
        Execute a singles battle decision.
        
        Args:
            command: Decision command (e.g., "move 1" or "switch 2")
            snapshot: Browser snapshot
            
        Returns:
            True if successful
        """
        command = command.strip()
        
        if command.startswith("move"):
            # Move decision: "move 1" or "move 1 mega" or "move 1 tera"
            return await self._click_move_singles(command, snapshot)
        elif command.startswith("switch"):
            # Switch decision: "switch 2" or "switch pokemonname"
            return await self._click_switch_singles(command, snapshot)
        else:
            logger.error(f"Unknown singles command: {command}")
            return False
    
    async def _execute_doubles_decision(
        self, 
        command: str, 
        snapshot: Dict[str, Any]
    ) -> bool:
        """
        Execute a doubles battle decision.
        
        Args:
            command: Decision command (e.g., "move 1 1, move 2 2")
            snapshot: Browser snapshot
            
        Returns:
            True if successful
        """
        # Split into left and right decisions
        if ", " in command:
            parts = command.split(", ", 1)
            left_decision = parts[0].strip()
            right_decision = parts[1].strip() if len(parts) > 1 else None
        elif "," in command:
            parts = command.split(",", 1)
            left_decision = parts[0].strip()
            right_decision = parts[1].strip() if len(parts) > 1 else None
        else:
            # Single decision (may happen during force switch)
            left_decision = command.strip()
            right_decision = None
        
        # Execute left position decision (position 0)
        left_success = await self._execute_position_decision(
            left_decision, snapshot, position=0
        )
        
        # Execute right position decision (position 1) if present
        right_success = True
        if right_decision:
            right_success = await self._execute_position_decision(
                right_decision, snapshot, position=1
            )
        
        # Both must succeed for doubles
        return left_success and right_success
    
    async def _execute_position_decision(
        self,
        decision: str,
        snapshot: Dict[str, Any],
        position: int
    ) -> bool:
        """
        Execute a decision for a specific position in doubles.
        
        Args:
            decision: Decision for this position
            snapshot: Browser snapshot
            position: Position (0 = left, 1 = right)
            
        Returns:
            True if successful
        """
        if not decision or decision == "pass":
            # No action needed for this position
            return True
        
        if decision.startswith("move"):
            return await self._click_move_doubles(decision, snapshot, position)
        elif decision.startswith("switch"):
            return await self._click_switch_doubles(decision, snapshot, position)
        else:
            logger.error(f"Unknown position decision: {decision}")
            return False
    
    async def _click_move_singles(
        self, 
        command: str, 
        snapshot: Dict[str, Any]
    ) -> bool:
        """
        Click a move button for singles.
        
        Args:
            command: Move command (e.g., "move 1" or "move 1 mega")
            snapshot: Browser snapshot
            
        Returns:
            True if successful
        """
        # Parse move number and modifiers
        parts = command.split()
        if len(parts) < 2:
            logger.error(f"Invalid move command: {command}")
            return False
        
        move_index = int(parts[1])  # 1-4
        modifiers = parts[2:] if len(parts) > 2 else []
        
        # Find move button (1-indexed, so button 1 = first move)
        move_button = self._find_move_button(snapshot, move_index - 1)
        
        if not move_button:
            logger.error(f"Could not find move button {move_index}")
            return False
        
        # Click the move button
        await self._click_element(move_button, f"Move {move_index}")
        
        # Handle modifiers (mega, tera, dynamax)
        for modifier in modifiers:
            if modifier in ["mega", "tera", "dynamax", "zmove"]:
                await self._click_modifier(snapshot, modifier)
        
        return True
    
    async def _click_move_doubles(
        self,
        command: str,
        snapshot: Dict[str, Any],
        position: int
    ) -> bool:
        """
        Click a move button for doubles at specific position.
        
        Args:
            command: Move command (e.g., "move 1 2" = move 1, target 2)
            snapshot: Browser snapshot
            position: Pokemon position (0 = left, 1 = right)
            
        Returns:
            True if successful
        """
        # Parse: "move 1 2" = move index 1, target 2
        parts = command.split()
        if len(parts) < 2:
            logger.error(f"Invalid doubles move command: {command}")
            return False
        
        move_index = int(parts[1]) - 1  # Convert to 0-indexed
        target = int(parts[2]) if len(parts) > 2 else None
        
        # Find move button for this position
        move_button = self._find_move_button(snapshot, move_index, position)
        
        if not move_button:
            logger.error(f"Could not find move button {move_index + 1} for position {position}")
            return False
        
        # Click the move button
        await self._click_element(move_button, f"Move {move_index + 1} (position {position})")
        
        # Handle targeting if needed
        if target is not None:
            await self._select_target(snapshot, target, position)
        
        return True
    
    async def _click_switch_singles(
        self,
        command: str,
        snapshot: Dict[str, Any]
    ) -> bool:
        """
        Click a switch button for singles.
        
        Args:
            command: Switch command (e.g., "switch 2" or "switch pokemonname")
            snapshot: Browser snapshot
            
        Returns:
            True if successful
        """
        # Parse switch target
        parts = command.split()
        if len(parts) < 2:
            logger.error(f"Invalid switch command: {command}")
            return False
        
        switch_target = parts[1]
        
        # Try to parse as number first
        try:
            pokemon_index = int(switch_target) - 1  # Convert to 0-indexed
            switch_button = self._find_switch_button_by_index(snapshot, pokemon_index)
        except ValueError:
            # Not a number, treat as Pokemon name
            switch_button = self._find_switch_button_by_name(snapshot, switch_target)
        
        if not switch_button:
            logger.error(f"Could not find switch button for: {switch_target}")
            return False
        
        await self._click_element(switch_button, f"Switch to {switch_target}")
        return True
    
    async def _click_switch_doubles(
        self,
        command: str,
        snapshot: Dict[str, Any],
        position: int
    ) -> bool:
        """
        Click a switch button for doubles at specific position.
        
        Args:
            command: Switch command
            snapshot: Browser snapshot
            position: Pokemon position (0 = left, 1 = right)
            
        Returns:
            True if successful
        """
        # Similar to singles, but need to ensure we're switching the right position
        parts = command.split()
        if len(parts) < 2:
            logger.error(f"Invalid doubles switch command: {command}")
            return False
        
        switch_target = parts[1]
        
        # Find switch button (may need to specify position)
        try:
            pokemon_index = int(switch_target) - 1
            switch_button = self._find_switch_button_by_index(
                snapshot, pokemon_index, position
            )
        except ValueError:
            switch_button = self._find_switch_button_by_name(
                snapshot, switch_target, position
            )
        
        if not switch_button:
            logger.error(f"Could not find switch button for: {switch_target} at position {position}")
            return False
        
        await self._click_element(
            switch_button, 
            f"Switch to {switch_target} (position {position})"
        )
        return True
    
    async def _select_target(
        self,
        snapshot: Dict[str, Any],
        target: int,
        attacker_position: int
    ) -> bool:
        """
        Select target for a move in doubles.
        
        Args:
            snapshot: Browser snapshot
            target: Target number (1 = left opponent, 2 = right opponent, etc.)
            attacker_position: Position of attacking Pokemon
            
        Returns:
            True if successful
        """
        # After clicking a move, targeting UI may appear
        # Need to click on the target Pokemon or target indicator
        
        # Target mapping:
        # 1 = Left opponent
        # 2 = Right opponent
        # 0 = Both opponents (spread move)
        # -1 = Self/ally
        
        target_button = self._find_target_button(snapshot, target, attacker_position)
        
        if target_button:
            await self._click_element(target_button, f"Target {target}")
            return True
        else:
            # Some moves may auto-target, so this might be OK
            logger.debug(f"Could not find target button for target {target}, may auto-target")
            return True
    
    async def _click_modifier(
        self,
        snapshot: Dict[str, Any],
        modifier: str
    ) -> bool:
        """
        Click a modifier button (mega, tera, dynamax, zmove).
        
        Args:
            snapshot: Browser snapshot
            modifier: Modifier name ("mega", "tera", "dynamax", "zmove")
            
        Returns:
            True if successful
        """
        modifier_button = self._find_modifier_button(snapshot, modifier)
        
        if modifier_button:
            await self._click_element(modifier_button, f"{modifier.capitalize()} button")
            return True
        else:
            logger.warning(f"Could not find {modifier} button")
            return False
    
    async def execute_team_preview(
        self,
        team_selection: str,
        snapshot: Dict[str, Any]
    ) -> bool:
        """
        Execute team preview selection.
        
        Args:
            team_selection: Team selection string (e.g., "1234" for first 4 Pokemon)
            snapshot: Browser snapshot
            
        Returns:
            True if successful
        """
        logger.info(f"Selecting team: {team_selection}")
        
        # Parse team selection
        # Format: "1234" means select Pokemon 1, 2, 3, 4
        # Or "switch 1" format from AI decision
        
        if team_selection.startswith("switch"):
            # Extract number
            parts = team_selection.split()
            if len(parts) >= 2:
                lead_index = int(parts[1]) - 1  # Convert to 0-indexed
            else:
                lead_index = 0
        else:
            # Assume first Pokemon is lead
            lead_index = 0
        
        # Click on Pokemon in team preview
        # For VGC doubles, we typically select 4 Pokemon
        # The AI decision may specify which Pokemon to lead with
        
        # Find team preview Pokemon buttons
        team_buttons = self._find_team_preview_buttons(snapshot)
        
        if not team_buttons:
            logger.error("Could not find team preview buttons")
            return False
        
        # Click on selected Pokemon
        # For now, click the first one (lead)
        if lead_index < len(team_buttons):
            await self._click_element(
                team_buttons[lead_index], 
                f"Team preview Pokemon {lead_index + 1}"
            )
        
        # May need to click confirm/start button
        confirm_button = self._find_confirm_button(snapshot)
        if confirm_button:
            await self._click_element(confirm_button, "Confirm team selection")
        
        return True
    
    # Helper methods for finding elements
    
    def _find_move_button(
        self, 
        snapshot: Dict[str, Any], 
        move_index: int,
        position: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find move button by index.
        
        Args:
            snapshot: Browser snapshot
            move_index: Move index (0-3, 0-indexed)
            position: Position for doubles (0 or 1), None for singles
            
        Returns:
            Button element or None
        """
        if not snapshot:
            return None
        
        # Find all buttons that look like move buttons
        all_buttons = self._find_all_buttons(snapshot)
        move_buttons = []
        
        for button in all_buttons:
            if self._looks_like_move_button(button):
                move_buttons.append(button)
        
        # Filter by position if doubles
        if position is not None:
            # For doubles, we need to find buttons for specific position
            # This is complex - we'd need to understand the UI layout
            # For now, try to find buttons that might be for this position
            # In a full implementation, we'd parse the UI structure
            pass
        
        # Return the move button at the requested index
        if move_index < len(move_buttons):
            return move_buttons[move_index]
        
        # Fallback: try to find by move number in text
        # Some UIs show "Move 1", "Move 2", etc.
        move_number = move_index + 1
        for button in all_buttons:
            text = self._extract_text_content(button).lower()
            if f"move {move_number}" in text or f"move{move_number}" in text:
                return button
        
        return None
    
    def _find_switch_button_by_index(
        self,
        snapshot: Dict[str, Any],
        pokemon_index: int,
        position: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find switch button by Pokemon index.
        
        Args:
            snapshot: Browser snapshot
            pokemon_index: Pokemon index (0-indexed)
            position: Position for doubles
        
        Returns:
            Button element or None
        """
        if not snapshot:
            return None
        
        # Find all elements that might be Pokemon in reserve/team panel
        # Look for buttons or clickable elements with Pokemon names
        all_buttons = self._find_all_buttons(snapshot)
        pokemon_buttons = []
        
        for button in all_buttons:
            text = self._extract_text_content(button)
            # Check if this looks like a Pokemon button
            # Pokemon buttons typically have Pokemon names
            if self._looks_like_pokemon_button(button):
                pokemon_buttons.append(button)
        
        # Return the Pokemon at the requested index
        if pokemon_index < len(pokemon_buttons):
            return pokemon_buttons[pokemon_index]
        
        # Fallback: try to find by Pokemon number
        pokemon_number = pokemon_index + 1
        for button in all_buttons:
            text = self._extract_text_content(button).lower()
            if f"pokemon {pokemon_number}" in text or f"#{pokemon_number}" in text:
                return button
        
        return None
    
    def _find_switch_button_by_name(
        self,
        snapshot: Dict[str, Any],
        pokemon_name: str,
        position: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find switch button by Pokemon name.
        
        Args:
            snapshot: Browser snapshot
            pokemon_name: Pokemon name
            position: Position for doubles
        
        Returns:
            Button element or None
        """
        if not snapshot:
            return None
        
        pokemon_name_lower = pokemon_name.lower()
        
        # Find all buttons that might be Pokemon
        all_buttons = self._find_all_buttons(snapshot)
        
        for button in all_buttons:
            text = self._extract_text_content(button).lower()
            # Check if Pokemon name appears in button text
            if pokemon_name_lower in text:
                # Verify it's actually a Pokemon button
                if self._looks_like_pokemon_button(button):
                    return button
        
        return None
    
    def _find_target_button(
        self,
        snapshot: Dict[str, Any],
        target: int,
        attacker_position: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find target selection button.
        
        Args:
            snapshot: Browser snapshot
            target: Target number (1 = left opponent, 2 = right opponent, etc.)
            attacker_position: Attacking Pokemon position
        
        Returns:
            Button element or None
        """
        if not snapshot:
            return None
        
        # After clicking a move, targeting UI may appear
        # Look for target selection buttons
        all_buttons = self._find_all_buttons(snapshot)
        
        # Target mapping:
        # 1 = Left opponent
        # 2 = Right opponent
        # 0 = Both opponents (spread move)
        # -1 = Self/ally
        
        target_labels = {
            1: ["left", "opponent 1", "target 1", "enemy left"],
            2: ["right", "opponent 2", "target 2", "enemy right"],
            0: ["both", "all", "spread"],
            -1: ["self", "ally", "partner"]
        }
        
        labels = target_labels.get(target, [])
        
        for button in all_buttons:
            text = self._extract_text_content(button).lower()
            if any(label in text for label in labels):
                return button
        
        # Fallback: try to find by target number
        for button in all_buttons:
            text = self._extract_text_content(button).lower()
            if f"target {target}" in text or f"#{target}" in text:
                return button
        
        return None
    
    def _find_modifier_button(
        self,
        snapshot: Dict[str, Any],
        modifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find modifier button (mega, tera, etc.).
        
        Args:
            snapshot: Browser snapshot
            modifier: Modifier name
        
        Returns:
            Button element or None
        """
        if not snapshot:
            return None
        
        modifier_lower = modifier.lower()
        
        # Look for modifier buttons
        all_buttons = self._find_all_buttons(snapshot)
        
        for button in all_buttons:
            text = self._extract_text_content(button).lower()
            if modifier_lower in text:
                return button
        
        # Also check for modifier icons/images
        # Modifiers might be represented as icons rather than text buttons
        # This would require more sophisticated parsing
        
        return None
    
    def _find_team_preview_buttons(
        self,
        snapshot: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find team preview Pokemon buttons.
        
        Args:
            snapshot: Browser snapshot
        
        Returns:
            List of Pokemon button elements
        """
        if not snapshot:
            return []
        
        # Find all buttons that might be Pokemon in team preview
        all_buttons = self._find_all_buttons(snapshot)
        pokemon_buttons = []
        
        for button in all_buttons:
            if self._looks_like_pokemon_button(button):
                pokemon_buttons.append(button)
        
        return pokemon_buttons
    
    def _find_confirm_button(
        self,
        snapshot: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find confirm/start battle button.
        
        Args:
            snapshot: Browser snapshot
        
        Returns:
            Button element or None
        """
        if not snapshot:
            return None
        
        # Look for confirm/start buttons
        all_buttons = self._find_all_buttons(snapshot)
        
        confirm_labels = [
            "start battle",
            "confirm",
            "ready",
            "begin",
            "go"
        ]
        
        for button in all_buttons:
            text = self._extract_text_content(button).lower()
            if any(label in text for label in confirm_labels):
                return button
        
        return None
    
    # Helper methods for element finding
    
    def _find_all_buttons(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all buttons in the snapshot recursively.
        
        Args:
            snapshot: Browser snapshot
        
        Returns:
            List of button elements
        """
        buttons = []
        
        def search(node: Any, depth: int = 0) -> None:
            if depth > 20:
                return
            
            if not isinstance(node, dict):
                return
            
            # Check if this is a button
            role = node.get("role", "").lower()
            if "button" in role or node.get("type") == "button":
                buttons.append(node)
            
            # Also check for clickable elements
            if node.get("clickable", False) or node.get("enabled", True):
                # Might be a button even if not explicitly marked
                text = self._extract_text_content(node)
                if text and len(text) < 50:  # Buttons typically have short text
                    # Check if it looks like a button
                    if any(keyword in text.lower() for keyword in ["move", "switch", "confirm", "start", "select"]):
                        if node not in buttons:
                            buttons.append(node)
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    search(child, depth + 1)
        
        search(snapshot)
        return buttons
    
    def _looks_like_move_button(self, element: Dict[str, Any]) -> bool:
        """
        Check if an element looks like a move button.
        
        Args:
            element: Element to check
        
        Returns:
            True if it looks like a move button
        """
        text = self._extract_text_content(element).lower()
        
        # Move buttons typically have:
        # - PP information (e.g., "15/15")
        # - Move names
        # - Type indicators
        
        # Check for PP pattern
        if re.search(r'\d+/\d+', text):
            return True
        
        # Check for common move-related words
        move_indicators = ["pp", "move", "type"]
        if any(indicator in text for indicator in move_indicators):
            return True
        
        return False
    
    def _looks_like_pokemon_button(self, element: Dict[str, Any]) -> bool:
        """
        Check if an element looks like a Pokemon button.
        
        Args:
            element: Element to check
        
        Returns:
            True if it looks like a Pokemon button
        """
        text = self._extract_text_content(element)
        
        # Pokemon buttons typically have Pokemon names
        # Pokemon names are typically capitalized single words
        words = text.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 2:
                # Check if it's not a common UI word
                if word.lower() not in ["hp", "pp", "status", "active", "switch", "move", "button", "pokemon", "team"]:
                    return True
        
        return False
    
    def _extract_text_content(self, element: Dict[str, Any]) -> str:
        """
        Extract text content from an element.
        
        Args:
            element: Element from snapshot
        
        Returns:
            Text content
        """
        if not isinstance(element, dict):
            return ""
        
        # Try different text fields
        text = element.get("text", "") or element.get("name", "") or element.get("label", "")
        
        # Also check children for text
        children = element.get("children", [])
        if isinstance(children, list):
            child_texts = [self._extract_text_content(child) for child in children]
            text += " " + " ".join(filter(None, child_texts))
        
        return text.strip()
    
    async def _click_element(
        self,
        element: Dict[str, Any],
        description: str
    ):
        """
        Click an element using MCP browser tool.
        
        Args:
            element: Element to click (should have 'ref' field)
            description: Description for logging
        """
        from fp.mcp_browser_bridge import MCPBrowserBridge
        
        element_ref = element.get("ref", "") if isinstance(element, dict) else str(element)
        await MCPBrowserBridge.click(element_ref, description)

