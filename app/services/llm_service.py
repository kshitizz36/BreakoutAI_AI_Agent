from typing import List, Dict, Any, Optional
from groq import Groq
import json
from loguru import logger
from pydantic import BaseModel, Field
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import os

class ExtractedInformation(BaseModel):
    email: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    social_media: Dict[str, str] = Field(default_factory=dict)
    phone: Optional[str] = None
    additional_info: Dict[str, Any] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "mixtral-8x7b-32768"
        logger.add("logs/llm_service.log", rotation="500 MB")
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Minimum time between requests

    def _truncate_text(self, text: str, max_length: int = 200) -> str:
        """Truncate text while keeping complete sentences."""
        if not text or len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        if last_period > 0:
            return truncated[:last_period + 1]
        return truncated + "..."

    def _create_extraction_prompt(self, search_results: List[Any], entity: str) -> str:
        """Create a structured prompt for information extraction."""
        # Take only first 3 results and truncate content
        limited_results = search_results[:3]
        context = "\n".join([
            f"Source {i+1}:\n"
            f"Title: {result.title}\n"
            f"URL: {result.link}\n"
            f"Content: {self._truncate_text(result.content if result.content else result.snippet)}"
            for i, result in enumerate(limited_results)
        ])
        
        return f"""Find key information about {entity} from these sources.
Provide information in this JSON format:
{{
    "website": "main website",
    "location": "headquarters location",
    "description": "brief company description",
    "email": "contact email if found",
    "phone": "contact phone if found",
    "social_media": {{"platform": "url"}},
    "additional_info": {{"key": "value"}}
}}

Sources:
{context}

Extract only factual information present in the sources."""

    async def _rate_limited_request(self, messages: List[Dict[str, str]], max_retries: int = 3) -> Any:
        """Make a rate-limited request to the LLM API."""
        for attempt in range(max_retries):
            try:
                # Add delay between requests
                await asyncio.sleep(self.min_request_interval)
                
                completion = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=500
                )
                return completion
            except Exception as e:
                if "rate_limit_exceeded" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # Exponential backoff
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    continue
                raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def extract_information(self, search_results: List[Any], entity: str) -> ExtractedInformation:
        """Extract structured information from search results using the LLM."""
        try:
            prompt = self._create_extraction_prompt(search_results, entity)
            
            completion = await self._rate_limited_request([
                {
                    "role": "system",
                    "content": "You are a precise information extraction assistant. Return only valid JSON."
                },
                {"role": "user", "content": prompt}
            ])
            
            response_text = completion.choices[0].message.content.strip()
            try:
                # Clean response if needed
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3]
                response_text = response_text.strip()
                
                extracted_info = json.loads(response_text)
                return ExtractedInformation(**extracted_info)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON for entity {entity}: {e}")
                return ExtractedInformation()
                
        except Exception as e:
            logger.error(f"LLM extraction failed for entity {entity}: {str(e)}")
            return ExtractedInformation()

    async def verify_information(self, info: ExtractedInformation) -> ExtractedInformation:
        """Verify and validate extracted information."""
        try:
            # Simplified verification prompt
            prompt = "Verify this information is well-formatted and add confidence scores:\n" + \
                    json.dumps(info.model_dump(), indent=2)
            
            completion = await self._rate_limited_request([
                {
                    "role": "system",
                    "content": "You are a data verification assistant. Return only valid JSON."
                },
                {"role": "user", "content": prompt}
            ])
            
            response_text = completion.choices[0].message.content.strip()
            try:
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3]
                response_text = response_text.strip()
                
                verification = json.loads(response_text)
                return ExtractedInformation(**verification)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse verification response: {e}")
                return info
                
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return info