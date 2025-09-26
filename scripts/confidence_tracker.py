#!/usr/bin/env python3
"""
Confidence Tracking System for ROM 2.4 Port Completion

This script analyzes confidence score trajectories to detect architectural 
issues requiring different approaches than individual task completion.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ConfidenceTracker:
    """Tracks confidence score trajectories and detects architectural issues."""
    
    def __init__(self, plan_file: Path = None):
        self.plan_file = plan_file or Path("PYTHON_PORT_PLAN.md")
        self.history: List[Dict] = []
        
    def extract_current_scores(self) -> Dict[str, Tuple[str, float]]:
        """Extract current confidence scores from the plan file."""
        if not self.plan_file.exists():
            return {}
            
        content = self.plan_file.read_text()
        scores = {}
        
        # Pattern: STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.45)
        pattern = r"### (\w+) — .*?\nSTATUS: completion:([✅❌]) implementation:(\w+) correctness:(\w+) \(confidence ([\d.]+)\)"
        
        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            subsystem = match.group(1)
            completion = match.group(2)
            confidence = float(match.group(5))
            scores[subsystem] = (completion, confidence)
            
        return scores
    
    def load_history(self, history_file: Path = None) -> None:
        """Load historical confidence tracking data."""
        history_file = history_file or Path("confidence_history.json")
        if history_file.exists():
            with open(history_file) as f:
                self.history = json.load(f)
    
    def save_history(self, history_file: Path = None) -> None:
        """Save confidence tracking history."""
        history_file = history_file or Path("confidence_history.json")
        with open(history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def record_snapshot(self) -> Dict:
        """Record a confidence snapshot with timestamp."""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "scores": self.extract_current_scores()
        }
        self.history.append(snapshot)
        return snapshot
    
    def detect_task_completion_disconnect(self) -> List[str]:
        """Detect subsystems with task-completion disconnect pattern."""
        current_scores = self.extract_current_scores()
        disconnected = []
        
        for subsystem, (completion, confidence) in current_scores.items():
            # Pattern: completion:❌ but individual tasks likely completed
            if completion == "❌" and confidence < 0.80:
                # Check if this is a known architectural issue
                architectural_indicators = [
                    "resets", "movement_encumbrance", "boards_notes",
                    "game_update_loop", "imc_chat", "logging_admin"
                ]
                if subsystem in architectural_indicators:
                    disconnected.append(subsystem)
                    
        return disconnected
    
    def detect_confidence_stagnation(self, threshold_days: int = 30) -> List[str]:
        """Detect subsystems with stagnant confidence scores."""
        if len(self.history) < 2:
            return []
            
        stagnant = []
        recent = self.history[-1]["scores"]
        old = self.history[0]["scores"] if len(self.history) > 5 else self.history[-2]["scores"]
        
        for subsystem in recent:
            if subsystem in old:
                old_confidence = old[subsystem][1]
                recent_confidence = recent[subsystem][1] 
                # Less than 0.05 improvement over time period
                if abs(recent_confidence - old_confidence) < 0.05:
                    stagnant.append(subsystem)
                    
        return stagnant
    
    def calculate_completion_probability(self) -> Dict[str, float]:
        """Calculate probability of completing each subsystem."""
        current_scores = self.extract_current_scores()
        probabilities = {}
        
        for subsystem, (completion, confidence) in current_scores.items():
            if completion == "✅":
                probabilities[subsystem] = 1.0
            else:
                # Factor in confidence score and architectural complexity
                base_prob = confidence
                
                # Adjust for known architectural challenges
                architectural_penalty = 0.0
                if subsystem in ["resets", "movement_encumbrance", "boards_notes"]:
                    architectural_penalty = 0.15
                elif subsystem in ["game_update_loop", "command_interpreter"]:
                    architectural_penalty = 0.10
                    
                probabilities[subsystem] = max(0.0, base_prob - architectural_penalty)
                
        return probabilities
    
    def generate_strategic_recommendations(self) -> Dict[str, List[str]]:
        """Generate strategic recommendations based on confidence analysis."""
        recommendations = {
            "immediate_actions": [],
            "architectural_fixes": [],
            "integration_tests": [],
            "batch_optimizations": []
        }
        
        disconnected = self.detect_task_completion_disconnect()
        stagnant = self.detect_confidence_stagnation()
        probabilities = self.calculate_completion_probability()
        
        # Immediate actions for disconnected subsystems
        for subsystem in disconnected:
            recommendations["immediate_actions"].append(
                f"Investigate {subsystem}: individual tasks completed but confidence < 0.80"
            )
        
        # Architectural fixes for low-probability subsystems
        for subsystem, prob in probabilities.items():
            if prob < 0.60:
                recommendations["architectural_fixes"].append(
                    f"Refactor {subsystem}: completion probability {prob:.2f} indicates architectural issues"
                )
        
        # Integration tests for stagnant subsystems
        for subsystem in stagnant:
            recommendations["integration_tests"].append(
                f"Add integration tests for {subsystem}: confidence score stagnation detected"
            )
        
        # Batch optimizations
        if len(disconnected) > 3:
            recommendations["batch_optimizations"].append(
                "Increase MAX_SUBSYSTEMS_PER_RUN and enable ARCHITECTURAL_FIXES mode"
            )
            
        return recommendations
    
    def print_status_report(self) -> None:
        """Print comprehensive confidence tracking status report."""
        print("=" * 60)
        print("ROM 2.4 Port Confidence Tracking Report")
        print("=" * 60)
        
        current_scores = self.extract_current_scores()
        total_subsystems = len(current_scores)
        completed = sum(1 for completion, _ in current_scores.values() if completion == "✅")
        
        print(f"Overall Progress: {completed}/{total_subsystems} subsystems completed ({completed/total_subsystems*100:.1f}%)")
        print()
        
        # Completion status breakdown
        print("Completion Status:")
        incomplete = [(name, conf) for name, (comp, conf) in current_scores.items() if comp == "❌"]
        incomplete.sort(key=lambda x: x[1])  # Sort by confidence (lowest first)
        
        for subsystem, confidence in incomplete:
            print(f"  ❌ {subsystem:20} (confidence: {confidence:.2f})")
        
        print()
        
        # Strategic recommendations
        recommendations = self.generate_strategic_recommendations()
        for category, items in recommendations.items():
            if items:
                print(f"{category.replace('_', ' ').title()}:")
                for item in items:
                    print(f"  • {item}")
                print()
        
        # Completion probability analysis
        probabilities = self.calculate_completion_probability()
        low_prob = [(name, prob) for name, prob in probabilities.items() if prob < 0.80]
        if low_prob:
            print("Low Completion Probability Subsystems:")
            low_prob.sort(key=lambda x: x[1])
            for subsystem, prob in low_prob:
                print(f"  • {subsystem:20} ({prob:.2f} probability)")


def main():
    """Main confidence tracking analysis."""
    tracker = ConfidenceTracker()
    tracker.load_history()
    
    # Record current snapshot
    snapshot = tracker.record_snapshot()
    tracker.save_history()
    
    # Generate and display report
    tracker.print_status_report()
    
    # Save detailed analysis
    recommendations = tracker.generate_strategic_recommendations()
    with open("strategic_recommendations.json", "w") as f:
        json.dump({
            "timestamp": snapshot["timestamp"],
            "current_scores": snapshot["scores"],
            "recommendations": recommendations,
            "completion_probabilities": tracker.calculate_completion_probability()
        }, f, indent=2)
    
    print(f"\nDetailed analysis saved to strategic_recommendations.json")


if __name__ == "__main__":
    main()