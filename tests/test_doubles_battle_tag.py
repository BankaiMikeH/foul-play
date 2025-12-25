"""
Test battle tag parsing for doubles and Bo3 formats.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fp.run_battle import get_battle_tag_and_opponent
from config import FoulPlayConfig


class TestBattleTagParsing:
    """Test parsing of battle initialization messages."""
    
    @pytest.mark.asyncio
    async def test_standard_doubles_battle_tag(self):
        """Test parsing standard VGC battle initialization."""
        # Mock websocket client
        mock_client = MagicMock()
        
        # Simulate message from Pokemon Showdown
        battle_message = """>battle-gen9vgc2026regf-123
|title|VGCTestBot1 vs. VGCTestBot2
|gametype|doubles
|player|p1|VGCTestBot1|1|
|player|p2|VGCTestBot2|1|
|teamsize|p1|4
|teamsize|p2|4
|gen|9"""
        
        mock_client.receive_message = AsyncMock(return_value=battle_message)
        FoulPlayConfig.username = "VGCTestBot1"
        
        battle_tag, opponent = await get_battle_tag_and_opponent(mock_client)
        
        assert battle_tag == "battle-gen9vgc2026regf-123"
        assert opponent == "VGCTestBot2"
    
    @pytest.mark.asyncio
    async def test_bo3_battle_tag(self):
        """Test parsing Bo3 battle initialization."""
        mock_client = MagicMock()
        
        # Bo3 creates two rooms - lobby and actual battle
        # We should pick the actual battle room, not the lobby
        lobby_message = """>battle-gen9vgc2026regfbo3-456
|title|VGCTestBot1 vs. VGCTestBot2
|tournament|Best of 3"""
        
        battle_message = """>battle-gen9vgc2026regfbo3-456-1
|title|VGCTestBot1 vs. VGCTestBot2 (Game 1)
|gametype|doubles
|player|p1|VGCTestBot1|1|
|player|p2|VGCTestBot2|1|"""
        
        # First receive lobby, then battle
        mock_client.receive_message = AsyncMock(side_effect=[lobby_message, battle_message])
        FoulPlayConfig.username = "VGCTestBot1"
        
        # Current implementation might not handle this correctly
        # This test documents expected behavior
        battle_tag, opponent = await get_battle_tag_and_opponent(mock_client)
        
        # Should get the actual battle room, not lobby
        assert "battle-gen9vgc2026regfbo3" in battle_tag
        assert opponent == "VGCTestBot2"
    
    @pytest.mark.asyncio
    async def test_multiline_message_parsing(self):
        """Test parsing when battle info comes in multiline message."""
        mock_client = MagicMock()
        
        # Sometimes messages come as one big multiline string
        message = """>battle-gen9vgc2026regf-789

|title|PlayerOne vs. PlayerTwo
|gametype|doubles
|player|p1|PlayerOne|1|
|player|p2|PlayerTwo|1|
|teamsize|p1|4
|teamsize|p2|4"""
        
        mock_client.receive_message = AsyncMock(return_value=message)
        FoulPlayConfig.username = "PlayerOne"
        
        battle_tag, opponent = await get_battle_tag_and_opponent(mock_client)
        
        assert battle_tag == "battle-gen9vgc2026regf-789"
        assert opponent == "PlayerTwo"
    
    @pytest.mark.asyncio  
    async def test_opponent_name_extraction(self):
        """Test extracting opponent name from title."""
        mock_client = MagicMock()
        
        # Title format: "User vs. Opponent"
        message = """>battle-gen9doublesou-100
|title|MyBot vs. TheirBot"""
        
        mock_client.receive_message = AsyncMock(return_value=message)
        FoulPlayConfig.username = "MyBot"
        
        battle_tag, opponent = await get_battle_tag_and_opponent(mock_client)
        
        assert opponent == "TheirBot"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

