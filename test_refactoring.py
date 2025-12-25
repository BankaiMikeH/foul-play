"""
Quick test of the new refactored battle architecture
"""
import sys
import traceback

try:
    from fp.battle import create_battle, Pokemon, Battler
    from fp.battle_types import SinglesBattle, DoublesBattle
    
    print("✓ Imports successful!")
    
    # Test 1: Factory creates correct types
    singles = create_battle('test1', pokemon_format='gen9ou')
    doubles = create_battle('test2', pokemon_format='gen9vgc2026regf')
    
    print(f"✓ Factory created singles: {type(singles).__name__}")
    print(f"✓ Factory created doubles: {type(doubles).__name__}")
    
    assert isinstance(singles, SinglesBattle), f'Failed: singles is {type(singles)}, not SinglesBattler'
    assert isinstance(doubles, DoublesBattle), f'Failed: doubles is {type(doubles)}, not DoublesBattle'
    
    print("✓ Type assertions passed!")
    
    # Test 2: is_doubles property works
    assert not singles.is_doubles, 'Failed: singles.is_doubles should be False'
    assert doubles.is_doubles, 'Failed: doubles.is_doubles should be True'
    
    print("✓ is_doubles property works!")
    
    # Test 3: Battlers are correct types
    from fp.battler_singles import SinglesBattler as SB
    from fp.battler_doubles import DoublesBattler as DB
    
    assert isinstance(singles.user, SB), f'Failed: singles.user is {type(singles.user)}'
    assert isinstance(doubles.user, DB), f'Failed: doubles.user is {type(doubles.user)}'
    
    print("✓ Battler types correct!")
    
    # Test 4: Active structure is correct
    assert singles.user.active is None, 'Failed: singles.user.active should start as None'
    assert doubles.user.active == [None, None], f'Failed: doubles.user.active should be [None, None], got {doubles.user.active}'
    
    print("✓ Active structure correct!")
    
    # Test 5: Polymorphic methods work
    singles.user.set_active_pokemon(Pokemon("pikachu", 50), 0)
    doubles.user.set_active_pokemon(Pokemon("raichu", 50), 0)
    doubles.user.set_active_pokemon(Pokemon("charizard", 50), 1)
    
    assert singles.user.get_active_count() == 1
    assert doubles.user.get_active_count() == 2
    
    print("✓ Polymorphic methods work!")
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED! ✓✓✓")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

