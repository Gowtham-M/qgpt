# Intelligent Query Routing System

## Overview

The QGPT application now includes an intelligent query routing system that uses an Ollama LLM to automatically analyze user queries and route them to the most appropriate processing mode (RAG, Maps, Basic Chat, etc.).

## How It Works

### 1. Query Analysis Pipeline

When a user submits a query, the system follows this flow:

```
User Query → Query Analysis API → Ollama LLM → Mode Recommendation → Automatic Routing
```

1. **User Input**: User types a query in the chat interface
2. **Query Analysis**: The query is sent to `/v1/query/analyze` endpoint
3. **LLM Processing**: Ollama analyzes the query intent, keywords, and context
4. **Mode Recommendation**: AI recommends the best mode with confidence score
5. **Automatic Routing**: System automatically switches modes and processes the query

### 2. Supported Modes

The system can intelligently route queries to these modes:

- **RAG Mode**: Document-based questions, research queries, factual questions
- **Maps Mode**: Location analysis, geographic queries, real estate questions
- **Basic Mode**: General conversation, creative tasks, casual chat
- **Search Mode**: Finding specific information within documents
- **Summarize Mode**: Content summarization requests
- **AgenticBot Mode**: Complex multi-step autonomous tasks
- **ToolCalling Mode**: External API interactions, calculations

### 3. Key Features

#### Intelligent Detection
- **Location Queries**: Automatically detects coordinates, addresses, place names
- **Document Queries**: Identifies requests for document-based information
- **Conversational Intent**: Recognizes casual vs. information-seeking queries
- **Task Complexity**: Determines if autonomous planning or tools are needed

#### User Experience
- **Seamless Mode Switching**: Automatic mode changes based on query intent
- **Real-time Feedback**: Shows analysis results with confidence scores
- **Visual Notifications**: Displays AI reasoning for mode recommendations
- **Fallback Handling**: Gracefully handles analysis errors

#### Context Awareness
- **Conversation History**: Considers recent messages for better routing
- **Available Resources**: Takes into account uploaded documents and context
- **User Preferences**: Learns from interaction patterns

## Technical Implementation

### Backend Components

#### 1. Query Router (`/qgpt_core/server/query_router/`)
- **Purpose**: Analyzes queries using Ollama LLM
- **Endpoint**: `POST /v1/query/analyze`
- **Input**: Query text, conversation history, context files
- **Output**: Recommended mode, confidence score, reasoning

#### 2. Query Routing Service
```python
@singleton
class QueryRoutingService:
    def analyze_query(self, request: QueryAnalysisRequest) -> QueryAnalysisResponse:
        # Uses Ollama LLM to analyze query intent
        # Returns structured recommendation with reasoning
```

#### 3. LLM Analysis Prompt
The system uses a sophisticated prompt that instructs the Ollama LLM to:
- Analyze user intent and keywords
- Consider context and conversation history
- Evaluate available resources
- Provide structured JSON responses with reasoning

### Frontend Components

#### 1. Enhanced `handleSendMessageWithMaps` Function
```typescript
const handleSendMessageWithMaps = async () => {
    // 1. Analyze query with AI
    const analysisResult = await analyzeQuery(input, messages, fileIds);
    
    // 2. Handle specific routing (Maps, coordinates, etc.)
    if (coords || locationMatch || analysisResult.recommended_mode === "Maps") {
        // Switch to Maps mode and process location
    }
    
    // 3. Apply AI recommendations
    if (analysisResult.confidence > 0.7) {
        setMode(analysisResult.recommended_mode);
    }
    
    // 4. Continue with normal processing
    handleSendMessage();
};
```

#### 2. Analysis Notification Component
- Shows AI recommendations in real-time
- Displays confidence scores and reasoning
- Auto-dismisses after 5 seconds
- User can manually close notifications

## Usage Examples

