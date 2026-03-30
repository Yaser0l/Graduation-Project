"""Test script for the multi-agent workflow."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import run_workflow, prepare_input
from src.states.obd2_state import CarMetadata
import json


def test_sample_data():
    """Test workflow with sample data."""
    print("=" * 60)
    print("TEST: Running workflow with sample data")
    print("=" * 60)
    
    try:
        result = run_workflow()
        
        # Verify result has expected fields
        assert "final_report" in result, "Missing final_report in result"
        assert result["final_report"], "Final report is empty"
        
        print("\nTest passed: Sample data workflow completed successfully")
        return True
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_custom_tire_issue():
    """Test workflow with custom tire pressure issue."""
    print("\n" + "=" * 60)
    print("TEST: Custom tire pressure issue")
    print("=" * 60)
    
    custom_data = {
        "user_id": "test_user_002",
        "car_metadata": {
            "car_name": "Honda Accord",
            "car_model": "Sport",
            "year": 2021,
            "mileage": 35000,
            "vin": "1HGCV1F30LA000001"
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
                    "front_left": 30,
                    "front_right": 31,
                    "rear_left": 29,
                    "rear_right": 30,
                    "unit": "PSI",
                    "recommended": 32
                },
                "engine_temp": 190,
                "oil_pressure": 45,
                "battery_voltage": 12.8
            },
            "freeze_frame_data": {
                "vehicle_speed": 55,
                "engine_rpm": 2300,
                "fuel_level": 70
            }
        }
    }
    
    try:
        result = run_workflow(custom_data)
        
        # Verify result
        assert "final_report" in result, "Missing final_report"
        assert "tire" in result["final_report"].lower(), "Report doesn't mention tire issue"
        
        print("\nTest passed: Custom tire issue workflow completed")
        return True
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_input_validation():
    """Test input validation."""
    print("\n" + "=" * 60)
    print("TEST: Input validation")
    print("=" * 60)
    
    # Test missing fields
    invalid_data = {
        "user_id": "test_user",
        # Missing car_metadata and obd2_data
    }
    
    try:
        state = prepare_input(invalid_data)
        print("Test failed: Should have raised an error for missing fields")
        return False
    except Exception as e:
        print(f"Test passed: Correctly caught validation error: {type(e).__name__}")
        return True


def test_memory_system():
    """Test memory system."""
    print("\n" + "=" * 60)
    print("TEST: Memory system")
    print("=" * 60)
    
    from src.memory.user_memory import memory_manager
    from src.states.obd2_state import CarMetadata
    
    test_user_id = "memory_test_user"
    
    try:
        # Test save profile
        car_metadata = CarMetadata(
            car_name="Test Car",
            car_model="Test Model",
            year=2022,
            mileage=10000,
            vin="TEST123456789"
        )
        
        success = memory_manager.save_user_profile(test_user_id, car_metadata)
        assert success, "Failed to save profile"
        
        # Test load profile
        loaded_profile = memory_manager.load_user_profile(test_user_id)
        assert loaded_profile is not None, "Failed to load profile"
        assert loaded_profile.car_name == "Test Car", "Profile data mismatch"
        
        # Test append history
        interaction = {
            "type": "test",
            "summary": "Test interaction"
        }
        success = memory_manager.append_to_history(test_user_id, interaction)
        assert success, "Failed to append history"
        
        # Test load history
        history = memory_manager.load_conversation_history(test_user_id)
        assert len(history) > 0, "No history loaded"
        
        print("Test passed: Memory system working correctly")
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_system():
    """Test RAG system."""
    print("\n" + "=" * 60)
    print("TEST: RAG system")
    print("=" * 60)
    
    from src.rag.knowledge_base import knowledge_base
    
    try:
        # Test retrieval
        docs = knowledge_base.retrieve("C0750 tire pressure sensor", k=3)
        assert len(docs) > 0, "No documents retrieved"
        
        print(f"Retrieved {len(docs)} documents")
        print(f"First document preview: {docs[0].page_content[:100]}...")
        
        # Test reflection
        is_sufficient, score, reflection = knowledge_base.reflect_on_retrieval(
            "C0750 tire pressure sensor",
            docs
        )
        
        print(f"Reflection - Sufficient: {is_sufficient}, Score: {score:.2f}")
        print(f"Reflection message: {reflection}")
        
        print("Test passed: RAG system working correctly")
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_codes_routes_to_error():
    """Edge: empty diagnostic_codes should route to error node without LLM calls."""
    print("\n" + "=" * 60)
    print("TEST: Empty diagnostic codes routes to error")
    print("=" * 60)

    from src.graph.main_graph import main_workflow

    input_state = {
        "user_id": "edge_user_empty_codes",
        "car_metadata": {
            "car_name": "Test Car",
            "car_model": "Base",
            "year": 2022,
            "mileage": 1000,
            "vin": "EDGE00000001"
        },
        "obd2_data": {
            "diagnostic_codes": [],
            "sensor_readings": {}
        },
        "messages": []
    }

    try:
        # prepare_input will validate the pydantic model; pass dict directly since we need router to see empty list
        result = main_workflow.invoke(input_state)
        assert "final_report" in result, "Missing final_report"
        assert result["final_report"].startswith("ERROR:"), "Should return an ERROR final_report"
        print("Test passed: Empty codes routed to error as expected")
        return True
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 30)
    print("RUNNING ALL TESTS")
    print("=" * 30 + "\n")
    
    tests = [
        ("Memory System", test_memory_system),
        ("RAG System", test_rag_system),
        ("Input Validation", test_input_validation),
        ("Sample Data Workflow", test_sample_data),
        ("Custom Tire Issue", test_custom_tire_issue),
        ("Empty Codes → Error", test_empty_codes_routes_to_error),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\nTest '{name}' crashed: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

