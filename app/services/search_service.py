from typing import List, Dict, Optional
from serpapi.google_search import GoogleSearch
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from bs4 import BeautifulSoup
import asyncio
import os
from pydantic import BaseModel

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str
    displayed_link: str
    content: Optional[str] = None

class SearchService:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_KEY not found in environment variables")
        
        self.async_client = httpx.AsyncClient()
        logger.add("logs/search_service.log", rotation="500 MB")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Perform an async web search with content extraction."""
        try:
            # Perform Google Search using serpapi
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": max_results,
                "engine": "google",
                "hl": "en",
                "gl": "us"
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" in results:
                raise Exception(f"SerpAPI error: {results['error']}")
            
            organic_results = results.get("organic_results", [])
            
            # Create SearchResult objects
            search_results = []
            for result in organic_results[:max_results]:
                search_results.append(SearchResult(
                    title=result.get("title", ""),
                    link=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    displayed_link=result.get("displayed_link", "")
                ))
            
            # Enhance results with content extraction
            enhanced_results = await self._enhance_search_results(search_results)
            
            return enhanced_results
                
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def _enhance_search_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Enhance search results with content extraction."""
        async def fetch_content(result: SearchResult) -> SearchResult:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        result.link,
                        timeout=10.0,
                        follow_redirects=True
                    )
                    
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    for element in soup(["script", "style"]):
                        element.decompose()
                    
                    text = soup.get_text()
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    
                    result.content = text[:5000]
                    
            except Exception as e:
                logger.warning(f"Failed to enhance content for {result.link}: {str(e)}")
                
            return result

        tasks = [fetch_content(result) for result in results]
        enhanced_results = await asyncio.gather(*tasks)
        return enhanced_results

    async def batch_search(self, queries: List[str], batch_size: int = 10) -> Dict[str, List[SearchResult]]:
        """Perform batch searches with rate limiting."""
        results = {}
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            batch_tasks = [self.search(query) for query in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            
            for query, result in zip(batch, batch_results):
                results[query] = result
            
            if i + batch_size < len(queries):
                await asyncio.sleep(2)
                
        return results