### Example 1: Location Query
**User Input**: "Analyze the neighborhood around 37.7749, -122.4194"
**AI Analysis**: 
- Detected: Coordinates present
- Recommended Mode: Maps
- Confidence: 95%
- Reasoning: "Query contains specific coordinates for location analysis"
**Result**: Automatically switches to Maps mode and analyzes the San Francisco location

### Example 2: Document Query
**User Input**: "What does the contract say about payment terms?"
**AI Analysis**:
- Detected: Document-specific question
- Recommended Mode: RAG
- Confidence: 88%
- Reasoning: "Query seeks specific information from documents"
**Result**: Uses RAG mode to search through uploaded contracts

### Example 3: Conversational Query
**User Input**: "How's your day going?"
**AI Analysis**:
- Detected: Casual conversation
- Recommended Mode: Basic
- Confidence: 92%
- Reasoning: "Conversational query not requiring specific data sources"
**Result**: Uses Basic chat mode for natural conversation

### Example 4: Summary Request
**User Input**: "Summarize the main findings from our research"
**AI Analysis**:
- Detected: Summarization request
- Recommended Mode: Summarize
- Confidence: 90%
- Reasoning: "Query explicitly requests content summarization"
**Result**: Switches to Summarize mode and processes research data

## Configuration and Setup

### 1. Backend Requirements
- Ollama LLM properly configured and running
- Query router service registered in dependency injection
- API endpoints exposed through FastAPI

### 2. Frontend Integration
- `analyzeQuery` API function implemented
- Enhanced message handling with AI routing
- Notification components for user feedback

### 3. Environment Variables
No additional environment variables required - the system uses existing Ollama configuration.

## Benefits

### For Users
- **Effortless Experience**: No manual mode switching required
- **Faster Results**: Queries automatically routed to optimal processing
- **Better Accuracy**: Right mode chosen for each query type
- **Transparency**: See why certain modes were recommended

### For Developers
- **Extensible Architecture**: Easy to add new modes and routing logic
- **Maintainable Code**: Clear separation between analysis and processing
- **Robust Error Handling**: Graceful fallbacks when analysis fails
- **Monitoring Friendly**: Detailed logging and confidence metrics

## Future Enhancements

### Potential Improvements
1. **Machine Learning**: Train models on user interaction patterns
2. **Personalization**: Learn individual user preferences
3. **Batch Analysis**: Analyze multiple queries simultaneously
4. **Advanced Context**: Consider more sophisticated conversation context
5. **Multi-language Support**: Extend to non-English queries
6. **Performance Optimization**: Cache common query patterns

### Integration Opportunities
1. **User Feedback Loop**: Allow users to correct routing decisions
2. **Analytics Dashboard**: Monitor routing accuracy and patterns
3. **A/B Testing**: Compare different routing strategies
4. **External APIs**: Integrate with specialized analysis services

## Troubleshooting

### Common Issues

#### 1. Analysis Errors
**Symptom**: Queries default to RAG mode
**Cause**: Ollama LLM not responding or configuration issues
**Solution**: Check Ollama service status and API connectivity

#### 2. Incorrect Routing
**Symptom**: Queries routed to wrong modes
**Cause**: LLM prompt needs refinement or training data issues
**Solution**: Review and update analysis prompts, add more examples

#### 3. Performance Issues
**Symptom**: Slow query processing
**Cause**: LLM analysis taking too long
**Solution**: Optimize prompts, consider caching, or use faster models

### Debugging Tips

1. **Check Console Logs**: Analysis results are logged for debugging
2. **Monitor API Calls**: Verify `/v1/query/analyze` endpoint responses
3. **Test Manually**: Use API directly to test analysis logic
4. **Review Notifications**: User notifications show reasoning for debugging

## Conclusion

The intelligent query routing system significantly enhances the QGPT user experience by automatically directing queries to the most appropriate processing modes. This reduces cognitive load on users while improving response quality and system efficiency.

The system is designed to be extensible, maintainable, and transparent, providing a solid foundation for future AI-powered enhancements to the QGPT platform.
