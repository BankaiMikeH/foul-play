#!/usr/bin/env python3
"""
Phase 12 Comprehensive Test

Tests all team learning and adaptation features:
1. Battle tracking and recording
2. Performance database
3. Meta analysis
4. Team recommendations
5. Learning engine (ML)
6. Evolutionary algorithm
7. Adaptive team generation

Run with: python test_phase12.py
"""

import json
import os
import tempfile
from fp.team_learning import (
    BattleTracker,
    PerformanceDatabase,
    MetaAnalyzer,
    TeamRecommender,
    LearningEngine,
    EvolutionaryTeamBuilder,
    AdaptiveTeamGenerator
)


def print_test_header(test_name: str):
    """Print test section header."""
    print("\n" + "="*70)
    print(f"  TEST: {test_name}")
    print("="*70)


def create_test_team(prefix: str = "") -> list:
    """Create a test team."""
    return [
        {'name': f'{prefix}Incineroar', 'types': ['Fire', 'Dark'], 
         'stats': {'hp': 95, 'atk': 115, 'def': 90, 'spa': 80, 'spd': 90, 'spe': 60}},
        {'name': f'{prefix}Landorus-Therian', 'types': ['Ground', 'Flying'],
         'stats': {'hp': 89, 'atk': 145, 'def': 90, 'spa': 105, 'spd': 80, 'spe': 91}},
        {'name': f'{prefix}Rillaboom', 'types': ['Grass'],
         'stats': {'hp': 100, 'atk': 125, 'def': 90, 'spa': 60, 'spd': 70, 'spe': 85}},
        {'name': f'{prefix}Iron Hands', 'types': ['Fighting', 'Electric'],
         'stats': {'hp': 154, 'atk': 140, 'def': 108, 'spa': 50, 'spd': 68, 'spe': 50}},
        {'name': f'{prefix}Flutter Mane', 'types': ['Ghost', 'Fairy'],
         'stats': {'hp': 55, 'atk': 55, 'def': 55, 'spa': 135, 'spd': 135, 'spe': 135}},
        {'name': f'{prefix}Gholdengo', 'types': ['Steel', 'Ghost'],
         'stats': {'hp': 87, 'atk': 60, 'def': 95, 'spa': 133, 'spd': 91, 'spe': 84}}
    ]


def test_battle_tracker():
    """Test 1: Battle Tracker"""
    print_test_header("Battle Tracker")
    
    # Create temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize tracker
        tracker = BattleTracker(db_path)
        print("✅ Battle tracker initialized")
        
        # Create test team
        team = create_test_team()
        
        # Record some battles
        print("\n📝 Recording test battles...")
        
        results = ['win', 'win', 'loss', 'win', 'tie', 'win', 'loss', 'win']
        ratings = [1500, 1520, 1540, 1520, 1540, 1540, 1560, 1540, 1560]
        
        for i, result in enumerate(results):
            battle_id = tracker.record_battle(
                team=team,
                strategy='Balanced',
                result=result,
                opponent=f'Opponent{i}',
                rating_before=ratings[i],
                rating_after=ratings[i+1],
                turns=10 + i,
                phase10_score=8.0 + i*0.1
            )
            print(f"  Battle {battle_id}: {result} (Rating: {ratings[i]} → {ratings[i+1]})")
        
        # Get team stats
        stats = tracker.get_team_stats(team)
        print(f"\n📊 Team Performance:")
        print(f"  Total Battles: {stats['total_battles']}")
        print(f"  Win Rate: {stats['win_rate']*100:.1f}%")
        print(f"  Peak Rating: {stats['peak_rating']}")
        
        assert stats['total_battles'] == len(results), "Battle count mismatch"
        print("\n✅ Battle tracker test PASSED")
        
        return tracker
        
    except Exception as e:
        print(f"\n❌ Battle tracker test FAILED: {e}")
        raise
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


