<!-- 36cebede-ce69-4604-b465-00b36644f60f 5fe0cea8-1c1a-4d03-a37d-5be9573fad8e -->
# Multi-Agent Mechanic Workflow System

## Architecture Overview

The system will have a hierarchical structure:

- **Router Node** (top level) → routes to appropriate orchestration
- **OBD2 Orchestration** → analyzes diagnostic data with sub-agents
- **Writer Orchestration** → produces user-facing reports with product recommendations

## Key Technical Decisions

- **LLM**: OpenAI (GPT-4/GPT-3.5)
- **Vector Store**: Chroma (local, simple setup)
- **Memory**: JSON file storage for user profiles and chat history
- **Web Search**: Tavily API for real-time information
- **Framework**: LangGraph for workflow orchestration

## Implementation Structure

### 1. Project Setup & Dependencies

Create `requirements.txt` with:

- `langgraph`, `langchain`, `langchain-openai`, `langchain-community`
- `chromadb` (vector store)
- `tavily-python` (web search)
- `pydantic` (state management)
- `python-dotenv` (environment variables)

### 2. Pydantic State Definitions

**OBD2 State** (`src/states/obd2_state.py`):

```python
class CarMetadata(BaseModel):
    car_model: str
    car_name: str
    mileage: int
    year: int
    vin: Optional[str]

class OBD2State(TypedDict):
    user_id: str
    car_metadata: CarMetadata
    obd2_data: Dict[str, Any]  # Raw OBD2 codes and sensor data
    retrieved_context: List[str]  # From RAG
    web_search_results: Optional[List[str]]
    analysis_draft: Optional[str]  # Writer agent output
    analysis_review: Optional[str]  # Observation agent feedback
    final_analysis: Optional[str]  # Approved analysis
    reflection_count: int  # Track Retrieve-Reflect-Retry cycles
    messages: Annotated[List[BaseMessage], add_messages]
```

**Writer State** (`src/states/writer_state.py`):

```python
class WriterState(TypedDict):
    user_id: str
    car_metadata: CarMetadata
    obd2_analysis: str  # Input from OBD2 orchestration
    product_recommendations: Optional[List[Dict]]  # Web search results
    draft_report: Optional[str]
    technical_review: Optional[str]
    user_friendly_report: Optional[str]
    final_report: str
    messages: Annotated[List[BaseMessage], add_messages]
```

### 3. Memory Management System

**User Memory Manager** (`src/memory/user_memory.py`):

- Store user profiles in `data/users/{user_id}/profile.json`
- Store conversation history in `data/users/{user_id}/history.json`
- Implement methods:
  - `load_user_profile(user_id)` → returns CarMetadata
  - `save_user_profile(user_id, metadata)`
  - `load_conversation_history(user_id, limit=10)`
  - `append_to_history(user_id, interaction)`

### 4. RAG System Setup

**Knowledge Base** (`src/rag/knowledge_base.py`):

- Initialize Chroma vector store in `data/chroma_db/`
- Embed automotive repair manuals, OBD2 code definitions, common fixes
- Implement Retrieve-Reflect-Retry pattern:
  - **Retrieve**: Query vector store with OBD2 codes
  - **Reflect**: Agent evaluates relevance (score threshold)
  - **Retry**: If insufficient, reformulate query or trigger web search

**Documents to Index**:

- OBD2 diagnostic trouble codes (DTC) database
- Common repair procedures
- Parts compatibility information

### 5. OBD2 Orchestration Layer

**Main Orchestration** (`src/orchestrations/obd2_orchestration.py`):

**Sub-Agents**:

1. **Writer Agent** (`src/agents/obd2_writer.py`):

   - Takes OBD2 codes + retrieved context
   - Generates technical analysis draft
   - Tool: RAG retrieval with reflection
   - Tool: Tavily web search (fallback)

2. **Observation Agent** (`src/agents/obd2_observer.py`):

   - Reviews writer's draft for:
     - Technical accuracy
     - Completeness (all codes addressed)
     - Clarity of diagnosis
   - Returns: approval or revision requests

**Flow**:

```
Load User Memory → Parse OBD2 Data → Writer Agent (Retrieve-Reflect-Retry) 
→ Observation Agent → [Loop if revisions needed] → Save to State
```

**Retrieve-Reflect-Retry Implementation**:

- Max 3 retry cycles
- Reflection criteria: relevance score > 0.7, context completeness
- If RAG fails twice, trigger Tavily search

### 6. Writer Orchestration Layer

**Main Orchestration** (`src/orchestrations/writer_orchestration.py`):

**Sub-Agents**:

1. **Product Research Agent** (`src/agents/product_researcher.py`):

   - Extracts problem components from OBD2 analysis (e.g., "tires", "brake pads")
   - Uses Tavily to search for:
     - Compatible products (e.g., tire models for specific car)
     - Pricing information
     - Vendor links
   - Returns structured product recommendations

2. **Technical Writer Agent** (`src/agents/technical_writer.py`):

   - Combines OBD2 analysis + product recommendations
   - Generates detailed technical section

