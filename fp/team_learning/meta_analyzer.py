"""
Meta Analyzer

Analyzes trends and patterns in battle data to identify what's working
in the current metagame.

Phase 12 - Team Learning & Adaptation
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from .performance_db import PerformanceDatabase


class MetaAnalyzer:
    """Analyzes metagame trends from battle data."""
    
    def __init__(self, db: Optional[PerformanceDatabase] = None):
        """
        Initialize meta analyzer.
        
        Args:
            db: Performance database, or None to create new one
        """
        self.db = db if db else PerformanceDatabase()
    
    def get_meta_report(self, min_battles: int = 5, days: int = 7) -> Dict:
        """
        Generate a comprehensive meta report.
        
        Args:
            min_battles: Minimum battles for inclusion
            days: Days to analyze (0 for all time)
        
        Returns:
            Meta report dictionary
        """
        report = {
            'overall_stats': self.db.get_statistics(),
            'best_strategy': self.get_best_strategy(),
            'best_pokemon': self.get_best_pokemon(min_battles=min_battles),
            'worst_pokemon': self.get_worst_pokemon(min_battles=min_battles),
            'top_teams': self.get_top_teams(min_battles=min_battles),
            'strategy_breakdown': self.get_strategy_breakdown(),
            'pokemon_usage': self.get_pokemon_usage(),
            'recent_performance': self.get_recent_performance(days=days)
        }
        
        return report
    
    def get_best_strategy(self) -> Optional[Dict]:
        """Get the best performing strategy."""
        strategies = self.db.get_top_strategies()
        
        if strategies:
            best = strategies[0]
            return {
                'name': best['strategy'],
                'win_rate': best['win_rate'],
                'total_battles': best['total_battles'],
                'wins': best['wins'],
                'losses': best['losses']
            }
        return None
    
    def get_best_pokemon(self, min_battles: int = 10, limit: int = 10) -> List[Dict]:
        """Get top performing Pokemon."""
        pokemon = self.db.get_top_pokemon(limit=limit, min_battles=min_battles)
        
        return [{
            'name': p['pokemon_name'],
            'win_rate': p['win_rate'],
            'total_battles': p['total_battles'],
            'survival_rate': p['survival_rate']
        } for p in pokemon]
    
    def get_worst_pokemon(self, min_battles: int = 10, limit: int = 10) -> List[Dict]:
        """Get worst performing Pokemon."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM pokemon_performance
            WHERE total_battles >= ?
            ORDER BY win_rate ASC, total_battles DESC
            LIMIT ?
        """, (min_battles, limit))
        
        pokemon = [dict(row) for row in cursor.fetchall()]
        
        return [{
            'name': p['pokemon_name'],
            'win_rate': p['win_rate'],
            'total_battles': p['total_battles'],
            'survival_rate': p['survival_rate']
        } for p in pokemon]
    
    def get_top_teams(self, min_battles: int = 5, limit: int = 5) -> List[Dict]:
        """Get top performing teams."""
        teams = self.db.get_top_teams(limit=limit, min_battles=min_battles)
        
        result = []
        for team in teams:
            import json
            team_data = json.loads(team['team_json'])
            team_names = [p['name'] for p in team_data]
            
            result.append({
                'pokemon': team_names,
                'strategy': team['strategy'],
                'win_rate': team['win_rate'],
                'total_battles': team['total_battles'],
                'peak_rating': team['peak_rating'],
                'phase10_score': team.get('phase10_score', 0.0)
            })
        
        return result
    
    def get_strategy_breakdown(self) -> List[Dict]:
        """Get breakdown of all strategies."""
        strategies = self.db.get_top_strategies()
        
        return [{
            'strategy': s['strategy'],
            'win_rate': s['win_rate'],
            'total_battles': s['total_battles'],
            'avg_rating': s['avg_rating']
        } for s in strategies]
    
    def get_pokemon_usage(self) -> List[Dict]:
        """Get Pokemon usage statistics."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT 
                pokemon_name,
                total_battles,
                win_rate,
                survival_rate
            FROM pokemon_performance
            ORDER BY total_battles DESC
            LIMIT 20
        """)
        
        return [{
            'name': row['pokemon_name'],
            'usage': row['total_battles'],
            'win_rate': row['win_rate'],
            'survival_rate': row['survival_rate']
        } for row in cursor.fetchall()]
    
    def get_recent_performance(self, days: int = 7) -> Dict:
        """Get performance in recent time period."""
        cursor = self.db.conn.cursor()
        
        # Calculate cutoff date
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get recent battles
        cursor.execute("""
            SELECT result, COUNT(*) as count
            FROM battles
            WHERE timestamp >= ?
            GROUP BY result
        """, (cutoff,))
        
        results = {row['result']: row['count'] for row in cursor.fetchall()}
        total = sum(results.values())
        
        if total == 0:
            return {
                'days': days,
                'total_battles': 0,
                'win_rate': 0.0
            }
        
        # Get average rating
        cursor.execute("""
            SELECT AVG(rating_after) as avg_rating
            FROM battles
            WHERE timestamp >= ?
        """, (cutoff,))
        
        avg_rating = cursor.fetchone()['avg_rating'] or 1500
        
        return {
            'days': days,
            'total_battles': total,
            'wins': results.get('win', 0),
            'losses': results.get('loss', 0),
            'ties': results.get('tie', 0),
            'win_rate': results.get('win', 0) / total,
            'avg_rating': int(avg_rating)
        }
    
    def detect_meta_shift(self, window_days: int = 7) -> Dict:
        """
        Detect if meta has shifted recently.
        
        Args:
            window_days: Size of time windows to compare
        
        Returns:
            Meta shift analysis
        """
        # Get recent performance
        recent = self.get_recent_performance(days=window_days)
        
        # Get older performance (previous window)
        cutoff_recent = (datetime.now() - timedelta(days=window_days)).isoformat()
        cutoff_old = (datetime.now() - timedelta(days=window_days*2)).isoformat()
        
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT result, COUNT(*) as count
            FROM battles
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY result
        """, (cutoff_old, cutoff_recent))
        
        old_results = {row['result']: row['count'] for row in cursor.fetchall()}
        old_total = sum(old_results.values())
        
        if old_total == 0:
            return {
                'shift_detected': False,
                'reason': 'Insufficient historical data'
            }
        
        old_winrate = old_results.get('win', 0) / old_total
        recent_winrate = recent['win_rate']
        
        # Detect significant shift (>10% change)
        shift = abs(recent_winrate - old_winrate)
        shift_detected = shift > 0.1
        
        return {
            'shift_detected': shift_detected,
            'recent_winrate': recent_winrate,
            'old_winrate': old_winrate,
            'change': recent_winrate - old_winrate,
            'trend': 'improving' if recent_winrate > old_winrate else 'declining'
        }
    
    def get_pokemon_synergies(self, min_battles: int = 3) -> List[Dict]:
        """
        Identify Pokemon pairs that work well together.
        
        Args:
            min_battles: Minimum battles for pair
        
        Returns:
            List of synergistic pairs
        """
        cursor = self.db.conn.cursor()
        
        # Get all teams with their results
        cursor.execute("""
            SELECT tp.team_json, tp.win_rate, tp.total_battles
            FROM team_performance tp
            WHERE tp.total_battles >= ?
            ORDER BY tp.win_rate DESC
        """, (min_battles,))
        
        teams = [dict(row) for row in cursor.fetchall()]
        
        # Count pair frequencies and win rates
        pair_stats = {}
        
        import json
        from itertools import combinations
        
        for team in teams:
            team_data = json.loads(team['team_json'])
            pokemon_names = [p['name'] for p in team_data]
            
            # Get all pairs
            for pair in combinations(sorted(pokemon_names), 2):
                pair_key = f"{pair[0]}+{pair[1]}"
                
                if pair_key not in pair_stats:
                    pair_stats[pair_key] = {
                        'battles': 0,
                        'total_winrate': 0.0
                    }
                
                pair_stats[pair_key]['battles'] += team['total_battles']
                pair_stats[pair_key]['total_winrate'] += team['win_rate'] * team['total_battles']
        
        # Calculate average win rates for pairs
        synergies = []
        for pair_key, stats in pair_stats.items():
            if stats['battles'] >= min_battles:
                avg_winrate = stats['total_winrate'] / stats['battles']
                pokemon = pair_key.split('+')
                
                synergies.append({
                    'pokemon_1': pokemon[0],
                    'pokemon_2': pokemon[1],
                    'avg_winrate': avg_winrate,
                    'battles': stats['battles']
                })
        
        # Sort by win rate
        synergies.sort(key=lambda x: -x['avg_winrate'])
        
        return synergies[:20]  # Top 20 pairs