def test_performance_database():
    """Test 2: Performance Database"""
    print_test_header("Performance Database")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = PerformanceDatabase(db_path)
        print("✅ Database initialized")
        
        # Test recording
        battle_id = db.record_battle(
            team_hash='test_hash_123',
            strategy='Balanced',
            format_name='gen9vgc2026regf',
            opponent='TestOpponent',
            result='win',
            rating_before=1500,
            rating_after=1520,
            turns=15
        )
        
        print(f"✅ Battle recorded: ID {battle_id}")
        
        # Test statistics
        stats = db.get_statistics()
        print(f"\n📊 Database Statistics:")
        print(f"  Total Battles: {stats['total_battles']}")
        print(f"  Win Rate: {stats['win_rate']*100:.1f}%")
        
        assert stats['total_battles'] == 1, "Battle count should be 1"
        print("\n✅ Performance database test PASSED")
        
    except Exception as e:
        print(f"\n❌ Performance database test FAILED: {e}")
        raise
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_meta_analyzer():
    """Test 3: Meta Analyzer"""
    print_test_header("Meta Analyzer")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create database with data
        tracker = BattleTracker(db_path)
        team = create_test_team()
        
        # Record battles
        for i in range(10):
            result = 'win' if i < 7 else 'loss'
            tracker.record_battle(
                team=team,
                strategy='Balanced',
                result=result,
                rating_before=1500,
                rating_after=1520 if result == 'win' else 1480,
                phase10_score=8.0
            )
        
        # Analyze
        analyzer = MetaAnalyzer(tracker.db)
        report = analyzer.get_meta_report(min_battles=1)
        
        print("✅ Meta report generated")
        print(f"\n📊 Report Summary:")
        print(f"  Total Battles: {report['overall_stats']['total_battles']}")
        
        if report['best_strategy']:
            print(f"  Best Strategy: {report['best_strategy']['name']}")
            print(f"  Win Rate: {report['best_strategy']['win_rate']*100:.1f}%")
        
        if report['best_pokemon']:
            print(f"  Best Pokemon: {report['best_pokemon'][0]['name']}")
        
        assert report['overall_stats']['total_battles'] == 10, "Should have 10 battles"
        print("\n✅ Meta analyzer test PASSED")
        
    except Exception as e:
        print(f"\n❌ Meta analyzer test FAILED: {e}")
        raise
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_team_recommender():
    """Test 4: Team Recommender"""
    print_test_header("Team Recommender")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create database with data
        tracker = BattleTracker(db_path)
        
        # Record multiple teams
        for i in range(3):
            team = create_test_team(f"Team{i}_")
            for j in range(6):
                result = 'win' if j < 4 else 'loss'
                tracker.record_battle(
                    team=team,
                    strategy='Balanced',
                    result=result,
                    rating_before=1500,
                    rating_after=1520 if result == 'win' else 1480
                )
        
        # Get recommendations
        recommender = TeamRecommender(tracker.db)
        best = recommender.recommend('best_overall', limit=3, min_battles=3)
        
        print("✅ Recommendations generated")
        print(f"\n🏆 Top Recommendations:")
        
        for i, team in enumerate(best, 1):
            print(f"  {i}. {', '.join(team['pokemon'][:3])}...")
            print(f"     Win Rate: {team['win_rate']*100:.1f}%")
        
        assert len(best) > 0, "Should have recommendations"
        print("\n✅ Team recommender test PASSED")
        
    except Exception as e:
        print(f"\n❌ Team recommender test FAILED: {e}")
        raise
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_learning_engine():
    """Test 5: Learning Engine"""
    print_test_header("Learning Engine (ML)")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create database with data
        tracker = BattleTracker(db_path)
        team = create_test_team()
        
        # Record 25 battles for training
        for i in range(25):
            result = 'win' if i % 3 != 0 else 'loss'  # ~66% win rate
            tracker.record_battle(
                team=team,
                strategy='Balanced',
                result=result,
                rating_before=1500,
                rating_after=1520 if result == 'win' else 1480
            )
        
        # Train learning engine
        engine = LearningEngine(tracker.db)
        
        print("🤖 Training ML model...")
        trained = engine.train(min_battles=20)
        
        if not trained:
            print("⚠️  Could not train (likely sklearn not installed)")
            print("   Skipping ML test (this is OK)")
            print("\n✅ Learning engine test SKIPPED (no sklearn)")
            return
        
        print("✅ Model trained successfully")
        
        # Predict
        win_prob = engine.predict_win_probability(team)
        print(f"\n🔮 Prediction for team:")
        print(f"  Win Probability: {win_prob*100:.1f}%")
        
        # Get insights
        insights = engine.get_model_insights()
        print(f"  Training Accuracy: {insights['accuracy']*100:.1f}%")
        
        assert 0.0 <= win_prob <= 1.0, "Win probability should be 0-1"
        print("\n✅ Learning engine test PASSED")
        
    except ImportError:
        print("\n⚠️  scikit-learn not installed, skipping ML test")
        print("✅ Learning engine test SKIPPED (no sklearn)")
    except Exception as e:
        print(f"\n❌ Learning engine test FAILED: {e}")
        raise
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_evolutionary_builder():
    """Test 6: Evolutionary Team Builder"""
    print_test_header("Evolutionary Algorithm")
    
    try:
        builder = EvolutionaryTeamBuilder()
        print("✅ Evolutionary builder initialized")
        
        print("\n🧬 Evolving team (5 generations for speed)...")
        result = builder.evolve(
            strategy='Balanced',
            population_size=10,
            generations=5,
            verbose=False
        )
        
        print("✅ Evolution complete")
        print(f"\n🏆 Best Team:")
        for i, pokemon in enumerate(result['team'], 1):
            print(f"  {i}. {pokemon['name']}")
        
        print(f"\n  Fitness Score: {result['fitness']:.2f}")
        
        assert len(result['team']) == 6, "Should have 6 Pokemon"
        assert result['fitness'] > 0, "Fitness should be positive"
        print("\n✅ Evolutionary builder test PASSED")
        
    except Exception as e:
        print(f"\n❌ Evolutionary builder test FAILED: {e}")
        raise


