"""
Learning Engine

Simple machine learning for predicting team performance.
Uses scikit-learn for win rate prediction and team evaluation.

Phase 12 - Team Learning & Adaptation
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from .performance_db import PerformanceDatabase


class LearningEngine:
    """
    Machine learning engine for team performance prediction.
    
    Uses simple logistic regression to predict win probability.
    """
    
    def __init__(self, db: Optional[PerformanceDatabase] = None):
        """
        Initialize learning engine.
        
        Args:
            db: Performance database
        """
        self.db = db if db else PerformanceDatabase()
        self.model = None
        self.feature_names = []
        self.pokemon_to_index = {}
        self.trained = False
    
    def train(self, min_battles: int = 20) -> bool:
        """
        Train the model on battle history.
        
        Args:
            min_battles: Minimum battles needed for training
        
        Returns:
            True if training successful, False otherwise
        """
        # Check if we have enough data
        stats = self.db.get_statistics()
        if stats['total_battles'] < min_battles:
            return False
        
        # Extract features and labels
        X, y = self._prepare_training_data()
        
        if len(X) < min_battles:
            return False
        
        # Train model
        try:
            from sklearn.linear_model import LogisticRegression
            
            self.model = LogisticRegression(max_iter=1000)
            self.model.fit(X, y)
            self.trained = True
            
            return True
        except ImportError:
            print("⚠️  scikit-learn not installed. ML features disabled.")
            print("   Install with: pip install scikit-learn")
            return False
        except Exception as e:
            print(f"⚠️  Training failed: {e}")
            return False
    
    def predict_win_probability(self, team: List[Dict]) -> float:
        """
        Predict probability that a team will win.
        
        Args:
            team: Team to evaluate
        
        Returns:
            Win probability (0.0-1.0)
        """
        if not self.trained:
            # Fallback: use historical win rate for Pokemon
            return self._simple_prediction(team)
        
        # Extract features
        features = self._extract_features(team)
        
        # Predict
        try:
            probability = self.model.predict_proba([features])[0][1]
            return probability
        except Exception:
            return self._simple_prediction(team)
    
    def predict_rating(self, team: List[Dict], current_rating: int = 1500) -> int:
        """
        Predict expected rating after 10 battles.
        
        Args:
            team: Team to evaluate
            current_rating: Current rating
        
        Returns:
            Predicted rating
        """
        win_prob = self.predict_win_probability(team)
        
        # Simple estimation: expected rating change per battle
        # Win = +20, Loss = -20
        expected_change_per_battle = 20 * (2 * win_prob - 1)
        
        # After 10 battles
        predicted_rating = current_rating + int(expected_change_per_battle * 10)
        
        return predicted_rating
    
    def rank_teams(self, teams: List[List[Dict]]) -> List[Tuple[List[Dict], float]]:
        """
        Rank teams by predicted performance.
        
        Args:
            teams: List of teams to rank
        
        Returns:
            List of (team, win_probability) tuples, sorted by probability
        """
        rankings = []
        
        for team in teams:
            prob = self.predict_win_probability(team)
            rankings.append((team, prob))
        
        # Sort by probability (descending)
        rankings.sort(key=lambda x: -x[1])
        
        return rankings
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from database."""
        # Get all battles
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT b.team_hash, b.result, tp.team_json
            FROM battles b
            JOIN team_performance tp ON b.team_hash = tp.team_hash
        """)
        
        battles = cursor.fetchall()
        
        if not battles:
            return np.array([]), np.array([])
        
        # Build Pokemon index
        all_pokemon = set()
        import json
        
        for battle in battles:
            team_data = json.loads(battle['team_json'])
            for pokemon in team_data:
                all_pokemon.add(pokemon['name'])
        
        self.pokemon_to_index = {name: i for i, name in enumerate(sorted(all_pokemon))}
        self.feature_names = sorted(all_pokemon)
        
        # Extract features and labels
        X = []
        y = []
        
        for battle in battles:
            team_data = json.loads(battle['team_json'])
            features = self._extract_features(team_data)
            label = 1 if battle['result'] == 'win' else 0
            
            X.append(features)
            y.append(label)
        
        return np.array(X), np.array(y)
    
    def _extract_features(self, team: List[Dict]) -> np.ndarray:
        """
        Extract features from a team.
        
        Features: One-hot encoding of Pokemon presence
        """
        # Initialize feature vector
        features = np.zeros(len(self.pokemon_to_index))
        
        # Set 1 for each Pokemon on team
        for pokemon in team:
            name = pokemon['name']
            if name in self.pokemon_to_index:
                idx = self.pokemon_to_index[name]
                features[idx] = 1
        
        return features
    
    def _simple_prediction(self, team: List[Dict]) -> float:
        """Simple prediction based on historical Pokemon win rates."""
        total_win_rate = 0.0
        count = 0
        
        for pokemon in team:
            stats = self.db.get_pokemon_performance(pokemon['name'])
            if stats and stats['total_battles'] >= 3:
                total_win_rate += stats['win_rate']
                count += 1
        
        if count > 0:
            return total_win_rate / count
        
        # Default to 50%
        return 0.5
    
    def get_pokemon_value(self, pokemon_name: str) -> float:
        """
        Get the learned value of a Pokemon.
        
        Args:
            pokemon_name: Pokemon name
        
        Returns:
            Value score (-1.0 to 1.0)
        """
        if not self.trained or pokemon_name not in self.pokemon_to_index:
            # Fallback to win rate
            stats = self.db.get_pokemon_performance(pokemon_name)
            if stats and stats['total_battles'] >= 5:
                return 2 * stats['win_rate'] - 1.0  # Map 0-1 to -1 to 1
            return 0.0
        
        # Get coefficient from model
        idx = self.pokemon_to_index[pokemon_name]
        coefficient = self.model.coef_[0][idx]
        
        return coefficient
    
    def get_model_insights(self) -> Dict:
        """
        Get insights from the trained model.
        
        Returns:
            Model insights dictionary
        """
        if not self.trained:
            return {'status': 'not_trained'}
        
        # Get Pokemon values
        pokemon_values = []
        for name, idx in self.pokemon_to_index.items():
            value = self.model.coef_[0][idx]
            pokemon_values.append({'name': name, 'value': value})
        
        # Sort by value
        pokemon_values.sort(key=lambda x: -x['value'])
        
        # Training accuracy (on training data - for demonstration)
        X, y = self._prepare_training_data()
        accuracy = self.model.score(X, y)
        
        return {
            'status': 'trained',
            'accuracy': accuracy,
            'top_pokemon': pokemon_values[:10],
            'worst_pokemon': pokemon_values[-10:],
            'num_features': len(self.pokemon_to_index),
            'training_samples': len(X)
        }


# Example usage
if __name__ == '__main__':
    print("Learning Engine Example")
    print("=" * 60)
    
    # Initialize engine
    engine = LearningEngine()
    
    # Try to train
    print("\n🤖 Training model...")
    success = engine.train(min_battles=10)
    
    if success:
        print("✅ Model trained successfully!")
        
        # Get insights
        insights = engine.get_model_insights()
        print(f"\n📊 Model Insights:")
        print(f"   Training Accuracy: {insights['accuracy']*100:.1f}%")
        print(f"   Features: {insights['num_features']}")
        print(f"   Training Samples: {insights['training_samples']}")
        
        if insights.get('top_pokemon'):
            print(f"\n   Most Valuable Pokemon:")
            for pkmn in insights['top_pokemon'][:5]:
                print(f"      {pkmn['name']}: {pkmn['value']:+.3f}")
        
        # Example prediction
        example_team = [
            {'name': 'Incineroar'},
            {'name': 'Landorus-Therian'},
            {'name': 'Rillaboom'},
            {'name': 'Iron Hands'},
            {'name': 'Flutter Mane'},
            {'name': 'Gholdengo'}
        ]
        
        win_prob = engine.predict_win_probability(example_team)
        rating = engine.predict_rating(example_team, 1500)
        
        print(f"\n🔮 Example Prediction:")
        print(f"   Team: {', '.join([p['name'] for p in example_team])}")
        print(f"   Win Probability: {win_prob*100:.1f}%")
        print(f"   Expected Rating (after 10 battles): {rating}")
    else:
        print("⚠️  Not enough data to train model yet.")
        print("   Need at least 20 battles.")

