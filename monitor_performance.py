"""
Performance Monitoring Script

Tracks bot performance metrics:
- Win/loss ratio
- Decision times
- Rating progression
- Error rates
"""

import json
import os
from datetime import datetime
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self, log_file="performance.json"):
        self.log_file = log_file
        self.data = self.load_data()
    
    def load_data(self):
        """Load existing performance data"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return {
            "battles": [],
            "stats": {
                "total_battles": 0,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "errors": 0
            },
            "rating_history": [],
            "decision_times": [],
            "formats": defaultdict(lambda: {"wins": 0, "losses": 0})
        }
    
    def save_data(self):
        """Save performance data"""
        with open(self.log_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def record_battle(self, battle_info):
        """
        Record a battle result
        
        Args:
            battle_info (dict): {
                'result': 'win' | 'loss' | 'tie',
                'format': 'gen9vgc2024',
                'rating': 1234,
                'opponent': 'opponent_name',
                'turns': 15,
                'avg_decision_time': 1.5,
                'team': 'team1',
                'timestamp': '2025-11-27 12:00:00'
            }
        """
        # Add to battles list
        self.data["battles"].append(battle_info)
        
        # Update stats
        self.data["stats"]["total_battles"] += 1
        if battle_info['result'] == 'win':
            self.data["stats"]["wins"] += 1
        elif battle_info['result'] == 'loss':
            self.data["stats"]["losses"] += 1
        else:
            self.data["stats"]["ties"] += 1
        
        # Update rating history
        if 'rating' in battle_info:
            self.data["rating_history"].append({
                'battle': self.data["stats"]["total_battles"],
                'rating': battle_info['rating'],
                'timestamp': battle_info.get('timestamp', str(datetime.now()))
            })
        
        # Update decision times
        if 'avg_decision_time' in battle_info:
            self.data["decision_times"].append(battle_info['avg_decision_time'])
        
        # Update format stats
        fmt = battle_info.get('format', 'unknown')
        if battle_info['result'] == 'win':
            self.data["formats"][fmt]["wins"] += 1
        elif battle_info['result'] == 'loss':
            self.data["formats"][fmt]["losses"] += 1
        
        self.save_data()
    
    def record_error(self, error_info):
        """Record an error"""
        if "errors" not in self.data:
            self.data["errors"] = []
        self.data["errors"].append({
            'timestamp': str(datetime.now()),
            'error': str(error_info)
        })
        self.data["stats"]["errors"] += 1
        self.save_data()
    
    def get_summary(self):
        """Get performance summary"""
        stats = self.data["stats"]
        total = stats["total_battles"]
        
        if total == 0:
            return "No battles recorded yet."
        
        win_rate = (stats["wins"] / total) * 100
        
        summary = f"""
Performance Summary
==================

Battles: {total}
Wins:    {stats["wins"]} ({win_rate:.1f}%)
Losses:  {stats["losses"]} ({(stats["losses"]/total)*100:.1f}%)
Ties:    {stats["ties"]}
Errors:  {stats["errors"]}

Rating:
  Current: {self.data["rating_history"][-1]["rating"] if self.data["rating_history"] else "N/A"}
  Peak:    {max([r["rating"] for r in self.data["rating_history"]]) if self.data["rating_history"] else "N/A"}
  Start:   {self.data["rating_history"][0]["rating"] if self.data["rating_history"] else "N/A"}

Decision Time:
  Average: {sum(self.data["decision_times"])/len(self.data["decision_times"]):.2f}s
  Min:     {min(self.data["decision_times"]):.2f}s
  Max:     {max(self.data["decision_times"]):.2f}s

By Format:
"""
        for fmt, data in self.data["formats"].items():
            fmt_total = data["wins"] + data["losses"]
            fmt_wr = (data["wins"] / fmt_total) * 100 if fmt_total > 0 else 0
            summary += f"  {fmt}: {data['wins']}-{data['losses']} ({fmt_wr:.1f}%)\n"
        
        return summary
    
    def get_recent_battles(self, n=10):
        """Get recent battle results"""
        return self.data["battles"][-n:]
    
    def get_rating_trend(self):
        """Get rating progression"""
        return self.data["rating_history"]
    
    def export_csv(self, filename="battles.csv"):
        """Export battles to CSV"""
        import csv
        
        with open(filename, 'w', newline='') as f:
            if not self.data["battles"]:
                return
            
            fieldnames = self.data["battles"][0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for battle in self.data["battles"]:
                writer.writerow(battle)


def example_usage():
    """Example of how to use the monitor"""
    
    # Create monitor
    monitor = PerformanceMonitor()
    
    # Record a battle
    monitor.record_battle({
        'result': 'win',
        'format': 'gen9vgc2024',
        'rating': 1234,
        'opponent': 'TestOpponent',
        'turns': 15,
        'avg_decision_time': 1.5,
        'team': 'team1',
        'timestamp': str(datetime.now())
    })
    
    # Get summary
    print(monitor.get_summary())
    
    # Export to CSV
    monitor.export_csv()


if __name__ == "__main__":
    import sys
    
    monitor = PerformanceMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "summary":
            print(monitor.get_summary())
        elif sys.argv[1] == "recent":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            battles = monitor.get_recent_battles(n)
            print(f"\nLast {len(battles)} battles:")
            for i, battle in enumerate(battles, 1):
                print(f"{i}. {battle['result'].upper()} vs {battle.get('opponent', '?')} "
                      f"({battle.get('format', '?')}) - Rating: {battle.get('rating', '?')}")
        elif sys.argv[1] == "export":
            filename = sys.argv[2] if len(sys.argv) > 2 else "battles.csv"
            monitor.export_csv(filename)
            print(f"Exported to {filename}")
        else:
            print("Usage: python monitor_performance.py [summary|recent|export]")
    else:
        print(monitor.get_summary())

