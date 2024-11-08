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

    async def extract_information(self, search_results: List[Dict], entity: str) -> ExtractedInformation:
        """Extract structured information from search results using the LLM."""
        try:
            prompt = self._create_extraction_prompt(search_results, entity)
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise information extraction assistant. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            response_text = completion.choices[0].message.content
            try:
                extracted_info = json.loads(response_text)
                return ExtractedInformation(**extracted_info)
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON for entity: {entity}")
                return ExtractedInformation()
                
        except Exception as e:
            logger.error(f"LLM extraction failed for entity {entity}: {str(e)}")
            return ExtractedInformation()

    def _create_extraction_prompt(self, search_results: List[Dict], entity: str) -> str:
        """Create a structured prompt for information extraction."""
        context = "\n\n".join([
            f"Title: {result['title']}\nURL: {result['link']}\nContent: {result.get('content', result['snippet'])}"
            for result in search_results
        ])
        
        return f"""Task: Extract structured information about {entity} from the following search results.
        
Search Results:
{context}

Extract the following information in JSON format:
- email: Any email addresses found
- location: Physical location or address
- website: Main website URL
- description: Brief description
- social_media: Dictionary of social media platforms and their links
- phone: Contact phone numbers
- additional_info: Any other relevant information

Format as valid JSON. Use null for missing information. Include confidence scores (0-1) for each field.
"""

    async def verify_information(self, info: ExtractedInformation) -> ExtractedInformation:
        """Verify and validate extracted information."""
        try:
            prompt = f"""Verify the following extracted information and provide confidence scores:
            {json.dumps(info.dict(), indent=2)}
            
            For each field:
            1. Verify the format (email, URL, phone number, etc.)
            2. Check for completeness and accuracy
            3. Provide a confidence score (0-1)
            
            Respond with JSON containing the verified information and confidence scores.
            """
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data verification assistant."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            verification = json.loads(completion.choices[0].message.content)
            return ExtractedInformation(**verification)
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return info