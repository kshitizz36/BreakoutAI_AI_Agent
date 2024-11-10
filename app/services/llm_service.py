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
Return information in this exact JSON format. Include as much detail as possible:
{{
    "email": "company email or null",
    "location": "headquarters location",
    "website": "main company website",
    "description": "brief company description",
    "social_media": {{
        "platform_name": "url"
    }},
    "phone": "contact phone if found",
    "additional_info": {{
        "key": "any other relevant details"
    }}
}}

Sources:
{context}

Extract only factual information found in the sources. Use null for missing information."""

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
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3]
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
            # Create a simpler verification prompt
            info_dict = info.model_dump()
            prompt = f"""Verify and validate this information about {info_dict.get('Entity', 'the entity')}:
{json.dumps(info_dict, indent=2)}

Return the verified information in this exact JSON format, with confidence scores added. Example:
{{
    "email": "example@company.com",
    "location": "City, Country",
    "website": "https://company.com",
    "description": "Company description",
    "social_media": {{"platform": "url"}},
    "phone": "phone number",
    "additional_info": {{"key": "value"}},
    "confidence_scores": {{
        "email": 0.9,
        "location": 0.8,
        "website": 1.0,
        "description": 0.9
    }}
}}"""
            
            completion = await self._rate_limited_request([
                {
                    "role": "system",
                    "content": "You are a data verification assistant. Return only valid JSON with the exact structure requested."
                },
                {"role": "user", "content": prompt}
            ])
            
            # Clean and parse response
            response_text = completion.choices[0].message.content.strip()
            
            # Remove any markdown formatting if present
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
                
            response_text = response_text.strip()
            
            try:
                verification = json.loads(response_text)
                # Ensure all required fields exist
                required_fields = ['email', 'location', 'website', 'description', 
                                 'social_media', 'phone', 'additional_info']
                for field in required_fields:
                    if field not in verification:
                        verification[field] = info_dict.get(field)
                
                # Ensure confidence scores exist
                if 'confidence_scores' not in verification:
                    verification['confidence_scores'] = {}
                
                return ExtractedInformation(**verification)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse verification response: {e}\nResponse: {response_text}")
                # Return original info if verification fails
                return info
                
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return info