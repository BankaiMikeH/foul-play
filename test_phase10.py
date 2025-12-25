"""
Phase 10 Integration Test

Tests all team analysis components to ensure they work correctly.
"""

import sys
import traceback


def test_type_coverage():
    """Test type coverage analyzer."""
    print("Testing Type Coverage Analyzer...")
    try:
        from fp.team_analysis.type_coverage import TypeCoverageAnalyzer
        
        team = [
            {
                'name': 'Flutter Mane',
                'types': ['Ghost', 'Fairy'],
                'moves': [
                    {'name': 'Moonblast', 'type': 'Fairy'},
                    {'name': 'Shadow Ball', 'type': 'Ghost'}
                ]
            }
        ]
        
        analyzer = TypeCoverageAnalyzer()
        result = analyzer.analyze_team(team)
        
        assert 'offensive' in result
        assert 'defensive' in result
        assert 'score' in result
        
        print("  ✅ Type Coverage Analyzer: PASSED")
        return True
    except Exception as e:
        print(f"  ❌ Type Coverage Analyzer: FAILED - {e}")
        traceback.print_exc()
        return False


def test_speed_analyzer():
    """Test speed tier analyzer."""
    print("Testing Speed Tier Analyzer...")
    try:
        from fp.team_analysis.speed_analysis import SpeedTierAnalyzer
        
        team = [
            {
                'name': 'Flutter Mane',
                'stats': {'spe': 205},
                'item': 'Booster Energy',
                'ability': 'Protosynthesis',
                'moves': [{'name': 'Protect'}]
            }
        ]
        
        analyzer = SpeedTierAnalyzer()
        result = analyzer.analyze_team_speeds(team)
        
        assert 'team_speeds' in result
        assert 'speed_control' in result
        
        print("  ✅ Speed Tier Analyzer: PASSED")
        return True
    except Exception as e:
        print(f"  ❌ Speed Tier Analyzer: FAILED - {e}")
        traceback.print_exc()
        return False


def test_role_identifier():
    """Test role identification system."""
    print("Testing Role Identifier...")
    try:
        from fp.team_analysis.role_system import RoleIdentifier
        
        team = [
            {
                'name': 'Incineroar',
                'stats': {'hp': 202, 'atk': 136, 'def': 110, 'spa': 76, 'spd': 156, 'spe': 80},
                'ability': 'Intimidate',
                'item': 'Sitrus Berry',
                'moves': [
                    {'name': 'Fake Out'},
                    {'name': 'Knock Off'}
                ]
            }
        ]
        
        identifier = RoleIdentifier()
        result = identifier.analyze_team_roles(team)
        
        assert 'pokemon_roles' in result
        assert 'role_distribution' in result
        
        print("  ✅ Role Identifier: PASSED")
        return True
    except Exception as e:
        print(f"  ❌ Role Identifier: FAILED - {e}")
        traceback.print_exc()
        return False


def test_synergy_scorer():
    """Test synergy scorer."""
    print("Testing Synergy Scorer...")
    try:
        from fp.team_analysis.synergy_scorer import SynergyScorer
        
        team = [
            {
                'name': 'Rillaboom',
                'types': ['Grass'],
                'stats': {'spe': 105, 'atk': 194},
                'ability': 'Grassy Surge',
                'moves': [{'name': 'Grassy Glide', 'type': 'Grass'}]
            },
            {
                'name': 'Iron Hands',
                'types': ['Fighting', 'Electric'],
                'stats': {'spe': 70, 'atk': 211},
                'ability': 'Quark Drive',
                'moves': [{'name': 'Fake Out', 'type': 'Normal'}]
            }
        ]
        
        scorer = SynergyScorer()
        result = scorer.analyze_team_synergy(team)
        
        assert 'pair_synergies' in result
        assert 'team_score' in result
        
        print("  ✅ Synergy Scorer: PASSED")
        return True
    except Exception as e:
        print(f"  ❌ Synergy Scorer: FAILED - {e}")
        traceback.print_exc()
        return False


def test_team_analyzer():
    """Test main team analyzer."""
    print("Testing Team Analyzer...")
    try:
        from fp.team_analysis import TeamAnalyzer
        
        team = [
            {
                'name': 'Flutter Mane',
                'types': ['Ghost', 'Fairy'],
                'stats': {'hp': 131, 'atk': 54, 'def': 75, 'spa': 187, 'spd': 155, 'spe': 205},
                'ability': 'Protosynthesis',
                'item': 'Booster Energy',
                'moves': [
                    {'name': 'Moonblast', 'type': 'Fairy'},
                    {'name': 'Shadow Ball', 'type': 'Ghost'}
                ]
            },
            {
                'name': 'Incineroar',
                'types': ['Fire', 'Dark'],
                'stats': {'hp': 202, 'atk': 136, 'def': 110, 'spa': 76, 'spd': 156, 'spe': 80},
                'ability': 'Intimidate',
                'item': 'Sitrus Berry',
                'moves': [
                    {'name': 'Fake Out', 'type': 'Normal'},
                    {'name': 'Knock Off', 'type': 'Dark'}
                ]
            }
        ]
        
        analyzer = TeamAnalyzer()
        result = analyzer.analyze_team(team)
        
        assert 'type_coverage' in result
        assert 'speed_tiers' in result
        assert 'roles' in result
        assert 'synergy' in result
        assert 'overall_score' in result
        
        # Test report generation
        report = analyzer.generate_report(team, detailed=False)
        assert len(report) > 0
        
        print("  ✅ Team Analyzer: PASSED")
        return True
    except Exception as e:
        print(f"  ❌ Team Analyzer: FAILED - {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("   PHASE 10: TEAM SYNERGY ENGINE - INTEGRATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_type_coverage,
        test_speed_analyzer,
        test_role_identifier,
        test_synergy_scorer,
        test_team_analyzer
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 60)
    print("   TEST RESULTS")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED! Phase 10 is working correctly!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

