# Multi-Agent Mechanic Workflow - Architecture Diagram

## System Architecture

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                      INPUT: OBD2 Data + User Info              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        MAIN WORKFLOW                           ┃
┃                                                                 ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  1. Initialize & Validate Input                         │  ┃
┃  │     • Check required fields                             │  ┃
┃  │     • Validate OBD2 data structure                      │  ┃
┃  │     • Route to appropriate orchestration                │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃               OBD2 ORCHESTRATION LAYER                         ┃
┃                                                                 ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 1: Load User Memory                               │  ┃
┃  │  ┌──────────────────────────────────────────────────┐   │  ┃
┃  │  │ • Load user profile (car metadata)               │   │  ┃
┃  │  │ • Load conversation history (last 10)            │   │  ┃
┃  │  │ • Get user context                                │   │  ┃
┃  │  └──────────────────────────────────────────────────┘   │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┃                                ↓                               ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 2: OBD2 Writer Agent (R³ Pattern)                │  ┃
┃  │  ┌──────────────────────────────────────────────────┐   │  ┃
┃  │  │ RETRIEVE: Query RAG knowledge base              │   │  ┃
┃  │  │   • Extract diagnostic codes                     │   │  ┃
┃  │  │   • Query Chroma vector store                    │   │  ┃
┃  │  │   • Get top-k relevant documents                 │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ REFLECT: Evaluate retrieval quality             │   │  ┃
┃  │  │   • Calculate relevance scores                   │   │  ┃
┃  │  │   • Check threshold (>0.7)                       │   │  ┃
┃  │  │   • Assess completeness                          │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ RETRY: Fallback if needed                        │   │  ┃
┃  │  │   • Reformulate query                            │   │  ┃
┃  │  │   • Trigger Tavily web search                    │   │  ┃
┃  │  │   • Max 3 cycles                                 │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ WRITE: Generate technical analysis               │   │  ┃
┃  │  │   • Use GPT-4 with retrieved context            │   │  ┃
┃  │  │   • Include car history                          │   │  ┃
┃  │  │   • Technical depth & accuracy                   │   │  ┃
┃  │  └──────────────────────────────────────────────────┘   │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┃                                ↓                               ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 3: OBD2 Observer Agent (Quality Control)         │  ┃
┃  │  ┌──────────────────────────────────────────────────┐   │  ┃
┃  │  │ REVIEW:                                          │   │  ┃
┃  │  │   • Completeness (all codes addressed?)          │   │  ┃
┃  │  │   • Technical accuracy                           │   │  ┃
┃  │  │   • Clarity of explanation                       │   │  ┃
┃  │  │   • Actionable recommendations                   │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ DECISION:                                        │   │  ┃
┃  │  │   • APPROVED → Continue to save                  │   │  ┃
┃  │  │   • NEEDS_REVISION → Back to Writer             │   │  ┃
┃  │  │   • Max 3 revision cycles                        │   │  ┃
┃  │  └──────────────────────────────────────────────────┘   │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┃                    ↓                    ↑                      ┃
┃                    ↓                    ↑ (if revisions)       ┃
┃                    ↓ (if approved)      ↑                      ┃
┃                    ↓────────────────────┘                      ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 4: Save Analysis to Memory                        │  ┃
┃  │  • Store in conversation history                        │  ┃
┃  │  • Link to user profile                                 │  ┃
┃  │  • Prepare for Writer orchestration                     │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                ↓
                    Final OBD2 Analysis
                                ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃              WRITER ORCHESTRATION LAYER                        ┃
