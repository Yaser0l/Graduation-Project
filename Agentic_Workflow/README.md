# Multi-Agent Mechanic Workflow System

An intelligent multi-agent system built with **LangGraph** and **LangChain** that analyzes OBD2 diagnostic data and provides comprehensive automotive repair recommendations with product suggestions.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-latest-green.svg)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange.svg)](https://www.langchain.com/langgraph)

## Key Features

- **Intelligent OBD2 Analysis**: Analyzes diagnostic trouble codes with automotive knowledge base context
- **Retrieve-Reflect-Retry Pattern**: Ensures high-quality analysis through iterative refinement
- **User Memory Management**: Maintains car metadata and conversation history per user
- **Product Recommendations**: Automatically searches for compatible parts with pricing and links
- **Web-Enhanced Search**: Falls back to Tavily web search when knowledge base is insufficient
- **Quality Control**: Observer agent reviews all analysis for accuracy and completeness

## Architecture

The system features a hierarchical multi-agent workflow with two main orchestration layers:

```
┌─────────────────────────────────────────────┐
│           ROUTER (Entry Point)              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│      OBD2 ORCHESTRATION LAYER               │
│  ┌────────────────────────────────────┐     │
│  │  1. Load User Memory               │     │
│  │  2. Writer Agent (R³ Pattern)      │     │
│  │     • Retrieve from RAG            │     │
│  │     • Reflect on quality           │     │
│  │     • Retry with web search        │     │
│  │  3. Observer Agent                 │     │
│  │     • Review & approve/revise      │     │
│  │  4. Save Analysis                  │     │
│  └────────────────────────────────────┘     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│     WRITER ORCHESTRATION LAYER              │
│  ┌────────────────────────────────────┐     │
│  │  1. Product Research Agent         │     │
│  │     • Extract needed parts         │     │
│  │     • Search web for products      │     │
│  │  2. Technical Writer Agent         │     │
│  │     • Combine analysis + products  │     │
│  │  3. Formatter Agent                │     │
│  │     • User-friendly formatting     │     │
│  │  4. Save Final Report              │     │
│  └────────────────────────────────────┘     │
└─────────────────────────────────────────────┘
                    ↓
               Final Report
```

## Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key
- Tavily API key (optional, for web search)

### Installation

1. **Clone and navigate to the project:**
```bash
cd F_Project
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=sk-your-openai-key-here
TAVILY_API_KEY=tvly-your-tavily-key-here
```

4. **Run the system:**
```bash
python src/main.py
```

### Running Tests

```bash
python tests/test_workflow.py
```

## Usage Example

### Input Format

```json
{
  "user_id": "user_001",
  "car_metadata": {
    "car_name": "Toyota Camry",
    "car_model": "SE",
    "year": 2020,
    "mileage": 45000,
    "vin": "1HGBH41JXMN109186"
  },
  "obd2_data": {
    "diagnostic_codes": [
      {
        "code": "C0750",
        "description": "Tire Pressure Monitor Sensor Battery Low",
        "system": "Chassis"
      }
    ],
    "sensor_readings": {
      "tire_pressure": {
        "front_left": 28,
        "front_right": 29,
        "rear_left": 27,
        "rear_right": 28,
        "unit": "PSI",
        "recommended": 35
      }
    }
  }
}
```

### Output

The system generates a comprehensive diagnostic report including:

- **Executive Summary** - Brief overview of findings
- **Detailed Analysis** - Technical breakdown of each issue
- **Root Causes** - Why the problems occurred
- **Recommended Actions** - Prioritized repair steps
- **Product Recommendations** - Compatible parts with links
- **Cost Estimates** - Expected repair costs
- **Safety Information** - Critical warnings

Reports are automatically saved to `output/diagnostic_report_{user_id}_{timestamp}.txt`

## Project Structure

```
F_Project/
├── src/
│   ├── agents/              # Individual agent implementations
│   │   ├── obd2_writer.py
│   │   ├── obd2_observer.py
│   │   ├── product_researcher.py
│   │   ├── technical_writer.py
│   │   └── formatter.py
│   ├── orchestrations/      # Orchestration layers
│   │   ├── obd2_orchestration.py
│   │   └── writer_orchestration.py
│   ├── states/              # Pydantic state definitions
│   │   ├── obd2_state.py
│   │   └── writer_state.py
│   ├── tools/               # Tool implementations
│   │   ├── rag_tool.py      # RAG retrieval
│   │   ├── tavily_tool.py   # Web search
│   │   ├── memory_tools.py  # Memory management
│   │   └── obd2_parser.py   # OBD2 parsing
│   ├── memory/              # User memory system
│   │   └── user_memory.py
│   ├── rag/                 # RAG knowledge base
│   │   └── knowledge_base.py
│   ├── graph/               # LangGraph workflow
│   │   └── main_graph.py
│   ├── router.py            # Request router
│   └── main.py              # Entry point
├── data/
│   ├── users/               # User profiles and history (auto-created)
│   ├── chroma_db/           # Vector store (auto-created)
│   └── sample_obd2_data.json
├── tests/
│   └── test_workflow.py     # Comprehensive test suite
├── output/                  # Generated reports (auto-created)
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
├── USAGE_GUIDE.md          # Detailed usage guide
└── README.md               # This file
```

## Configuration

Edit `config.py` to customize:

- **Model Selection**: Choose GPT-4 or GPT-3.5 per agent
- **Temperature Settings**: Control creativity vs. consistency
- **Retry Limits**: Max cycles for Retrieve-Reflect-Retry
- **RAG Parameters**: Chunk size, overlap, top-k results
- **Reflection Threshold**: Quality score threshold (default: 0.7)

## Testing

The test suite includes:

- Memory system validation
- RAG retrieval testing
- Input validation checks
- Full workflow integration tests
- Custom scenario testing

Run tests:
```bash
python tests/test_workflow.py
```

## Documentation

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Comprehensive usage guide with examples
- **[multi-agent.plan.md](multi-agent.plan.md)** - Original architecture plan and design decisions

## Technologies Used

- **[LangGraph](https://www.langchain.com/langgraph)** - Multi-agent workflow orchestration
- **[LangChain](https://www.langchain.com/)** - Agent framework and tools
- **[OpenAI GPT-4/3.5](https://openai.com/)** - Language models
- **[Chroma](https://www.trychroma.com/)** - Vector database for RAG
- **[Tavily](https://tavily.com/)** - Web search API
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation

## Core Patterns Implemented

### 1. Retrieve-Reflect-Retry (R³)

The OBD2 Writer Agent uses this pattern for knowledge retrieval:

1. **Retrieve**: Query vector database for relevant information
2. **Reflect**: Evaluate quality of retrieved content (score > 0.7)
3. **Retry**: If insufficient, reformulate query or use web search

### 2. Writer-Observer Loop

Quality control through iterative refinement:

1. Writer creates analysis draft
2. Observer reviews for completeness and accuracy
3. If revisions needed, loops back to Writer
4. Maximum 3 revision cycles to prevent infinite loops

### 3. Memory-Augmented Agents

Each user has persistent memory:

- Car metadata (model, year, mileage, VIN)
- Conversation history (last 10 interactions)
- Stored locally in JSON format

## Advanced Usage

### Custom Input

```python
from src.main import run_workflow

custom_data = {
    "user_id": "user_002",
    "car_metadata": {...},
    "obd2_data": {...}
}

result = run_workflow(custom_data)
print(result["final_report"])
```

### Accessing Sub-Orchestrations

```python
from src.orchestrations.obd2_orchestration import obd2_orchestration

# Run only OBD2 analysis
result = obd2_orchestration.invoke(obd2_state)
```

### Extending the Knowledge Base

```python
from src.rag.knowledge_base import knowledge_base

texts = ["Your automotive knowledge..."]
metadatas = [{"type": "repair", "category": "engine"}]
knowledge_base.add_texts(texts, metadatas)
```

## Contributing

Suggestions for improvements:

1. Add more agents (cost estimator, safety checker)
2. Expand knowledge base with more automotive data
3. Add support for more OBD2 code types
4. Integrate with actual OBD2 hardware readers
5. Add visualization of affected systems

## License

MIT

## Acknowledgments

Built using the powerful LangGraph and LangChain frameworks for production-ready multi-agent systems.
