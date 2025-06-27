"""
Query Routing Service Module - Uses Ollama LLM to intelligently route queries to appropriate endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import logging
from injector import inject, singleton

from qgpt_core.server.utils.auth import authenticated
from qgpt_core.components.llm.llm_component import LLMComponent
from qgpt_core.settings.settings import Settings
from llama_index.core.llms import ChatMessage, MessageRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

query_router = APIRouter(prefix="/v1/query", dependencies=[Depends(authenticated)])


class QueryMessage(BaseModel):
    """Message model for query analysis"""
    role: str = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")


class QueryAnalysisRequest(BaseModel):
    """Request model for query analysis"""
    query: str = Field(..., description="User query to analyze")
    messages: Optional[List[QueryMessage]] = Field(default=[], description="Conversation history")
    context_files: Optional[List[str]] = Field(default=[], description="Available context files")


class QueryAnalysisResponse(BaseModel):
    """Response model for query analysis"""
    recommended_mode: Literal["RAG", "Maps", "Basic", "Search", "Summarize", "AgenticBot", "ToolCalling"] = Field(
        ..., description="Recommended mode for handling the query"
    )
    confidence: float = Field(..., description="Confidence score for the recommendation (0-1)")
    reasoning: str = Field(..., description="Explanation for the recommendation")
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, description="Any extracted data from the query")


@singleton
class QueryRoutingService:
    """Service for analyzing queries and routing them to appropriate endpoints"""
    
    @inject
    def __init__(self, settings: Settings, llm_component: LLMComponent):
        self.settings = settings
        self.llm_component = llm_component
        
    def analyze_query(self, request: QueryAnalysisRequest) -> QueryAnalysisResponse:
        """Analyze a query and determine the best mode to handle it"""
        try:
            # Prepare the analysis prompt
            analysis_prompt = self._create_analysis_prompt(request)
            
            # Use LLM to analyze the query
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=analysis_prompt),
                ChatMessage(role=MessageRole.USER, content=f"Analyze this query: {request.query}")
            ]
            
            # Get response from LLM
            response = self.llm_component.llm.chat(messages)
            analysis_result = response.message.content
            
            # Parse the LLM response
            return self._parse_analysis_result(analysis_result, request.query)
            
        except Exception as e:
            logger.error(f"Error in query analysis: {str(e)}")
            # Return a safe default
            return QueryAnalysisResponse(
                recommended_mode="RAG",
                confidence=0.5,
                reasoning="Default routing due to analysis error",
                extracted_data=None
            )
    
    def _create_analysis_prompt(self, request: QueryAnalysisRequest) -> str:
        """Create the system prompt for query analysis"""
        
        context_info = ""
        if request.context_files:
            context_info = f"Available context files: {len(request.context_files)} files available for RAG queries."
        
        conversation_context = ""
        if request.messages:
            recent_messages = request.messages[-3:]  # Last 3 messages for context
            conversation_context = f"Recent conversation context: {[msg.content for msg in recent_messages]}"
        
        prompt = f"""You are an intelligent query router for a multi-modal AI assistant. Your job is to analyze user queries and determine the best mode to handle them.

Available modes:
1. **RAG**: For questions that need document-based context, research queries, factual questions that benefit from knowledge base
2. **Maps**: For location-based queries, geographic questions, place analysis, navigation, real estate queries
3. **Basic**: For general conversation, creative tasks, casual chat that doesn't need specific data
4. **Search**: For finding specific information within documents, keyword-based searches
5. **Summarize**: For requests to summarize content, create overviews, condense information
6. **AgenticBot**: For complex tasks requiring autonomous decision-making and multi-step planning
7. **ToolCalling**: For queries requiring external APIs, calculations, or specific tool usage

{context_info}
{conversation_context}

Instructions:
- Analyze the user's query intent, keywords, and context
- Consider location indicators: coordinates, addresses, place names, "near me", geographic terms
- Consider document-related terms: "search in documents", "what does the document say", "find information about"
- Consider summary requests: "summarize", "overview", "brief", "main points"
- Consider conversational tone vs information seeking
- Look for coordinates in formats like (lat, lng), "latitude X longitude Y", or specific addresses
- Pay attention to real estate terms: "neighborhood", "area analysis", "property", "location insights"

