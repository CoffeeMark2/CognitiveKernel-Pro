#!/usr/bin/env python3

import sys
import os

from ck_pro.agents.bc_search_tool import BCSearchTool

def test_bc_search_tool():

    # Create an instance of BCSearchTool
    search_tool = BCSearchTool()

    # Test the __call__ method with a simple query
    result = search_tool("capital city of country where learning institution is situated 2023")
    print("Search result:")
    print(result)
    print()

    print("Test completed!")

if __name__ == "__main__":
    test_bc_search_tool()