┃                                                                 ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 1: Product Research Agent                         │  ┃
┃  │  ┌──────────────────────────────────────────────────┐   │  ┃
┃  │  │ EXTRACT: Identify needed parts                   │   │  ┃
┃  │  │   • Parse OBD2 analysis                          │   │  ┃
┃  │  │   • Use LLM to extract product types             │   │  ┃
┃  │  │   • E.g., "TPMS sensor", "tires", "brake pads"  │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ SEARCH: Find products                            │   │  ┃
┃  │  │   • Tavily web search                            │   │  ┃
┃  │  │   • Use car metadata for compatibility           │   │  ┃
┃  │  │   • Get pricing, links, vendors                  │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ STRUCTURE: Format recommendations                │   │  ┃
┃  │  │   • Product name, type, price                    │   │  ┃
┃  │  │   • Compatibility notes                          │   │  ┃
┃  │  │   • Purchase links                               │   │  ┃
┃  │  └──────────────────────────────────────────────────┘   │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┃                                ↓                               ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 2: Technical Writer Agent                         │  ┃
┃  │  ┌──────────────────────────────────────────────────┐   │  ┃
┃  │  │ COMBINE:                                         │   │  ┃
┃  │  │   • OBD2 technical analysis                      │   │  ┃
┃  │  │   • Product recommendations                      │   │  ┃
┃  │  │   • Car metadata context                         │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ WRITE SECTIONS:                                  │   │  ┃
┃  │  │   • Executive Summary                            │   │  ┃
┃  │  │   • Detailed Findings                            │   │  ┃
┃  │  │   • Root Cause Analysis                          │   │  ┃
┃  │  │   • Recommended Actions                          │   │  ┃
┃  │  │   • Product Recommendations                      │   │  ┃
┃  │  │   • Cost Considerations                          │   │  ┃
┃  │  │   • Safety Notes                                 │   │  ┃
┃  │  └──────────────────────────────────────────────────┘   │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┃                                ↓                               ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 3: Formatter Agent                                │  ┃
┃  │  ┌──────────────────────────────────────────────────┐   │  ┃
┃  │  │ FORMAT:                                          │   │  ┃
┃  │  │   • Convert technical jargon to plain language   │   │  ┃
┃  │  │   • Add visual structure (boxes, sections)       │   │  ┃
┃  │  │   • Use emojis for clarity                       │   │  ┃
┃  │  │   • Highlight important info                     │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ STRUCTURE:                                       │   │  ┃
┃  │  │   • Clear headers and sections                   │   │  ┃
┃  │  │   • Bullet points for readability                │   │  ┃
┃  │  │   • Priority levels (urgent, soon, later)        │   │  ┃
┃  │  │   • Next steps checklist                         │   │  ┃
┃  │  │                                                   │   │  ┃
┃  │  │ TONE:                                            │   │  ┃
┃  │  │   • Friendly and helpful                         │   │  ┃
┃  │  │   • Clear and actionable                         │   │  ┃
┃  │  │   • Empathetic to user concerns                  │   │  ┃
┃  │  └──────────────────────────────────────────────────┘   │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┃                                ↓                               ┃
┃  ┌─────────────────────────────────────────────────────────┐  ┃
┃  │  Step 4: Save Final Report                              │  ┃
┃  │  • Store in conversation history                        │  ┃
┃  │  • Save to file (with timestamp)                        │  ┃
┃  │  • Return to user                                       │  ┃
┃  └─────────────────────────────────────────────────────────┘  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    OUTPUT: Final Report                        ┃
┃                                                                 ┃
┃  • User-friendly diagnostic report                             ┃
┃  • Product recommendations with links                          ┃
┃  • Actionable next steps                                       ┃
┃  • Saved to file and memory                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Data Flow

```
User Input
    ↓
┌─────────────────────┐
│   user_id           │
│   car_metadata      │
│   obd2_data         │
└─────────────────────┘
    ↓
[Router & Validation]
    ↓
┌─────────────────────┐
│   OBD2State         │
├─────────────────────┤
│ • user_id           │
│ • car_metadata      │
│ • obd2_data         │
│ • retrieved_context │
│ • analysis_draft    │
│ • analysis_review   │
│ • final_analysis    │
│ • reflection_count  │
│ • revision_count    │
└─────────────────────┘
    ↓
[OBD2 Orchestration]
    ↓
┌─────────────────────┐
│   WriterState       │
├─────────────────────┤
│ • user_id           │
│ • car_metadata      │
│ • obd2_analysis     │
│ • products          │
│ • draft_report      │
│ • final_report      │
└─────────────────────┘
    ↓
[Writer Orchestration]
    ↓
┌─────────────────────┐
│   Final Output      │
├─────────────────────┤
│ • final_report      │
│ • saved to file     │
│ • saved to memory   │
└─────────────────────┘
```