# Example usage
if __name__ == '__main__':
    analyzer = MetaAnalyzer()
    
    print("Meta Analysis Example")
    print("=" * 60)
    
    # Generate meta report
    report = analyzer.get_meta_report(min_battles=1)
    
    print("\n📊 Overall Statistics:")
    stats = report['overall_stats']
    print(f"  Total Battles: {stats['total_battles']}")
    print(f"  Win Rate: {stats['win_rate']*100:.1f}%")
    print(f"  Average Rating: {stats['avg_rating']}")
    
    if report['best_strategy']:
        print(f"\n🎯 Best Strategy: {report['best_strategy']['name']}")
        print(f"  Win Rate: {report['best_strategy']['win_rate']*100:.1f}%")
        print(f"  Battles: {report['best_strategy']['total_battles']}")
    
    if report['best_pokemon']:
        print(f"\n⭐ Top Pokemon:")
        for i, pkmn in enumerate(report['best_pokemon'][:5], 1):
            print(f"  {i}. {pkmn['name']}: {pkmn['win_rate']*100:.1f}% WR ({pkmn['total_battles']} battles)")
    
    if report['top_teams']:
        print(f"\n🏆 Top Teams:")
        for i, team in enumerate(report['top_teams'][:3], 1):
            print(f"  {i}. {', '.join(team['pokemon'][:3])}...")
            print(f"     Win Rate: {team['win_rate']*100:.1f}% ({team['total_battles']} battles)")

