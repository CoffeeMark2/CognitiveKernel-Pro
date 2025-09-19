import sys
import os
import json
from typing import List, Dict, Any, Optional
import traceback

# Add the bc project to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents', 'bc'))

# Import from the correct relative paths
from .utils import KwargsInitializable, rprint, GET_ENV_VAR
from ..agents.tool import Tool

# Import the necessary components from the bc project
try:
    # from .bc.searcher.tools import register_tools
    from .bc.search_agent.query import QueryAgent
    from .bc.searcher.searchers import SearcherType

except ImportError as e:
    traceback.print_exc()
    rprint(f"Warning: Could not import bc search components: {e}")
    raise ModuleNotFoundError("Please ensure the 'bc' package is correctly installed and accessible.")

class BCSearchTool(Tool):
    def __init__(self, searcher_type="bm25", index_path="/data/guibin/xkf/bc-ck/ck/ck_pro/agents/bc/indexes/bm25"):
        super().__init__(name="simple_web_search")
        self.index_path = index_path
        self.searcher_type = searcher_type
        self.llm = None  # will be set later

    def set_llm(self, llm):
        self.llm = llm  # might be useful for formatting?

    def get_function_definition(self, short: bool):
            if short:
                return """- def simple_web_search(query: str) -> str:  # Perform a quick web search using a search engine for straightforward information needs."""
            else:
                return """- simple_web_search
```python
def simple_web_search(query: str) -> str:
    \""" Perform a quick web search using a search engine for straightforward information needs.
    Args:
        query (str): A simple, well-phrased search term or question.
    Returns:
        str: A string containing search results, including titles, URLs, and snippets.
    Notes:
        - Use for quick lookups or when you need up-to-date information.
        - Avoid complex or multi-step queries; keep the query simple and direct.
        - Do not use for tasks requiring deep reasoning or multi-source synthesis.
    Examples:
        >>> answer = simple_web_search(query="latest iPhone")
        >>> print(answer)
    \"""
```"""
        
    
    def __call__(self, query: str):
        try:
            print(f"BCSearchTool called with query: {query}")
            searcher_class = SearcherType.get_searcher_class(self.searcher_type) 
            class SearcherArgs:
                index_path = self.index_path
            my_agent = QueryAgent(
                searcher_class=searcher_class,
                searcher_args=SearcherArgs()
            )
            ret= my_agent.ask(query)
            print(f"BCSearchTool returning: {ret}")
            return ret
        
        except Exception as e:
            traceback.print_exc()
            rprint(f"Error in BCSearchTool: {e}")
            return "Search Results: An error occurred during the search."