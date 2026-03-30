# Multi-Agent Mechanic Workflow - Usage Guide

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

### 3. Run the System

```bash
# Run with sample data
python src/main.py

# Run tests
python tests/test_workflow.py
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      MAIN WORKFLOW                          │
│                    (Router at top)                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │    OBD2 ORCHESTRATION LAYER           │
        ├───────────────────────────────────────┤
        │  1. Load User Memory                  │
        │  2. OBD2 Writer Agent                 │
        │     - Retrieve from RAG               │
        │     - Reflect on quality              │
        │     - Retry with web search           │
        │  3. Observation Agent                 │
        │     - Review analysis                 │
        │     - Request revisions               │
        │  4. Save Analysis                     │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   WRITER ORCHESTRATION LAYER          │
        ├───────────────────────────────────────┤
        │  1. Product Research Agent            │
        │     - Extract product needs           │
        │     - Search web for products         │
        │  2. Technical Writer Agent            │
        │     - Combine analysis + products     │
        │     - Create detailed report          │
        │  3. Formatter Agent                   │
        │     - Convert to user-friendly        │
        │     - Add visual formatting           │
        │  4. Save Final Report                 │
        └───────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────┐
                    │    END    │
                    └───────────┘
```

## Key Features

### 1. Retrieve-Reflect-Retry Pattern

The OBD2 Writer Agent implements this pattern:

- **Retrieve**: Query the RAG knowledge base for relevant automotive information
- **Reflect**: Evaluate if retrieved information is sufficient (score threshold: 0.7)
- **Retry**: If insufficient, reformulate query or trigger web search (max 3 cycles)

### 2. Writer-Observer Loop

The OBD2 analysis goes through a review cycle:

- Writer Agent creates analysis draft
- Observer Agent reviews for completeness and accuracy
- If revisions needed, loops back to Writer (max 3 revisions)
- Ensures high-quality technical analysis

### 3. Memory Management

Per-user memory includes:
- Car metadata (model, year, mileage, VIN)
- Conversation history (last 10 interactions)
- Stored in JSON files under `data/users/{user_id}/`

### 4. Product Research

The Product Research Agent:
- Extracts needed parts from OBD2 analysis (e.g., "TPMS sensor", "tires")
- Searches web for compatible products
- Returns structured recommendations with links

## Input Format

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
      },
      "engine_temp": 195,
      "oil_pressure": 40,
      "battery_voltage": 12.6
    },
    "freeze_frame_data": {
      "vehicle_speed": 45,
      "engine_rpm": 2100,
      "fuel_level": 65
    }
  }
}
```

## Output

The system generates a comprehensive diagnostic report with:

1. **Executive Summary** - Brief overview of issues
2. **Detailed Findings** - Technical analysis of each problem
3. **Root Cause Analysis** - Why issues occurred
4. **Recommended Actions** - Prioritized repair steps
5. **Product Recommendations** - Compatible parts with links and pricing
6. **Cost Estimates** - Expected repair costs
7. **Safety Information** - Critical safety concerns

Reports are saved to `output/diagnostic_report_{user_id}_{timestamp}.txt`

## Configuration

Edit `config.py` to customize:

```python
# Model selection per agent
AGENT_MODELS = {
    "obd2_writer": {"model": "gpt-4-turbo-preview", "temperature": 0.3},
    "obd2_observer": {"model": "gpt-4-turbo-preview", "temperature": 0.2},
    # ... more agents
}

# Retrieve-Reflect-Retry settings
MAX_RETRY_CYCLES = 3
REFLECTION_SCORE_THRESHOLD = 0.7

# RAG settings
RAG_TOP_K = 5
RAG_CHUNK_SIZE = 1000
```

## Extending the System

### Adding New Agents

1. Create agent file in `src/agents/`
2. Implement agent class with `execute()` method
3. Create node function for LangGraph
4. Add to orchestration layer

Example:

```python
class CostEstimatorAgent:
    def execute(self, state):
        # Your logic here
        return {"estimated_cost": 250.0}

def cost_estimator_node(state):
    agent = CostEstimatorAgent()
    return agent.execute(state)
```

### Adding New Tools

1. Create tool file in `src/tools/`
2. Use `@tool` decorator for LangChain integration
3. Import and use in agents

### Adding to Knowledge Base

```python
from src.rag.knowledge_base import knowledge_base

# Add documents
texts = ["Your automotive knowledge here..."]
metadatas = [{"type": "repair", "category": "brakes"}]
knowledge_base.add_texts(texts, metadatas)
```

## Troubleshooting

### Issue: "No documents retrieved from knowledge base"

**Solution**: The knowledge base initializes automatically. If issues persist:

```python
from src.rag.knowledge_base import knowledge_base
knowledge_base.initialize_with_sample_data()
```

### Issue: "OPENAI_API_KEY not set"

**Solution**: Ensure `.env` file exists with valid API key:

```bash
echo "OPENAI_API_KEY=your_key" > .env
```

### Issue: Web search not working

**Solution**: Check Tavily API key is set. The system will still work with RAG only.

## Performance Optimization

1. **Caching**: Common OBD2 codes are cached after first lookup
2. **Batch Processing**: Multiple codes processed together
3. **Selective Web Search**: Only triggers when RAG is insufficient
4. **Model Selection**: Use GPT-3.5 for simpler tasks, GPT-4 for complex analysis

## Best Practices

1. **Always provide complete OBD2 data** including sensor readings
2. **Update car metadata** for accurate product recommendations
3. **Review reports** before sending to customers
4. **Expand knowledge base** with your own automotive data
5. **Monitor API costs** - adjust models and retry limits as needed

## Advanced Usage

### Custom Workflow

```python
from src.graph.main_graph import main_workflow

# Prepare custom input
input_data = {
    "user_id": "custom_user",
    "car_metadata": {...},
    "obd2_data": {...}
}

# Run workflow
result = main_workflow.invoke(input_data)

# Access results
final_report = result["final_report"]
obd2_analysis = result["obd2_analysis"]
```

### Streaming Output

```python
# Stream workflow events
for event in main_workflow.stream(input_data):
    print(event)
```

### Accessing Sub-Orchestrations

```python
from src.orchestrations.obd2_orchestration import obd2_orchestration
from src.orchestrations.writer_orchestration import writer_orchestration

# Run OBD2 analysis only
obd2_result = obd2_orchestration.invoke(obd2_state)

# Run writer with existing analysis
writer_result = writer_orchestration.invoke(writer_state)
```

## Support

For issues or questions:
1. Check this guide
2. Review test cases in `tests/test_workflow.py`
3. Examine sample data in `data/sample_obd2_data.json`
4. Review the plan in `multi-agent.plan.md`