## Component Interaction

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Agents     │◄────►│    Tools     │◄────►│   External   │
│              │      │              │      │   Services   │
│ • OBD2       │      │ • RAG        │      │ • OpenAI     │
│   Writer     │      │ • Memory     │      │ • Tavily     │
│ • OBD2       │      │ • OBD2       │      │ • Chroma     │
│   Observer   │      │   Parser     │      │              │
│ • Product    │      │ • Web Search │      │              │
│   Researcher │      │              │      │              │
│ • Technical  │      │              │      │              │
│   Writer     │      │              │      │              │
│ • Formatter  │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
       ↕                     ↕                      ↕
┌─────────────────────────────────────────────────────────┐
│              LangGraph State Management                 │
└─────────────────────────────────────────────────────────┘
       ↕                     ↕                      ↕
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    Memory    │      │     RAG      │      │   Reports    │
│   System     │      │  Knowledge   │      │   Output     │
│              │      │     Base     │      │              │
│ data/users/  │      │data/chroma_db│      │   output/    │
└──────────────┘      └──────────────┘      └──────────────┘
```

## Agent Decision Flow

```
                    ┌─── OBD2 Writer Agent ───┐
                    │                          │
                    │  1. Retrieve from RAG    │
                    │         ↓                │
                    │  2. Score < 0.7?         │
                    │         ↓                │
                    │    ┌────┴────┐           │
                    │   YES       NO           │
                    │    ↓         ↓           │
                    │  Retry    Continue       │
                    │   Web     with RAG       │
                    │  Search   context        │
                    │    ↓         ↓           │
                    │    └────┬────┘           │
                    │         ↓                │
                    │  3. Generate Analysis    │
                    └──────────────────────────┘
                             ↓
                    ┌─── OBD2 Observer ───┐
                    │                      │
                    │  1. Review Analysis  │
                    │         ↓            │
                    │  2. Approved?        │
                    │         ↓            │
                    │    ┌────┴────┐       │
                    │   YES       NO       │
                    │    ↓         ↓       │
                    │ Continue  Request    │
                    │           Revision   │
                    │    ↓         ↓       │
                    │    │     ┌───┘       │
                    │    │     │           │
                    │    │     └→ Writer   │
                    │    │      (max 3x)   │
                    │    ↓                 │
                    │  Finalize            │
                    └──────────────────────┘
```

## Technology Stack Layers

```
┌─────────────────────────────────────────────┐
│          Application Layer                  │
│  • Main workflow                            │
│  • Orchestrations                           │
│  • Agents                                   │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│          Framework Layer                    │
│  • LangGraph (workflow orchestration)       │
│  • LangChain (agent framework)              │
│  • Pydantic (data validation)               │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│          Service Layer                      │
│  • OpenAI GPT-4/3.5 (LLM)                   │
│  • Tavily (web search)                      │
│  • Chroma (vector store)                    │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│          Storage Layer                      │
│  • JSON (user memory)                       │
│  • Chroma DB (vector embeddings)            │
│  • Text files (reports)                     │
└─────────────────────────────────────────────┘
```

## Key Patterns

### 1. Retrieve-Reflect-Retry (R³)
```
Retrieve → Reflect → Score >= 0.7? → Yes → Continue
              ↑            ↓
              |           No
              |            ↓
              └───── Web Search
                    (Retry #N)
```

### 2. Writer-Observer Loop
```
Writer → Draft → Observer → Approved? → Yes → Continue
   ↑                            ↓
   |                           No
   |                            ↓
   └──────────── Revise ←──────┘
              (max 3 cycles)
```

### 3. Memory-Augmented Processing
```
Input → Load Memory → Process with Context → Save Results → Output
         ↑                                        ↓
         └────────────────────────────────────────┘
                   (persistent storage)
```

This architecture ensures high-quality automotive diagnostics through multi-agent collaboration, quality control loops, and intelligent information retrieval!

