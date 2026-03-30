"""Main entry point for the Multi-Agent Mechanic Workflow."""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from src.graph.main_graph import main_workflow
from src.states.obd2_state import CarMetadata
import config


def load_sample_data() -> Dict[str, Any]:
    """Load sample OBD2 data from file.
    
    Returns:
        Sample data dictionary
    """
    sample_path = Path(config.SAMPLE_DATA_PATH)
    
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample data file not found: {sample_path}")
    
    with open(sample_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def prepare_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare input data for the workflow.
    
    Args:
        data: Raw input data
        
    Returns:
        Prepared state dictionary
    """
    # Extract and validate car metadata
    car_metadata_dict = data.get("car_metadata", {})
    car_metadata = CarMetadata(**car_metadata_dict)
    
    # Prepare state
    state = {
        "user_id": data.get("user_id", "unknown_user"),
        "car_metadata": car_metadata,
        "obd2_data": data.get("obd2_data", {}),
        "messages": []
    }
    
    return state


def save_report(report: str, user_id: str, output_dir: str = "output") -> str:
    """Save the final report to a file.
    
    Args:
        report: Report content
        user_id: User identifier
        output_dir: Output directory
        
    Returns:
        Path to saved file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"diagnostic_report_{user_id}_{timestamp}.txt"
    filepath = output_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return str(filepath)


def run_workflow(input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run the multi-agent workflow.
    
    Args:
        input_data: Optional input data. If None, loads sample data.
        
    Returns:
        Final state with results
    """
    # Load data
    if input_data is None:
        print("Loading sample data...")
        input_data = load_sample_data()
    
    # Prepare input
    print("Preparing input...")
    state = prepare_input(input_data)
    
    print(f"\nProcessing request for user: {state['user_id']}")
    print(f"Vehicle: {state['car_metadata'].year} {state['car_metadata'].car_name}")
    print(f"Diagnostic codes: {len(state['obd2_data'].get('diagnostic_codes', []))}")
    
    # Run workflow
    print("\n" + "=" * 60)
    print("Starting Multi-Agent Workflow...")
    print("=" * 60 + "\n")
    
    result = main_workflow.invoke(state)
    
    return result


def display_report(result: Dict[str, Any]) -> None:
    """Display the final report.
    
    Args:
        result: Workflow result
    """
    final_report = result.get("final_report", "No report generated")
    
    print("\n" + "=" * 60)
    print("FINAL DIAGNOSTIC REPORT")
    print("=" * 60 + "\n")
    print(final_report)
    print("\n" + "=" * 60)


def main():
    """Main function."""
    try:
        # Check if API keys are set
        if not config.OPENAI_API_KEY:
            print("ERROR: OPENAI_API_KEY not set in environment")
            print("Please set your API key in the .env file")
            sys.exit(1)
        
        if not config.TAVILY_API_KEY:
            print("WARNING: TAVILY_API_KEY not set in environment")
            print("Web search functionality will be limited")
        
        # Run workflow with sample data
        result = run_workflow()
        
        # Display report
        display_report(result)
        
        # Save report to file
        user_id = result.get("user_id", "unknown")
        final_report = result.get("final_report", "")
        
        if final_report and not final_report.startswith("ERROR"):
            filepath = save_report(final_report, user_id)
            print(f"\nReport saved to: {filepath}")
        
        print("\nWorkflow completed successfully!")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