Respond with this exact JSON format:
{{
    "recommended_mode": "MODE_NAME",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this mode was chosen",
    "extracted_data": {{"coordinates": [lat, lng], "location_name": "name", "keywords": ["key1", "key2"]}}
}}

Examples:
- "What's the weather like?" → Basic (general conversation)
- "Analyze the area around 37.7749, -122.4194" → Maps (coordinates provided)
- "What does the contract say about payment terms?" → RAG (document-specific question)
- "Find all mentions of revenue in the documents" → Search (keyword search)
- "Summarize the main findings" → Summarize (summary request)
- "Plan a marketing strategy using available tools" → AgenticBot (complex planning)
- "Calculate the ROI using the API" → ToolCalling (external tool needed)
"""
        return prompt
    
    def _parse_analysis_result(self, analysis_result: str, original_query: str) -> QueryAnalysisResponse:
        """Parse the LLM analysis result into a structured response"""
        try:
            import json
            
            # Try to extract JSON from the response
            start_idx = analysis_result.find('{')
            end_idx = analysis_result.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = analysis_result[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                return QueryAnalysisResponse(
                    recommended_mode=parsed.get("recommended_mode", "RAG"),
                    confidence=float(parsed.get("confidence", 0.7)),
                    reasoning=parsed.get("reasoning", "LLM recommendation"),
                    extracted_data=parsed.get("extracted_data")
                )
            else:
                # Fallback parsing if JSON format is not found
                return self._fallback_parse(analysis_result, original_query)
                
        except Exception as e:
            logger.error(f"Error parsing analysis result: {str(e)}")
            return self._fallback_parse(analysis_result, original_query)
    
    def _fallback_parse(self, analysis_result: str, original_query: str) -> QueryAnalysisResponse:
        """Fallback parsing using keyword detection"""
        analysis_lower = analysis_result.lower()
        query_lower = original_query.lower()
        
        # Maps indicators
        maps_keywords = ["maps", "location", "coordinates", "latitude", "longitude", "address", "near", "area", "neighborhood", "place", "geographic"]
        if any(keyword in query_lower for keyword in maps_keywords) or "maps" in analysis_lower:
            return QueryAnalysisResponse(
                recommended_mode="Maps",
                confidence=0.8,
                reasoning="Query contains location-related keywords",
                extracted_data=None
            )
        
        # Search indicators
        search_keywords = ["find", "search", "locate", "where is", "show me"]
        if any(keyword in query_lower for keyword in search_keywords) and "document" in query_lower:
            return QueryAnalysisResponse(
                recommended_mode="Search",
                confidence=0.7,
                reasoning="Query appears to be searching within documents",
                extracted_data=None
            )
        
        # Summary indicators
        summary_keywords = ["summarize", "summary", "overview", "brief", "main points", "key findings"]
        if any(keyword in query_lower for keyword in summary_keywords):
            return QueryAnalysisResponse(
                recommended_mode="Summarize",
                confidence=0.8,
                reasoning="Query requests summarization",
                extracted_data=None
            )
        
        # Default to RAG for knowledge-based queries
        return QueryAnalysisResponse(
            recommended_mode="RAG",
            confidence=0.6,
            reasoning="Default routing for knowledge-based query",
            extracted_data=None
        )


@query_router.post("/analyze", response_model=QueryAnalysisResponse, summary="Analyze query and recommend routing")
async def analyze_query_route(request: QueryAnalysisRequest, req: Request) -> QueryAnalysisResponse:
    """
    Analyze a user query and recommend the best mode/endpoint to handle it
    """
    try:
        # Get injector from request state
        injector = req.state.injector
        query_service = injector.get(QueryRoutingService)
        
        # Analyze the query
        result = query_service.analyze_query(request)
        
        logger.info(f"Query analysis completed: {request.query[:50]}... → {result.recommended_mode} (confidence: {result.confidence})")
        return result
        
    except Exception as e:
        logger.error(f"Error in query analysis endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing query: {str(e)}")
