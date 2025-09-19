#!/usr/bin/env python3

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_web_agent_disabled():
    try:
        # Import the CKAgent
        from ck_pro.ck_main.agent import CKAgent

        # Create an instance of CKAgent
        ck_agent = CKAgent()

        # Check if web_agent is in active_functions
        if "web_agent" in ck_agent.active_functions:
            print("FAILED: web_agent is still in active_functions")
            return False
        else:
            print("PASSED: web_agent is not in active_functions")

        # Check if web_agent is in sub_agent_names
        if "web_agent" in ck_agent.sub_agent_names:
            print("FAILED: web_agent is still in sub_agent_names")
            return False
        else:
            print("PASSED: web_agent is not in sub_agent_names")

        # Check if web_agent is in ACTIVE_FUNCTIONS
        if "web_agent" in ck_agent.ACTIVE_FUNCTIONS:
            print("FAILED: web_agent is still in ACTIVE_FUNCTIONS")
            return False
        else:
            print("PASSED: web_agent is not in ACTIVE_FUNCTIONS")

        print("All tests passed! web_agent has been successfully disabled.")
        return True

    except Exception as e:
        print(f"Error during testing: {e}")
        return False

if __name__ == "__main__":
    print("Testing if web_agent is disabled...")
    success = test_web_agent_disabled()
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed!")
        sys.exit(1)