3. **User-Friendly Formatter Agent** (`src/agents/formatter.py`):

   - Translates technical jargon into plain language
   - Structures report with sections:
     - Summary (what's wrong)
     - Detailed findings
     - Recommended actions
     - Product recommendations with links
     - Estimated costs

**Flow**:

```
Receive OBD2 Analysis → Product Research Agent (Tavily) 
→ Technical Writer → Formatter → Final Report
```

### 7. Router Implementation

**Router Node** (`src/router.py`):

- Analyzes initial user input
- Routes to:
  - OBD2 Orchestration (if OBD2 data present)
  - Writer Orchestration (if analysis already exists)
  - Error handling (if invalid input)

### 8. LangGraph Workflow

**Main Graph** (`src/graph/main_graph.py`):

```
START → Router → OBD2_Orchestration → Writer_Orchestration → END
```

**Conditional Edges**:

- OBD2 Writer → Observer: Check if approved
- Observer → Writer: If revisions needed (max 3 loops)
- Retrieve → Reflect: Check context quality
- Reflect → Retry: If quality insufficient

### 9. Tool Definitions

**Tools Needed**:

1. **RAG Retrieval Tool** (`src/tools/rag_tool.py`):

   - Query Chroma vector store
   - Return top-k relevant documents

2. **Tavily Search Tool** (`src/tools/tavily_tool.py`):

   - Web search for:
     - Technical information (OBD2 orchestration)
     - Product recommendations (Writer orchestration)
   - Parse and structure results

3. **Memory Tools** (`src/tools/memory_tools.py`):

   - Load/save user profile
   - Retrieve conversation history

4. **OBD2 Parser Tool** (`src/tools/obd2_parser.py`):

   - Parse raw OBD2 JSON input
   - Extract diagnostic codes, sensor readings
   - Validate data format

### 10. Configuration & Environment

**`.env` file**:

```
OPENAI_API_KEY=your_key
TAVILY_API_KEY=your_key
CHROMA_DB_PATH=./data/chroma_db
USER_DATA_PATH=./data/users
```

**`config.py`**:

- Model names (gpt-4-turbo, gpt-3.5-turbo)
- Temperature settings per agent
- Retry limits
- Reflection thresholds

### 11. Entry Point & Testing

**Main Entry** (`src/main.py`):

- Initialize graph
- Accept user input (user_id + OBD2 data)
- Stream output
- Save results to memory

**Test Script** (`tests/test_workflow.py`):

- Sample OBD2 data (tire pressure issue)
- Mock user profile
- Verify full workflow execution

## File Structure

```
F_Project/
├── .env
├── .gitignore
├── requirements.txt
├── README.md
├── config.py
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── router.py
│   ├── states/
│   │   ├── obd2_state.py
│   │   └── writer_state.py
│   ├── orchestrations/
│   │   ├── obd2_orchestration.py
│   │   └── writer_orchestration.py
│   ├── agents/
│   │   ├── obd2_writer.py
│   │   ├── obd2_observer.py
│   │   ├── product_researcher.py
│   │   ├── technical_writer.py
│   │   └── formatter.py
│   ├── tools/
│   │   ├── rag_tool.py
│   │   ├── tavily_tool.py
│   │   ├── memory_tools.py
│   │   └── obd2_parser.py
│   ├── memory/
│   │   └── user_memory.py
│   ├── rag/
│   │   └── knowledge_base.py
│   └── graph/
│       └── main_graph.py
├── data/
│   ├── users/
│   ├── chroma_db/
│   └── sample_obd2_data.json
└── tests/
    └── test_workflow.py
```

## Improvements & Suggestions

1. **Additional Agent Idea**: Add a **Cost Estimator Agent** in Writer Orchestration to provide repair cost estimates based on labor rates and part prices

2. **Safety Check Agent**: In OBD2 Orchestration, add an agent that flags critical safety issues (brake failure, airbag codes) for immediate attention

3. **Feedback Loop**: After user receives report, capture feedback to improve RAG knowledge base

4. **Caching**: Implement caching for common OBD2 codes to reduce API calls

5. **Visualization**: Generate diagrams showing which car systems are affected

## Next Steps

Once approved, implementation will proceed in this order:

1. Project structure and dependencies
2. State definitions and memory system
3. RAG setup with sample automotive data
4. Individual agents with tools
5. Orchestration layers
6. Router and main graph
7. Testing with sample data
8. Documentation and examples

### To-dos

- [ ] Create project structure, requirements.txt, config files, and environment setup
- [ ] Implement Pydantic state definitions for OBD2State and WriterState
- [ ] Build user memory management system with JSON storage for profiles and history
- [ ] Initialize Chroma vector store and create knowledge base with automotive data
- [ ] Implement all tools: RAG retrieval, Tavily search, memory tools, OBD2 parser
- [ ] Create OBD2 Writer and Observation agents with Retrieve-Reflect-Retry pattern
- [ ] Create Product Researcher, Technical Writer, and Formatter agents
- [ ] Build OBD2 orchestration layer connecting writer and observer agents
- [ ] Build Writer orchestration layer with product research and report generation
- [ ] Implement router and main LangGraph workflow connecting all components
- [ ] Create main.py entry point with user input handling and output streaming
- [ ] Write test script with sample OBD2 data and verify end-to-end workflow