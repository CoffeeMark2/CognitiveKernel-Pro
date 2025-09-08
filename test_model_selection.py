#!/usr/bin/env python3
"""
Test script for the model selection feature
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ck_pro.agents.agent import MultiStepAgent, AgentSession
from ck_pro.agents.model import LLM

def test_model_selection():
    """Test the model selection feature"""
    print("Testing model selection feature...")
    
    # Create a simple agent
    agent = MultiStepAgent()
    
    # Check that assigner model is initialized
    print(f"Assigner model: {agent.assigner_model}")
    print(f"Model list: {agent.model_list}")
    
    # Create a simple session
    session = AgentSession(task="Test task: What is 2+2?")
    
    # Add a step to the session to avoid index error
    session.add_step({"step_idx": 0})
    
    # Test model selection
    state = {}
    selected_model = agent.select_model_for_step(session, state)
    print(f"Selected model: {selected_model}")
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_model_selection()