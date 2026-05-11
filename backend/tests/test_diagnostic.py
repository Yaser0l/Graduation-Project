import pytest
from unittest.mock import patch, MagicMock
from app.services.diagnostic import process_dtc_event
import uuid

@pytest.mark.asyncio
async def test_process_dtc_no_vin(mock_db):
    payload = {"dtc_list": ["P0300"]}
    result = await process_dtc_event(mock_db, payload)
    assert result == {"error": "Missing identification"}

@pytest.mark.asyncio
async def test_process_dtc_unregistered_vehicle(mock_db):
    mock_db.execute.return_value.first.return_value = None
    payload = {"vin": "1HGCM82633A004352", "dtc_list": ["P0300"]}
    result = await process_dtc_event(mock_db, payload)
    assert result == {"error": "Vehicle unregistered"}

@pytest.mark.asyncio
@patch('app.services.diagnostic.llm_service')
async def test_process_dtc_deduplication(mock_llm, mock_db):
    mock_vehicle = MagicMock()
    mock_vehicle._mapping = {"id": uuid.uuid4(), "vin": "abc", "user_id": uuid.uuid4(), "mileage": 100}
    
    mock_existing_report = MagicMock(id=uuid.uuid4())
    
    # 1. First DB query returns vehicle
    # 2. Second DB check returns existing deduplication
    mock_db.execute.return_value.first.side_effect = [mock_vehicle, mock_existing_report]
    
    payload = {"vin": "abc", "dtc_list": ["P0300"]}
    result = await process_dtc_event(mock_db, payload)
    
    assert result is None
    # Ensure commit was pushed for mileage update
    mock_db.commit.assert_called()

def test_diagnostic_list_requires_auth(client):
    response = client.get("/api/diagnostics/")
    assert response.status_code == 401
    
def test_diagnostic_list_empty(client, override_get_current_user, override_get_db, mock_db):
    # User is mocked to have empty reports list
    mock_db.execute.return_value.all.return_value = []
    
    response = client.get("/api/diagnostics/")
    assert response.status_code == 200
    assert response.json() == []
