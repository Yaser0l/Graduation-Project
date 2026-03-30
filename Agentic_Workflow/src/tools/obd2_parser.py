"""OBD2 data parser tool."""
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from src.states.obd2_state import OBD2Data, DiagnosticCode, SensorReadings


def parse_obd2_data(raw_data: Dict[str, Any]) -> OBD2Data:
    """Parse raw OBD2 data into structured format.
    
    Args:
        raw_data: Raw OBD2 data dictionary
        
    Returns:
        Structured OBD2Data object
    """
    # Parse diagnostic codes
    codes = []
    if 'diagnostic_codes' in raw_data:
        for code_data in raw_data['diagnostic_codes']:
            codes.append(DiagnosticCode(**code_data))
    
    # Parse sensor readings
    sensor_data = raw_data.get('sensor_readings', {})
    sensors = SensorReadings(**sensor_data)
    
    # Get freeze frame data
    freeze_frame = raw_data.get('freeze_frame_data', None)
    
    return OBD2Data(
        diagnostic_codes=codes,
        sensor_readings=sensors,
        freeze_frame_data=freeze_frame
    )


@tool
def extract_diagnostic_codes(obd2_data: Dict[str, Any]) -> str:
    """Extract and format diagnostic trouble codes from OBD2 data.
    
    Args:
        obd2_data: Raw OBD2 data
        
    Returns:
        Formatted string of diagnostic codes
    """
    codes = obd2_data.get('diagnostic_codes', [])
    
    if not codes:
        return "No diagnostic trouble codes found."
    
    formatted = ["Diagnostic Trouble Codes (DTCs):"]
    
    for code in codes:
        code_str = code.get('code', 'Unknown')
        description = code.get('description', 'No description')
        system = code.get('system', 'Unknown system')
        
        formatted.append(f"\n- {code_str}: {description}")
        formatted.append(f"  System: {system}")
    
    return "\n".join(formatted)


@tool
def analyze_sensor_readings(obd2_data: Dict[str, Any]) -> str:
    """Analyze sensor readings for anomalies.
    
    Args:
        obd2_data: Raw OBD2 data
        
    Returns:
        Analysis of sensor readings
    """
    sensor_readings = obd2_data.get('sensor_readings', {})
    
    if not sensor_readings:
        return "No sensor readings available."
    
    analysis = ["Sensor Reading Analysis:"]
    
    # Check tire pressure
    if 'tire_pressure' in sensor_readings:
        tire_data = sensor_readings['tire_pressure']
        recommended = tire_data.get('recommended', 35)
        
        pressures = {
            'Front Left': tire_data.get('front_left'),
            'Front Right': tire_data.get('front_right'),
            'Rear Left': tire_data.get('rear_left'),
            'Rear Right': tire_data.get('rear_right')
        }
        
        analysis.append("\nTire Pressure:")
        low_pressure = False
        
        for position, pressure in pressures.items():
            if pressure:
                status = "OK" if pressure >= recommended - 2 else "LOW"
                if status == "LOW":
                    low_pressure = True
                analysis.append(f"  {position}: {pressure} PSI ({status})")
        
        if low_pressure:
            analysis.append(f"  Warning: Some tires are below recommended pressure ({recommended} PSI)")
    
    # Check engine temperature
    engine_temp = sensor_readings.get('engine_temp')
    if engine_temp:
        analysis.append(f"\nEngine Temperature: {engine_temp}°F")
        if engine_temp > 220:
            analysis.append("  Warning: Engine temperature is high")
        elif engine_temp < 160:
            analysis.append("  Info: Engine may not be fully warmed up")
    
    # Check oil pressure
    oil_pressure = sensor_readings.get('oil_pressure')
    if oil_pressure:
        analysis.append(f"\nOil Pressure: {oil_pressure} PSI")
        if oil_pressure < 20:
            analysis.append("  Warning: Oil pressure is low")
    
    # Check battery voltage
    battery_voltage = sensor_readings.get('battery_voltage')
    if battery_voltage:
        analysis.append(f"\nBattery Voltage: {battery_voltage}V")
        if battery_voltage < 12.4:
            analysis.append("  Warning: Battery voltage is low")
        elif battery_voltage > 14.8:
            analysis.append("  Warning: Battery voltage is high (possible charging system issue)")
    
    return "\n".join(analysis)


def validate_obd2_data(raw_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate OBD2 data format.
    
    Args:
        raw_data: Raw OBD2 data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for required fields
    if 'diagnostic_codes' not in raw_data:
        return False, "Missing 'diagnostic_codes' field"
    
    if not isinstance(raw_data['diagnostic_codes'], list):
        return False, "'diagnostic_codes' must be a list"
    
    # Validate each diagnostic code
    for code in raw_data['diagnostic_codes']:
        if 'code' not in code:
            return False, "Each diagnostic code must have a 'code' field"
        if 'description' not in code:
            return False, "Each diagnostic code must have a 'description' field"
    
    return True, None


def format_obd2_summary(obd2_data: Dict[str, Any]) -> str:
    """Create a human-readable summary of OBD2 data.
    
    Args:
        obd2_data: Raw OBD2 data
        
    Returns:
        Formatted summary
    """
    codes = obd2_data.get('diagnostic_codes', [])
    code_count = len(codes)
    
    summary = [f"OBD2 Diagnostic Summary"]
    summary.append(f"{'=' * 40}")
    summary.append(f"\nTotal Diagnostic Codes: {code_count}")
    
    if code_count > 0:
        summary.append("\nActive Codes:")
        for code in codes:
            summary.append(f"  • {code.get('code', 'Unknown')}: {code.get('description', 'No description')}")
    
    # Add sensor summary
    sensor_readings = obd2_data.get('sensor_readings', {})
    if sensor_readings:
        summary.append("\nKey Sensor Readings:")
        
        if 'tire_pressure' in sensor_readings:
            summary.append("  • Tire Pressure: See detailed analysis")
        
        if 'engine_temp' in sensor_readings:
            summary.append(f"  • Engine Temp: {sensor_readings['engine_temp']}°F")
        
        if 'battery_voltage' in sensor_readings:
            summary.append(f"  • Battery: {sensor_readings['battery_voltage']}V")
    
    return "\n".join(summary)

