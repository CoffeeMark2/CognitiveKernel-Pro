#!/usr/bin/env python3

import sys
import os
import traceback

# Add the project root to the path

#check system path
print("System path:", sys.path)

def test_bc_search_tool():
    try:
        # Import the new BCSearchTool
        from ck_pro.agents.bc_search_tool import BCSearchTool

        print("Successfully imported BCSearchTool")

        # Try to create an instance
        try:
            search_tool = BCSearchTool(max_results=3)
            print("Successfully created BCSearchTool instance")

            # Try to get function definition
            func_def = search_tool.get_function_definition(short=True)
            print(f"Function definition: {func_def}")

            # Try to perform a search (this will use the placeholder implementation)
            result = search_tool("test query")
            print(f"Search result: {result}")

        except Exception as e:
            traceback.print_exc()
            print(f"Error creating or using BCSearchTool: {e}")
            return False

    except ImportError as e:
        traceback.print_exc()
        print(f"Failed to import BCSearchTool: {e}")
        return False
    except Exception as e:
        traceback.print_exc()
        print(f"Unexpected error: {e}")
        return False

    return True

if __name__ == "__main__":
    print("Testing BCSearchTool...")
    success = test_bc_search_tool()
    if success:
        print("Test passed!")
    else:
        print("Test failed!")
        sys.exit(1)