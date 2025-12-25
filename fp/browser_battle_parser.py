"""
Parse battle state from browser accessibility snapshots.

This module extracts battle information from the Pokemon Showdown
browser interface by parsing the accessibility tree.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class BrowserBattleParser:
    """
    Parser for extracting battle state from browser snapshots.
    """
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    def parse_battle_state(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse complete battle state from browser snapshot.
        
        Args:
            snapshot: Browser accessibility snapshot
            
        Returns:
            Dictionary containing parsed battle state
        """
        state = {
            "active_pokemon": self.parse_active_pokemon(snapshot),
            "reserve_pokemon": self.parse_reserve_pokemon(snapshot),
            "opponent_pokemon": self.parse_opponent_pokemon(snapshot),
            "available_moves": self.parse_available_moves(snapshot),
            "turn_state": self.parse_turn_state(snapshot),
            "battle_format": self.parse_battle_format(snapshot),
            "battle_finished": self.check_battle_finished(snapshot),
            "winner": None,
            "team_preview": self.check_team_preview(snapshot),
        }
        
        if state["battle_finished"]:
            state["winner"] = self.parse_winner(snapshot)
        
        return state
    
    def parse_active_pokemon(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse active Pokemon from battle UI.
        
        Returns:
            List of active Pokemon dictionaries with name, HP, status, etc.
        """
        active_pokemon = []
        
        if not snapshot:
            return active_pokemon
        
        # Search for active Pokemon in the battle UI
        # Look for elements that might represent active Pokemon
        # Common patterns:
        # - Pokemon names in battle area
        # - HP bars with Pokemon names
        # - Pokemon sprites with labels
        
        # Search recursively through the snapshot tree
        def search_for_pokemon(node: Any, depth: int = 0) -> None:
            if depth > 20:  # Prevent infinite recursion
                return
            
            if not isinstance(node, dict):
                return
            
            # Check if this node might be a Pokemon
            text = self._extract_text_content(node)
            role = node.get("role", "")
            name = node.get("name", "")
            
            # Look for Pokemon indicators
            # Pokemon Showdown typically shows Pokemon names, HP, status
            pokemon_indicators = [
                "hp", "status", "fainted", "active", "pokemon"
            ]
            
            # Check if this looks like a Pokemon element
            is_pokemon_element = False
            pokemon_name = None
            hp_info = None
            status = None
            
            # Try to extract Pokemon name from text
            # Pokemon names are typically capitalized single words
            if text:
                # Look for Pokemon name patterns
                words = text.split()
                for word in words:
                    # Simple heuristic: capitalized word that might be a Pokemon name
                    if word and word[0].isupper() and len(word) > 2:
                        # Check if it's not a common UI word
                        if word.lower() not in ["hp", "pp", "status", "active", "switch", "move"]:
                            pokemon_name = word
                            is_pokemon_element = True
                            break
            
            # Look for HP information
            hp_match = re.search(r'(\d+)\s*/\s*(\d+)\s*hp', text.lower())
            if hp_match:
                hp_info = (int(hp_match.group(1)), int(hp_match.group(2)))
                is_pokemon_element = True
            
            # Look for status conditions
            status_conditions = ["burn", "poison", "paralyze", "sleep", "freeze", "toxic"]
            for condition in status_conditions:
                if condition in text.lower():
                    status = condition
                    is_pokemon_element = True
                    break
            
            if is_pokemon_element and pokemon_name:
                active_pokemon.append({
                    "name": pokemon_name.lower(),
                    "hp": hp_info,
                    "status": status,
                    "element": node
                })
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    search_for_pokemon(child, depth + 1)
        
        # Start search from root
        search_for_pokemon(snapshot)
        
        # Limit to reasonable number (singles = 1, doubles = 2)
        return active_pokemon[:2]
    
    def parse_reserve_pokemon(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse reserve Pokemon (available for switching).
        
        Returns:
            List of reserve Pokemon dictionaries
        """
        reserve_pokemon = []
        
        if not snapshot:
            return reserve_pokemon
        
        # Look for reserve Pokemon in team panel
        # These are typically in a sidebar or bottom panel
        # May be smaller sprites or icons
        
        def search_for_reserve(node: Any, depth: int = 0) -> None:
            if depth > 20:
                return
            
            if not isinstance(node, dict):
                return
            
            text = self._extract_text_content(node)
            role = node.get("role", "")
            
            # Look for reserve/team panel indicators
            # Pokemon Showdown shows reserve Pokemon in a team panel
            # Look for elements that might be in a team/reserve area
            
            # Check if this might be a reserve Pokemon
            # Reserve Pokemon are typically shown as smaller elements
            # May have Pokemon names or sprites
            
            if text:
                words = text.split()
                for word in words:
                    if word and word[0].isupper() and len(word) > 2:
                        if word.lower() not in ["hp", "pp", "status", "active", "switch", "move", "team"]:
                            # Check if we haven't already added this Pokemon
                            existing = any(p.get("name") == word.lower() for p in reserve_pokemon)
                            if not existing:
                                reserve_pokemon.append({
                                    "name": word.lower(),
                                    "element": node
                                })
            
            # Recursively search children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    search_for_reserve(child, depth + 1)
        
        search_for_reserve(snapshot)
        
        return reserve_pokemon[:6]  # Max 6 Pokemon in team
    
    def parse_opponent_pokemon(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse opponent's Pokemon information.
        
        Returns:
            List of opponent Pokemon dictionaries
        """
        opponent_pokemon = []
        
        # Similar to active Pokemon but on opponent's side
        # May have less information visible
        
        # For now, use similar logic to active Pokemon
        # In a full implementation, we'd distinguish between
        # user's side and opponent's side
        
        return opponent_pokemon
    
    def parse_available_moves(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse available moves from move buttons.
        
        Returns:
            List of move dictionaries with name, PP, disabled status, etc.
        """
        moves = []
        
        if not snapshot:
            return moves
        
        # Look for move buttons
        # Pokemon Showdown shows 4 move buttons
        # Each button typically shows:
        # - Move name
        # - PP remaining (e.g., "15/15" or "0/15")
        # - Type indicator
        # - Disabled state
        
        buttons = self._find_buttons(snapshot)
        
        for button in buttons:
            text = self._extract_text_content(button)
            if not text:
                continue
            
            # Check if this looks like a move button
            # Move buttons typically contain:
            # - Move name (capitalized words)
            # - PP information
            # - Type indicators
            
            # Look for PP pattern
            pp_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
            
            # Look for move name (typically before PP)
            move_name = None
            if pp_match:
                # Extract text before PP as move name
                move_text = text[:pp_match.start()].strip()
                if move_text:
                    # Take first capitalized word as move name
                    words = move_text.split()
                    for word in words:
                        if word and word[0].isupper():
                            move_name = word.lower()
                            break
            
            # If no PP found, might still be a move button
            if not move_name and text:
                # Try to extract move name from text
                words = text.split()
                for word in words:
                    if word and word[0].isupper() and len(word) > 2:
                        # Check if it's not a common UI word
                        if word.lower() not in ["hp", "pp", "status", "active", "switch", "move", "button"]:
                            move_name = word.lower()
                            break
            
            if move_name:
                # Check if disabled
                disabled = "disabled" in text.lower() or button.get("disabled", False)
                
                moves.append({
                    "name": move_name,
                    "pp": (int(pp_match.group(1)), int(pp_match.group(2))) if pp_match else None,
                    "disabled": disabled,
                    "element": button
                })
        
        # Limit to 4 moves (standard Pokemon has 4 moves)
        return moves[:4]
    
    def parse_turn_state(self, snapshot: Dict[str, Any]) -> str:
        """
        Determine current turn state.
        
        Returns:
            State string: "waiting_for_move", "team_preview", "battle_ended", etc.
        """
        if not snapshot:
            return "unknown"
        
        # Check for various UI states
        text_content = self._extract_all_text(snapshot).lower()
        
        # Check for team preview
        if any(indicator in text_content for indicator in ["choose your pokemon", "team preview", "select pokemon"]):
            return "team_preview"
        
        # Check for battle ended
        if any(indicator in text_content for indicator in ["won", "lost", "battle ended", "forfeit"]):
            return "battle_ended"
        
        # Check for waiting for opponent
        if any(indicator in text_content for indicator in ["waiting for opponent", "opponent is choosing"]):
            return "waiting_for_opponent"
        
        # Check for move buttons (indicates waiting for move)
        buttons = self._find_buttons(snapshot)
        move_buttons = [b for b in buttons if self._looks_like_move_button(b)]
        
        if move_buttons:
            return "waiting_for_move"
        
        # Default to waiting for move if we can't determine
        return "waiting_for_move"
    
    def parse_battle_format(self, snapshot: Dict[str, Any]) -> str:
        """
        Determine battle format (singles vs doubles).
        
        Returns:
            "singles" or "doubles"
        """
        if not snapshot:
            return "singles"
        
        text_content = self._extract_all_text(snapshot).lower()
        
        # Check for doubles indicators
        if any(indicator in text_content for indicator in ["doubles", "vgc", "2v2"]):
            return "doubles"
        
        # Check for two active Pokemon areas (doubles has 2 on each side)
        # This is a heuristic - in a full implementation we'd parse the UI structure
        
        return "singles"
    
    def check_team_preview(self, snapshot: Dict[str, Any]) -> bool:
        """
        Check if team preview interface is active.
        
        Returns:
            True if team preview is active
        """
        if not snapshot:
            return False
        
        text_content = self._extract_all_text(snapshot).lower()
        
        return any(indicator in text_content for indicator in [
            "choose your pokemon",
            "team preview",
            "select pokemon",
            "pick your team"
        ])
    
    def check_battle_finished(self, snapshot: Dict[str, Any]) -> bool:
        """
        Check if battle has finished.
        
        Returns:
            True if battle is finished
        """
        if not snapshot:
            return False
        
        text_content = self._extract_all_text(snapshot).lower()
        
        return any(indicator in text_content for indicator in [
            "won",
            "lost",
            "battle ended",
            "forfeit",
            "victory",
            "defeat"
        ])
    
    def parse_winner(self, snapshot: Dict[str, Any]) -> Optional[str]:
        """
        Parse winner from battle end message.
        
        Returns:
            Winner username or None
        """
        if not snapshot:
            return None
        
        text_content = self._extract_all_text(snapshot)
        
        # Look for win message patterns
        # Common patterns:
        # - "PlayerName won!"
        # - "You won!" or "You lost!"
        # - "PlayerName forfeited"
        
        win_patterns = [
            r'(\w+)\s+won',
            r'(\w+)\s+won!',
            r'winner:\s*(\w+)',
        ]
        
        for pattern in win_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        
        # Check for "You won" vs "You lost"
        if "you won" in text_content.lower():
            # Would need to know our username - return None for now
            return None
        elif "you lost" in text_content.lower():
            # Opponent won - would need to extract opponent name
            return None
        
        return None
    
    def parse_request_json(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse request JSON from battle UI.
        
        This is a fallback - ideally we'd get this from WebSocket,
        but for browser-only mode we may need to reconstruct it.
        
        Returns:
            Request JSON dictionary or None
        """
        # Reconstructing request JSON from UI is very difficult
        # We'll need to infer from visible elements
        # For now, return None - this would need significant work
        return None
    
    def extract_battle_tag(self, snapshot: Dict[str, Any]) -> Optional[str]:
        """
        Extract battle tag from URL or DOM.
        
        Returns:
            Battle tag (e.g., "battle-gen9vgc2025regh-123456") or None
        """
        if not snapshot:
            return None
        
        # Battle tag might be in:
        # - URL (accessible through snapshot metadata if available)
        # - Page title
        # - Battle room identifier in DOM
        
        # Check if snapshot has URL information
        url = snapshot.get("url") or snapshot.get("location")
        if url:
            # Extract battle tag from URL
            # Format: /battle-gen9vgc2025regh-123456
            match = re.search(r'/battle-([^/]+)', url)
            if match:
                return f"battle-{match.group(1)}"
        
        # Check page title
        title = snapshot.get("title") or snapshot.get("name", "")
        if title:
            match = re.search(r'battle-([^\s]+)', title)
            if match:
                return f"battle-{match.group(1)}"
        
        return None
    
    def extract_opponent_name(self, snapshot: Dict[str, Any]) -> Optional[str]:
        """
        Extract opponent name from battle UI.
        
        Returns:
            Opponent username or None
        """
        if not snapshot:
            return None
        
        text_content = self._extract_all_text(snapshot)
        
        # Look for opponent name patterns
        # Common patterns:
        # - "vs. OpponentName"
        # - "OpponentName's team"
        # - Opponent name in battle header
        
        patterns = [
            r'vs\.\s*(\w+)',
            r'vs\s+(\w+)',
            r"(\w+)'s\s+team",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        
        return None
    
    # Helper methods for searching accessibility tree
    
    def _find_elements_by_text(self, snapshot: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """
        Find elements containing specific text.
        
        Args:
            snapshot: Browser snapshot
            text: Text to search for
            
        Returns:
            List of matching elements
        """
        matches = []
        text_lower = text.lower()
        
        def search(node: Any, depth: int = 0) -> None:
            if depth > 20:
                return
            
            if not isinstance(node, dict):
                return
            
            node_text = self._extract_text_content(node).lower()
            if text_lower in node_text:
                matches.append(node)
            
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    search(child, depth + 1)
        
        search(snapshot)
        return matches
    
    def _find_elements_by_role(self, snapshot: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
        """
        Find elements by ARIA role.
        
        Args:
            snapshot: Browser snapshot
            role: ARIA role (e.g., "button", "img", "text")
            
        Returns:
            List of matching elements
        """
        matches = []
        
        def search(node: Any, depth: int = 0) -> None:
            if depth > 20:
                return
            
            if not isinstance(node, dict):
                return
            
            node_role = node.get("role", "")
            if role.lower() in node_role.lower():
                matches.append(node)
            
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    search(child, depth + 1)
        
        search(snapshot)
        return matches
    
    def _find_buttons(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all buttons in the snapshot.
        
        Returns:
            List of button elements
        """
        return self._find_elements_by_role(snapshot, "button")
    
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
    
    def _extract_all_text(self, snapshot: Dict[str, Any]) -> str:
        """
        Extract all text content from snapshot recursively.
        
        Args:
            snapshot: Browser snapshot
            
        Returns:
            All text content
        """
        return self._extract_text_content(snapshot)
    
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
    
    def _extract_pokemon_name(self, element: Dict[str, Any]) -> Optional[str]:
        """
        Extract Pokemon name from an element.
        
        Args:
            element: Element that may contain Pokemon name
            
        Returns:
            Pokemon name or None
        """
        text = self._extract_text_content(element)
        
        # Try to identify Pokemon name in text
        # Pokemon names are typically capitalized single words
        words = text.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 2:
                # Check if it's not a common UI word
                if word.lower() not in ["hp", "pp", "status", "active", "switch", "move", "button", "pokemon"]:
                    return word.lower()
        
        return None
    
    def _parse_hp(self, element: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        Parse HP from element (current/max).
        
        Args:
            element: Element containing HP information
            
        Returns:
            Tuple of (current_hp, max_hp) or None
        """
        text = self._extract_text_content(element)
        
        # Look for HP patterns: "150/150" or "75%"
        hp_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
        if hp_match:
            return (int(hp_match.group(1)), int(hp_match.group(2)))
        
        # Percentage pattern
        percent_match = re.search(r'(\d+)%', text)
        if percent_match:
            percent = int(percent_match.group(1))
            # Would need max HP to calculate current, but we can estimate
            # For now, return None
            return None
        
        return None
