#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test script for Team Manager Phase 7

Run this to verify the team management system is working correctly.
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")

from team_manager import TeamManager
from team_integration import BattleTeamManager, TeamSelectionStrategy


def test_basic_loading():
    """Test basic team loading"""
    print("=" * 60)
    print("Test 1: Basic Team Loading")
    print("=" * 60)
    
    manager = TeamManager()
    
    # Load VGC 2024 teams
    count = manager.load_teams("gen9vgc2024")
    print(f"[OK] Loaded {count} VGC 2024 teams")
    
    if count < 5:
        print(f"  WARNING: Expected at least 5 teams, got {count}")
        return False
    
    return True


def test_team_selection():
    """Test different team selection strategies"""
    print("\n" + "=" * 60)
    print("Test 2: Team Selection Strategies")
    print("=" * 60)
    
    manager = TeamManager()
    manager.load_teams("gen9vgc2024")
    
    # Test each strategy
    strategies = {
        "Best": manager.get_best_team(),
        "Random": manager.get_random_team(),
        "Rotation": manager.get_next_rotation_team(),
        "Least Used": manager.get_least_used_team(),
    }
    
    for strategy_name, team in strategies.items():
        if team is None:
            print(f"  [FAIL] {strategy_name} strategy failed")
            return False
        print(f"  [OK] {strategy_name}: {team.name}")
    
    return True


def test_team_conversion():
    """Test team format conversion"""
    print("\n" + "=" * 60)
    print("Test 3: Team Format Conversion")
    print("=" * 60)
    
    manager = TeamManager()
    manager.load_teams("gen9vgc2024")
    team = manager.get_team_by_id("miraidon_balance_1")
    
    if team is None:
        print("  [FAIL] Could not load miraidon_balance_1 team")
        return False
    
    # Test Showdown format
    showdown = team.to_showdown_format()
    if not showdown or len(showdown) < 100:
        print("  [FAIL] Showdown format conversion failed")
        return False
    print(f"  [OK] Showdown format: {len(showdown)} characters")
    
    # Test packed format
    try:
        packed = team.to_packed_format()
        print(f"  [OK] Packed format: {len(packed)} characters")
    except Exception as e:
        print(f"  [FAIL] Packed format conversion failed: {e}")
        return False
    
    return True


def test_performance_tracking():
    """Test performance tracking"""
    print("\n" + "=" * 60)
    print("Test 4: Performance Tracking")
    print("=" * 60)
    
    manager = TeamManager()
    manager.load_teams("gen9vgc2024")
    
    team = manager.get_best_team()
    team_id = team.id
    
    # Record some battles
    manager.record_battle_result(team_id, won=True)
    manager.record_battle_result(team_id, won=True)
    manager.record_battle_result(team_id, won=False)
    
    # Get stats
    stats = manager.get_team_stats(team_id)
    if stats is None:
        print("  [FAIL] Could not retrieve stats")
        return False
    
    print(f"  [OK] Battles: {stats.battles_played}")
    print(f"  [OK] Record: {stats.wins}W-{stats.losses}L")
    print(f"  [OK] Winrate: {stats.winrate:.1%}")
    
    if stats.battles_played != 3 or stats.wins != 2 or stats.losses != 1:
        print("  [FAIL] Stats incorrect")
        return False
    
    return True


def test_battle_integration():
    """Test BattleTeamManager integration"""
    print("\n" + "=" * 60)
    print("Test 5: Battle Integration")
    print("=" * 60)
    
    try:
        battle_mgr = BattleTeamManager(
            format_name="gen9vgc2024",
            strategy=TeamSelectionStrategy.ROTATION
        )
        print(f"  [OK] BattleTeamManager created")
        
        # Select a team
        packed, team_dict, team_name = battle_mgr.select_team()
        print(f"  [OK] Team selected: {team_name}")
        
        # Record result
        battle_mgr.record_battle_result("TestBot", "TestBot")
        print(f"  [OK] Result recorded")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Battle integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_doubles_ou():
    """Test Doubles OU format"""
    print("\n" + "=" * 60)
    print("Test 6: Doubles OU Format")
    print("=" * 60)
    
    manager = TeamManager()
    count = manager.load_teams("gen9doublesou")
    print(f"  [OK] Loaded {count} Doubles OU teams")
    
    if count < 3:
        print(f"  WARNING: Expected at least 3 teams, got {count}")
        return False
    
    team = manager.get_random_team()
    print(f"  [OK] Selected team: {team.name}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TEAM MANAGER PHASE 7 TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Basic Loading", test_basic_loading),
        ("Team Selection", test_team_selection),
        ("Format Conversion", test_team_conversion),
        ("Performance Tracking", test_performance_tracking),
        ("Battle Integration", test_battle_integration),
        ("Doubles OU", test_doubles_ou),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[FAIL] {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {test_name}")
    
    print("-" * 60)
    print(f"  Result: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    if passed == total:
        print("SUCCESS: ALL TESTS PASSED! Phase 7 is working correctly!\n")
        return 0
    else:
        print(f"WARNING: {total - passed} test(s) failed. Please review above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