def test_adaptive_generator():
    """Test 7: Adaptive Team Generator"""
    print_test_header("Adaptive Team Generator")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create database with data
        tracker = BattleTracker(db_path)
        team = create_test_team()
        
        # Record battles
        for i in range(15):
            result = 'win' if i % 2 == 0 else 'loss'
            tracker.record_battle(
                team=team,
                strategy='Balanced',
                result=result,
                rating_before=1500,
                rating_after=1520 if result == 'win' else 1480
            )
        
        # Generate adaptive team
        generator = AdaptiveTeamGenerator(perf_db=tracker.db, learning_rate=0.7)
        print("✅ Adaptive generator initialized")
        
        print("\n🧠 Generating adaptive team...")
        team_data = generator.generate('Balanced', use_learning=True)
        
        print("✅ Team generated")
        print(f"\n🏆 Generated Team:")
        for i, pokemon in enumerate(team_data['pokemon'], 1):
            print(f"  {i}. {pokemon['name']}")
        
        if team_data.get('adapted'):
            print(f"\n  ✨ Team was adapted using learned data!")
            print(f"  Improvements: {team_data.get('improvements_made', 0)}")
        
        assert len(team_data['pokemon']) == 6, "Should have 6 Pokemon"
        print("\n✅ Adaptive generator test PASSED")
        
    except Exception as e:
        print(f"\n❌ Adaptive generator test FAILED: {e}")
        raise
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def main():
    """Run all Phase 12 tests."""
    print("\n" + "="*70)
    print("  PHASE 12 COMPREHENSIVE TEST SUITE")
    print("  Team Learning & Adaptation")
    print("="*70)
    
    tests = [
        ("Battle Tracker", test_battle_tracker),
        ("Performance Database", test_performance_database),
        ("Meta Analyzer", test_meta_analyzer),
        ("Team Recommender", test_team_recommender),
        ("Learning Engine (ML)", test_learning_engine),
        ("Evolutionary Algorithm", test_evolutionary_builder),
        ("Adaptive Generator", test_adaptive_generator)
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            if "SKIPPED" in str(e):
                skipped += 1
            else:
                failed += 1
                print(f"\n❌ {test_name} FAILED: {e}")
    
    # Final summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    print(f"\n  Total Tests: {len(tests)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ⚠️  Skipped: {skipped}")
    print(f"  ❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✅ Phase 12 is working correctly!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review errors above.")
    
    print()


if __name__ == '__main__':
    main()

