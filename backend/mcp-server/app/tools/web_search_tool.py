import httpx
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import json

router = APIRouter(tags=["web_search"])


class WebSearchInput(BaseModel):
    """Input schema for the web search tool."""
    query: str = Field(..., description="The search query to perform")
    max_results: int = Field(default=5, description="Maximum number of results to return")
    search_engine: str = Field(default="google", description="Search engine to use (google, duckduckgo)")


class SearchResult(BaseModel):
    """Schema for a single search result."""
    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str = Field(..., description="Brief description or snippet of the result")
    source: str = Field(..., description="Source of the search result")


class WebSearchOutput(BaseModel):
    """Output schema for the web search tool."""
    query: str = Field(..., description="The original search query")
    results: List[SearchResult] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results found")
    search_engine: str = Field(..., description="Search engine used")
    search_time: float = Field(..., description="Time taken for the search in seconds")


class WebSearchTool:
    """Web search tool implementation."""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
    
    async def search_google(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using Google (simulated with DuckDuckGo for demo purposes)."""
        # Note: In a real implementation, you would use Google's API
        # For demo purposes, we'll use DuckDuckGo which doesn't require API keys
        return await self.search_duckduckgo(query, max_results)
    
    async def search_duckduckgo(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using DuckDuckGo."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            # Use DuckDuckGo's HTML search
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # Extract search results from DuckDuckGo HTML
                result_elements = soup.find_all('div', class_='result')
                
                for i, element in enumerate(result_elements[:max_results]):
                    try:
                        title_elem = element.find('a', class_='result__a')
                        snippet_elem = element.find('a', class_='result__snippet')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            url = title_elem.get('href', '')
                            
                            # Clean up DuckDuckGo redirect URLs
                            if url.startswith('/l/?uddg='):
                                url = url.replace('/l/?uddg=', '')
                            
                            snippet = ""
                            if snippet_elem:
                                snippet = snippet_elem.get_text(strip=True)
                            
                            if title and url:
                                results.append(SearchResult(
                                    title=title,
                                    url=url,
                                    snippet=snippet,
                                    source="DuckDuckGo"
                                ))
                    except Exception:
                        continue
                
                return results
                
        except Exception:
            # Fallback to a simple mock search
            return self._mock_search_results(query, max_results)
    
    def _mock_search_results(self, query: str, max_results: int) -> List[SearchResult]:
        """Fallback mock search results when real search fails."""
        mock_results = [
            SearchResult(
                title=f"Mock result for: {query}",
                url=f"https://example.com/search?q={query}",
                snippet=f"This is a mock search result for the query: {query}. In a real implementation, this would be actual search results.",
                source="Mock"
            )
        ]
        return mock_results[:max_results]


# Global web search tool instance
web_search_tool = WebSearchTool()


@router.post("/web_search", response_model=WebSearchOutput, operation_id="web_search_tool")
async def web_search_tool_endpoint(input_data: WebSearchInput) -> WebSearchOutput:
    """
    Web search tool that performs real-time internet searches.
    
    This tool can search the web using various search engines and return
    relevant results with titles, URLs, and snippets.
    """
    import time
    start_time = time.time()
    
    try:
        # Perform the search based on the specified engine
        if input_data.search_engine.lower() == "google":
            results = await web_search_tool.search_google(input_data.query, input_data.max_results)
        elif input_data.search_engine.lower() == "duckduckgo":
            results = await web_search_tool.search_duckduckgo(input_data.query, input_data.max_results)
        else:
            # Default to DuckDuckGo
            results = await web_search_tool.search_duckduckgo(input_data.query, input_data.max_results)
        
        search_time = time.time() - start_time
        
        return WebSearchOutput(
            query=input_data.query,
            results=results,
            total_results=len(results),
            search_engine=input_data.search_engine,
            search_time=search_time
        )
        
    except Exception:
        # Return mock results if search fails
        search_time = time.time() - start_time
        mock_results = web_search_tool._mock_search_results(input_data.query, input_data.max_results)
        
        return WebSearchOutput(
            query=input_data.query,
            results=mock_results,
            total_results=len(mock_results),
            search_engine=input_data.search_engine,
            search_time=search_time
        ) 