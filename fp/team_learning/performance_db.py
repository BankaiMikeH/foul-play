"""
Performance Database

SQLite database for storing and querying battle performance data.
Tracks teams, Pokemon, strategies, and battle results.

Phase 12 - Team Learning & Adaptation
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class PerformanceDatabase:
    """SQLite database for battle performance tracking."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize performance database.
        
        Args:
            db_path: Path to SQLite database file, or None for default
        """
        if db_path is None:
            # Default to fp/data/battles.db
            db_path = os.path.join(os.path.dirname(__file__), '../data/battles.db')
        
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Connect to SQLite database."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Battles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                team_hash TEXT NOT NULL,
                strategy TEXT,
                format TEXT,
                opponent TEXT,
                result TEXT NOT NULL,
                rating_before INTEGER,
                rating_after INTEGER,
                rating_change INTEGER,
                turns INTEGER,
                duration_seconds INTEGER
            )
        """)
        
        # Team performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_performance (
                team_hash TEXT PRIMARY KEY,
                team_json TEXT NOT NULL,
                strategy TEXT,
                total_battles INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                avg_rating INTEGER DEFAULT 1500,
                peak_rating INTEGER DEFAULT 1500,
                avg_turns REAL DEFAULT 0.0,
                last_used TEXT,
                phase10_score REAL,
                created_at TEXT
            )
        """)
        
        # Pokemon performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pokemon_performance (
                pokemon_name TEXT PRIMARY KEY,
                total_battles INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                times_fainted INTEGER DEFAULT 0,
                survival_rate REAL DEFAULT 1.0,
                last_used TEXT
            )
        """)
        
        # Strategy performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                strategy TEXT PRIMARY KEY,
                total_battles INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                avg_rating INTEGER DEFAULT 1500,
                best_team_hash TEXT,
                best_team_winrate REAL DEFAULT 0.0
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_timestamp ON battles(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_team_hash ON battles(team_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_strategy ON battles(strategy)")
        
        self.conn.commit()
    
    def record_battle(self, team_hash: str, strategy: str, format_name: str,
                     opponent: str, result: str, rating_before: int,
                     rating_after: int, turns: int = 0,
                     duration_seconds: int = 0) -> int:
        """Record a battle to the database."""
        cursor = self.conn.cursor()
        
        timestamp = datetime.now().isoformat()
        rating_change = rating_after - rating_before
        
        cursor.execute("""
            INSERT INTO battles 
            (timestamp, team_hash, strategy, format, opponent, result,
             rating_before, rating_after, rating_change, turns, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, team_hash, strategy, format_name, opponent, result,
              rating_before, rating_after, rating_change, turns, duration_seconds))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def update_team_performance(self, team_hash: str, team_json: str,
                               strategy: str, result: str, rating_after: int,
                               turns: int, phase10_score: Optional[float] = None):
        """Update team performance stats."""
        cursor = self.conn.cursor()
        
        # Check if team exists
        cursor.execute("SELECT * FROM team_performance WHERE team_hash = ?", (team_hash,))
        existing = cursor.fetchone()
        
        timestamp = datetime.now().isoformat()
        
        if existing:
            # Update existing record
            total_battles = existing['total_battles'] + 1
            wins = existing['wins'] + (1 if result == 'win' else 0)
            losses = existing['losses'] + (1 if result == 'loss' else 0)
            ties = existing['ties'] + (1 if result == 'tie' else 0)
            win_rate = wins / total_battles if total_battles > 0 else 0.0
            
            # Update average rating
            avg_rating = ((existing['avg_rating'] * existing['total_battles']) + rating_after) / total_battles
            
            # Update peak rating
            peak_rating = max(existing['peak_rating'], rating_after)
            
            # Update average turns
            avg_turns = ((existing['avg_turns'] * existing['total_battles']) + turns) / total_battles
            
            cursor.execute("""
                UPDATE team_performance
                SET total_battles = ?, wins = ?, losses = ?, ties = ?,
                    win_rate = ?, avg_rating = ?, peak_rating = ?,
                    avg_turns = ?, last_used = ?
                WHERE team_hash = ?
            """, (total_battles, wins, losses, ties, win_rate, int(avg_rating),
                  peak_rating, avg_turns, timestamp, team_hash))
        else:
            # Insert new record
            wins = 1 if result == 'win' else 0
            losses = 1 if result == 'loss' else 0
            ties = 1 if result == 'tie' else 0
            win_rate = wins / 1.0
            
            cursor.execute("""
                INSERT INTO team_performance
                (team_hash, team_json, strategy, total_battles, wins, losses, ties,
                 win_rate, avg_rating, peak_rating, avg_turns, last_used,
                 phase10_score, created_at)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (team_hash, team_json, strategy, wins, losses, ties, win_rate,
                  rating_after, rating_after, float(turns), timestamp,
                  phase10_score, timestamp))
        
        self.conn.commit()
    
    def update_pokemon_performance(self, pokemon_name: str, result: str,
                                   fainted: bool = False):
        """Update Pokemon performance stats."""
        cursor = self.conn.cursor()
        
        # Check if Pokemon exists
        cursor.execute("SELECT * FROM pokemon_performance WHERE pokemon_name = ?", (pokemon_name,))
        existing = cursor.fetchone()
        
        timestamp = datetime.now().isoformat()
        
        if existing:
            # Update existing
            total_battles = existing['total_battles'] + 1
            wins = existing['wins'] + (1 if result == 'win' else 0)
            losses = existing['losses'] + (1 if result == 'loss' else 0)
            ties = existing['ties'] + (1 if result == 'tie' else 0)
            win_rate = wins / total_battles if total_battles > 0 else 0.0
            
            times_fainted = existing['times_fainted'] + (1 if fainted else 0)
            survival_rate = 1.0 - (times_fainted / total_battles)
            
            cursor.execute("""
                UPDATE pokemon_performance
                SET total_battles = ?, wins = ?, losses = ?, ties = ?,
                    win_rate = ?, times_fainted = ?, survival_rate = ?,
                    last_used = ?
                WHERE pokemon_name = ?
            """, (total_battles, wins, losses, ties, win_rate, times_fainted,
                  survival_rate, timestamp, pokemon_name))
        else:
            # Insert new
            wins = 1 if result == 'win' else 0
            losses = 1 if result == 'loss' else 0
            ties = 1 if result == 'tie' else 0
            win_rate = wins / 1.0
            times_fainted = 1 if fainted else 0
            survival_rate = 0.0 if fainted else 1.0
            
            cursor.execute("""
                INSERT INTO pokemon_performance
                (pokemon_name, total_battles, wins, losses, ties, win_rate,
                 times_fainted, survival_rate, last_used)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)
            """, (pokemon_name, wins, losses, ties, win_rate, times_fainted,
                  survival_rate, timestamp))
        
        self.conn.commit()
    
    def update_strategy_performance(self, strategy: str, result: str,
                                   rating_after: int, team_hash: str):
        """Update strategy performance stats."""
        cursor = self.conn.cursor()
        
        # Check if strategy exists
        cursor.execute("SELECT * FROM strategy_performance WHERE strategy = ?", (strategy,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            total_battles = existing['total_battles'] + 1
            wins = existing['wins'] + (1 if result == 'win' else 0)
            losses = existing['losses'] + (1 if result == 'loss' else 0)
            ties = existing['ties'] + (1 if result == 'tie' else 0)
            win_rate = wins / total_battles if total_battles > 0 else 0.0
            
            # Update average rating
            avg_rating = ((existing['avg_rating'] * existing['total_battles']) + rating_after) / total_battles
            
            # Update best team if this is a win
            if result == 'win':
                cursor.execute("""
                    SELECT win_rate FROM team_performance WHERE team_hash = ?
                """, (team_hash,))
                team_perf = cursor.fetchone()
                if team_perf and team_perf['win_rate'] > existing['best_team_winrate']:
                    cursor.execute("""
                        UPDATE strategy_performance
                        SET best_team_hash = ?, best_team_winrate = ?
                        WHERE strategy = ?
                    """, (team_hash, team_perf['win_rate'], strategy))
            
            cursor.execute("""
                UPDATE strategy_performance
                SET total_battles = ?, wins = ?, losses = ?, ties = ?,
                    win_rate = ?, avg_rating = ?
                WHERE strategy = ?
            """, (total_battles, wins, losses, ties, win_rate, int(avg_rating), strategy))
        else:
            # Insert new
            wins = 1 if result == 'win' else 0
            losses = 1 if result == 'loss' else 0
            ties = 1 if result == 'tie' else 0
            win_rate = wins / 1.0
            
            cursor.execute("""
                INSERT INTO strategy_performance
                (strategy, total_battles, wins, losses, ties, win_rate,
                 avg_rating, best_team_hash, best_team_winrate)
                VALUES (?, 1, ?, ?, ?, ?, ?, NULL, 0.0)
            """, (strategy, wins, losses, ties, win_rate, rating_after))
        
        self.conn.commit()
    
    def get_team_performance(self, team_hash: str) -> Optional[Dict]:
        """Get performance stats for a team."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM team_performance WHERE team_hash = ?", (team_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_pokemon_performance(self, pokemon_name: str) -> Optional[Dict]:
        """Get performance stats for a Pokemon."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM pokemon_performance WHERE pokemon_name = ?", (pokemon_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_strategy_performance(self, strategy: str) -> Optional[Dict]:
        """Get performance stats for a strategy."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM strategy_performance WHERE strategy = ?", (strategy,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_recent_battles(self, limit: int = 10) -> List[Dict]:
        """Get recent battles."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM battles 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_overall_win_rate(self) -> float:
        """Get overall win rate across all battles."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins
            FROM battles
        """)
        row = cursor.fetchone()
        if row and row['total'] > 0:
            return row['wins'] / row['total']
        return 0.0
    
    def get_top_teams(self, limit: int = 10, min_battles: int = 5) -> List[Dict]:
        """Get top performing teams."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM team_performance
            WHERE total_battles >= ?
            ORDER BY win_rate DESC, total_battles DESC
            LIMIT ?
        """, (min_battles, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_top_pokemon(self, limit: int = 10, min_battles: int = 10) -> List[Dict]:
        """Get top performing Pokemon."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM pokemon_performance
            WHERE total_battles >= ?
            ORDER BY win_rate DESC, total_battles DESC
            LIMIT ?
        """, (min_battles, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_top_strategies(self) -> List[Dict]:
        """Get strategies ordered by win rate."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM strategy_performance
            ORDER BY win_rate DESC, total_battles DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Get overall statistics."""
        cursor = self.conn.cursor()
        
        # Total battles
        cursor.execute("SELECT COUNT(*) as count FROM battles")
        total_battles = cursor.fetchone()['count']
        
        # Win/loss record
        cursor.execute("""
            SELECT result, COUNT(*) as count
            FROM battles
            GROUP BY result
        """)
        results = {row['result']: row['count'] for row in cursor.fetchall()}
        
        # Unique teams used
        cursor.execute("SELECT COUNT(DISTINCT team_hash) as count FROM battles")
        unique_teams = cursor.fetchone()['count']
        
        # Average rating
        cursor.execute("SELECT AVG(rating_after) as avg_rating FROM battles")
        avg_rating = cursor.fetchone()['avg_rating'] or 1500
        
        return {
            'total_battles': total_battles,
            'wins': results.get('win', 0),
            'losses': results.get('loss', 0),
            'ties': results.get('tie', 0),
            'win_rate': results.get('win', 0) / total_battles if total_battles > 0 else 0.0,
            'unique_teams': unique_teams,
            'avg_rating': int(avg_rating)
        }
    
    def clear_all_data(self):
        """Clear all data from database (use with caution!)."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM battles")
        cursor.execute("DELETE FROM team_performance")
        cursor.execute("DELETE FROM pokemon_performance")
        cursor.execute("DELETE FROM strategy_performance")
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == '__main__':
    # Test database
    db = PerformanceDatabase('test_battles.db')
    
    print("Performance Database Test")
    print("=" * 60)
    
    # Record some test battles
    print("\nRecording test battles...")
    
    for i in range(5):
        result = 'win' if i < 3 else 'loss'
        battle_id = db.record_battle(
            team_hash='test_team_hash',
            strategy='Balanced',
            format_name='gen9vgc2026regf',
            opponent=f'Opponent{i}',
            result=result,
            rating_before=1500 + i*20,
            rating_after=1500 + i*20 + (20 if result == 'win' else -20),
            turns=10 + i
        )
        print(f"  Recorded battle {battle_id}: {result}")
        
        # Update team performance
        db.update_team_performance(
            team_hash='test_team_hash',
            team_json='{"team": "test"}',
            strategy='Balanced',
            result=result,
            rating_after=1500 + i*20,
            turns=10 + i,
            phase10_score=8.0
        )
        
        # Update Pokemon performance
        db.update_pokemon_performance('Incineroar', result, fainted=(i == 0))
    
    # Get statistics
    print("\nOverall Statistics:")
    stats = db.get_statistics()
    print(f"  Total Battles: {stats['total_battles']}")
    print(f"  Win Rate: {stats['win_rate']*100:.1f}%")
    print(f"  Average Rating: {stats['avg_rating']}")
    
    # Get team performance
    print("\nTeam Performance:")
    team_stats = db.get_team_performance('test_team_hash')
    if team_stats:
        print(f"  Battles: {team_stats['total_battles']}")
        print(f"  Win Rate: {team_stats['win_rate']*100:.1f}%")
        print(f"  Peak Rating: {team_stats['peak_rating']}")
    
    # Get Pokemon performance
    print("\nIncineroar Performance:")
    pkmn_stats = db.get_pokemon_performance('Incineroar')
    if pkmn_stats:
        print(f"  Battles: {pkmn_stats['total_battles']}")
        print(f"  Win Rate: {pkmn_stats['win_rate']*100:.1f}%")
        print(f"  Survival Rate: {pkmn_stats['survival_rate']*100:.1f}%")
    
    # Clean up
    print("\nCleaning up test data...")
    db.clear_all_data()
    db.close()
    
    # Remove test database
    import os
    if os.path.exists('test_battles.db'):
        os.remove('test_battles.db')
    
    print("✅ Database test complete!")

