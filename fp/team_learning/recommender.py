"""
Team Recommender

Recommends teams based on learned performance data.
Helps users find teams that have been successful.

Phase 12 - Team Learning & Adaptation
"""

import json
from typing import Dict, List, Optional
from .performance_db import PerformanceDatabase
from .meta_analyzer import MetaAnalyzer


class TeamRecommender:
    """Recommends teams based on performance data."""
    
    def __init__(self, db: Optional[PerformanceDatabase] = None):
        """
        Initialize team recommender.
        
        Args:
            db: Performance database, or None to create new one
        """
        self.db = db if db else PerformanceDatabase()
        self.analyzer = MetaAnalyzer(self.db)
    
    def recommend(self, criteria: str = "best_overall",
                 strategy: Optional[str] = None,
                 rating_range: Optional[tuple] = None,
                 limit: int = 5,
                 min_battles: int = 5) -> List[Dict]:
        """
        Recommend teams based on criteria.
        
        Args:
            criteria: Recommendation type ('best_overall', 'best_for_strategy',
                     'trending', 'rating_appropriate', 'underrated')
            strategy: Filter by strategy (optional)
            rating_range: Rating range tuple (min, max)
            limit: Number of teams to return
            min_battles: Minimum battles for consideration
        
        Returns:
            List of recommended teams
        """
        if criteria == "best_overall":
            return self._recommend_best_overall(limit, min_battles, strategy)
        
        elif criteria == "best_for_strategy":
            if not strategy:
                # Return best for each strategy
                return self._recommend_best_per_strategy(limit, min_battles)
            else:
                # Return best for specific strategy
                return self._recommend_for_strategy(strategy, limit, min_battles)
        
        elif criteria == "trending":
            return self._recommend_trending(limit, min_battles, days=7)
        
        elif criteria == "rating_appropriate":
            if not rating_range:
                rating_range = (1400, 1600)  # Default
            return self._recommend_for_rating(rating_range, limit, min_battles)
        
        elif criteria == "underrated":
            return self._recommend_underrated(limit, min_battles)
        
        else:
            raise ValueError(f"Unknown criteria: {criteria}")
    
    def _recommend_best_overall(self, limit: int, min_battles: int,
                                strategy: Optional[str] = None) -> List[Dict]:
        """Recommend teams with highest overall win rate."""
        cursor = self.db.conn.cursor()
        
        if strategy:
            cursor.execute("""
                SELECT * FROM team_performance
                WHERE total_battles >= ? AND strategy = ?
                ORDER BY win_rate DESC, total_battles DESC
                LIMIT ?
            """, (min_battles, strategy, limit))
        else:
            cursor.execute("""
                SELECT * FROM team_performance
                WHERE total_battles >= ?
                ORDER BY win_rate DESC, total_battles DESC
                LIMIT ?
            """, (min_battles, limit))
        
        teams = [dict(row) for row in cursor.fetchall()]
        
        return [self._format_team(team) for team in teams]
    
    def _recommend_for_strategy(self, strategy: str, limit: int,
                                min_battles: int) -> List[Dict]:
        """Recommend best teams for a specific strategy."""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM team_performance
            WHERE total_battles >= ? AND strategy = ?
            ORDER BY win_rate DESC, total_battles DESC
            LIMIT ?
        """, (min_battles, strategy, limit))
        
        teams = [dict(row) for row in cursor.fetchall()]
        
        return [self._format_team(team) for team in teams]
    
    def _recommend_best_per_strategy(self, limit: int,
                                     min_battles: int) -> Dict[str, List[Dict]]:
        """Recommend best teams for each strategy."""
        # Get all strategies
        strategies = self.db.get_top_strategies()
        
        result = {}
        for strat in strategies:
            strategy_name = strat['strategy']
            teams = self._recommend_for_strategy(strategy_name, limit, min_battles)
            if teams:
                result[strategy_name] = teams
        
        return result
    
    def _recommend_trending(self, limit: int, min_battles: int,
                           days: int = 7) -> List[Dict]:
        """Recommend teams that have been winning recently."""
        from datetime import datetime, timedelta
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = self.db.conn.cursor()
        
        # Get teams with recent battles
        cursor.execute("""
            SELECT 
                b.team_hash,
                COUNT(*) as recent_battles,
                SUM(CASE WHEN b.result = 'win' THEN 1 ELSE 0 END) as recent_wins,
                tp.team_json,
                tp.strategy,
                tp.phase10_score
            FROM battles b
            JOIN team_performance tp ON b.team_hash = tp.team_hash
            WHERE b.timestamp >= ?
            GROUP BY b.team_hash
            HAVING recent_battles >= ?
            ORDER BY (CAST(recent_wins AS REAL) / recent_battles) DESC,
                     recent_battles DESC
            LIMIT ?
        """, (cutoff, min_battles, limit))
        
        teams = []
        for row in cursor.fetchall():
            team_data = json.loads(row['team_json'])
            recent_winrate = row['recent_wins'] / row['recent_battles']
            
            teams.append({
                'pokemon': [p['name'] for p in team_data],
                'team_data': team_data,
                'strategy': row['strategy'],
                'recent_battles': row['recent_battles'],
                'recent_wins': row['recent_wins'],
                'recent_winrate': recent_winrate,
                'phase10_score': row['phase10_score'],
                'reason': f"Hot streak: {recent_winrate*100:.0f}% WR in last {days} days"
            })
        
        return teams
    
    def _recommend_for_rating(self, rating_range: tuple, limit: int,
                             min_battles: int) -> List[Dict]:
        """Recommend teams appropriate for rating range."""
        cursor = self.db.conn.cursor()
        
        min_rating, max_rating = rating_range
        
        cursor.execute("""
            SELECT * FROM team_performance
            WHERE total_battles >= ?
                AND avg_rating >= ?
                AND avg_rating <= ?
            ORDER BY win_rate DESC, total_battles DESC
            LIMIT ?
        """, (min_battles, min_rating, max_rating, limit))
        
        teams = [dict(row) for row in cursor.fetchall()]
        
        result = []
        for team in teams:
            formatted = self._format_team(team)
            formatted['reason'] = f"Proven at {team['avg_rating']} rating"
            result.append(formatted)
        
        return result
    
    def _recommend_underrated(self, limit: int, min_battles: int) -> List[Dict]:
        """Recommend good teams with low usage."""
        cursor = self.db.conn.cursor()
        
        # Get teams with high win rate but relatively few battles
        cursor.execute("""
            SELECT * FROM team_performance
            WHERE total_battles >= ?
                AND win_rate >= 0.55
            ORDER BY win_rate DESC, total_battles ASC
            LIMIT ?
        """, (min_battles, limit))
        
        teams = [dict(row) for row in cursor.fetchall()]
        
        result = []
        for team in teams:
            formatted = self._format_team(team)
            formatted['reason'] = f"Hidden gem: {team['win_rate']*100:.0f}% WR with only {team['total_battles']} battles"
            result.append(formatted)
        
        return result
    
    def _format_team(self, team_row: Dict) -> Dict:
        """Format team row for output."""
        team_data = json.loads(team_row['team_json'])
        
        return {
            'pokemon': [p['name'] for p in team_data],
            'team_data': team_data,
            'strategy': team_row['strategy'],
            'win_rate': team_row['win_rate'],
            'total_battles': team_row['total_battles'],
            'wins': team_row['wins'],
            'losses': team_row['losses'],
            'peak_rating': team_row['peak_rating'],
            'avg_rating': team_row['avg_rating'],
            'phase10_score': team_row.get('phase10_score', 0.0),
            'reason': f"{team_row['win_rate']*100:.0f}% win rate over {team_row['total_battles']} battles"
        }
    
    def get_recommendations_report(self, min_battles: int = 5) -> Dict:
        """
        Get comprehensive recommendations report.
        
        Args:
            min_battles: Minimum battles for consideration
        
        Returns:
            Full recommendations report
        """
        return {
            'best_overall': self.recommend('best_overall', limit=3, min_battles=min_battles),
            'best_per_strategy': self.recommend('best_for_strategy', limit=2, min_battles=min_battles),
            'trending': self.recommend('trending', limit=3, min_battles=min_battles),
            'underrated': self.recommend('underrated', limit=3, min_battles=min_battles)
        }


# Example usage
if __name__ == '__main__':
    recommender = TeamRecommender()
    
    print("Team Recommender Example")
    print("=" * 60)
    
    # Best overall
    print("\n🏆 Best Overall Teams:")
    best = recommender.recommend('best_overall', limit=3, min_battles=1)
    for i, team in enumerate(best, 1):
        print(f"\n{i}. {', '.join(team['pokemon'])}")
        print(f"   Strategy: {team['strategy']}")
        print(f"   Win Rate: {team['win_rate']*100:.1f}%")
        print(f"   Battles: {team['total_battles']}")
        print(f"   Peak Rating: {team['peak_rating']}")
    
    # Trending
    print("\n🔥 Trending Teams:")
    trending = recommender.recommend('trending', limit=2, min_battles=1)
    for i, team in enumerate(trending, 1):
        print(f"\n{i}. {', '.join(team['pokemon'])}")
        print(f"   {team['reason']}")
    
    # Full report
    print("\n📋 Full Recommendations Report:")
    report = recommender.get_recommendations_report(min_battles=1)
    print(f"  Best Overall Teams: {len(report['best_overall'])}")
    print(f"  Trending Teams: {len(report['trending'])}")
    print(f"  Underrated Teams: {len(report['underrated'])}")

