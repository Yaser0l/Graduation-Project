import time
import threading
import cantools
import can
import isotp
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DBC_FILE = BASE_DIR / "dbc_files" / "toyota_prius_2010_pt.dbc"

# Load DBC
db = cantools.database.load_file(DBC_FILE)

# ISO-TP Settings
OBD_FUNCTIONAL_REQ_ID = 0x7DF
OBD_ENGINE_RESP_ID = 0x7E8

def periodic_sender(bus):
    print("Started periodic CAN DBC frames sender.")
    # Initialize some mock data
    speed_mph = 35.0 # Let's say 35 mph
    counter = 0

    while True:
        try:
            # SPEED (ID: 180)
            data = db.encode_message('SPEED', {
                'SPEED': speed_mph,
                'ENCODER': counter % 256,
                'CHECKSUM': 0
            })
            bus.send(can.Message(arbitration_id=0x180, data=data, is_extended_id=False))

            # WHEEL_SPEEDS (ID: 170)
            data = db.encode_message('WHEEL_SPEEDS', {
                'WHEEL_SPEED_FL': speed_mph,
                'WHEEL_SPEED_FR': speed_mph,
                'WHEEL_SPEED_RL': speed_mph,
                'WHEEL_SPEED_RR': speed_mph
            })
            bus.send(can.Message(arbitration_id=0x170, data=data, is_extended_id=False))

            # STEER_ANGLE_SENSOR (ID: 37)
            data = db.encode_message('STEER_ANGLE_SENSOR', {
                'STEER_ANGLE': 5.0,
                'STEER_FRACTION': 0.0,
                'STEER_RATE': 0.0
            })
            bus.send(can.Message(arbitration_id=0x25, data=data, is_extended_id=False))

            # POWERTRAIN (ID: 452)
            data = db.encode_message('POWERTRAIN', {
                'ENGINE_RPM': 2500,
                'CHECKSUM': 0
            })
            bus.send(can.Message(arbitration_id=0x1C4, data=data, is_extended_id=False))

            # GAS_PEDAL (ID: 581)
            data = db.encode_message('GAS_PEDAL', {
                'GAS_PEDAL': 0.15
            })
            bus.send(can.Message(arbitration_id=0x245, data=data, is_extended_id=False))

            # BRAKE (ID: 166)
            data = db.encode_message('BRAKE', {
                'BRAKE_AMOUNT': 0,
                'BRAKE_PEDAL': 0
            })
            bus.send(can.Message(arbitration_id=0x166, data=data, is_extended_id=False))

            # GEAR_PACKET (ID: 295)
            data = db.encode_message('GEAR_PACKET', {
                'CAR_MOVEMENT': 0,
                'COUNTER': counter % 256,
                'CHECKSUM': 0,
                'GEAR': 3 # Drive
            })
            bus.send(can.Message(arbitration_id=0x127, data=data, is_extended_id=False))

            counter += 1
            time.sleep(0.05) # 50ms = 20Hz
        except Exception as e:
            print(f"Periodic sender error: {e}")
            time.sleep(1)

def isotp_server(bus):
    print("Started ISO-TP server for OBD-II and UDS requests.")
    
    # Mechanic requests: tx=0x7DF, rx=0x7E8
    # For simulator, we receive on 0x7DF, respond on 0x7E8
    addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=OBD_FUNCTIONAL_REQ_ID, txid=OBD_ENGINE_RESP_ID)
    stack = isotp.CanStack(bus, address=addr)
    
    while True:
        stack.process()
        
        if stack.available():
            req = stack.recv()
            if not req:
                continue
                
            print(f"ISO-TP Received: {req.hex()}")
            
            # OBD Service 03 (Read DTCs)
            if req == b'\x03':
                # Return P0123 (01 23) and U1234 (D2 34)
                # Response: 43 01 23 D2 34 00 00
                stack.send(bytes([0x43, 0x01, 0x23, 0xD2, 0x34, 0x00, 0x00]))
                print("Sent OBD DTCs response")
            
            # OBD Service 01, PID A6 (Odometer)
            elif len(req) >= 2 and req[0] == 0x01 and req[1] == 0xA6:
                # 12345.6 km -> 1234560 decameters
                # 0x0012D680
                stack.send(bytes([0x41, 0xA6, 0x00, 0x12, 0xD6, 0x80]))
                print("Sent OBD Odometer response")
                
            # OBD Service 09, PID 02 (VIN)
            elif len(req) >= 2 and req[0] == 0x09 and req[1] == 0x02:
                # Response 49 02 01 + VIN
                vin = b"SIMULATEDPRIUS"
                # pad to 17 bytes
                vin = vin.ljust(17, b'X')
                stack.send(bytes([0x49, 0x02, 0x01]) + vin)
                print(f"Sent VIN response: {vin}")
                
            # UDS Service 19 02 FF (Read DTC by status)
            elif len(req) >= 3 and req[0] == 0x19 and req[1] == 0x02 and req[2] == 0xFF:
                # Response 59 02 FF + DTCs
                # Each UDS DTC is 3 bytes code + 1 byte status
                # Send 12 34 56 09
                stack.send(bytes([0x59, 0x02, 0xFF, 0x12, 0x34, 0x56, 0x09]))
                print("Sent UDS DTC response")
                
        time.sleep(stack.sleep_time())

def main():
    channel = 'vcan0'
    try:
        bus = can.interface.Bus(channel=channel, interface='socketcan')
        print(f"Successfully opened CAN bus on {channel}")
        
        original_send = bus.send
        def verbose_send(msg, *args, **kwargs):
            original_send(msg, *args, **kwargs)
            print(f"Sent CAN frame: ID={hex(msg.arbitration_id)} Data={msg.data.hex() if msg.data else ''}")
        bus.send = verbose_send
        
    except OSError as e:
        print(f"Failed to open CAN bus on {channel}. Error: {e}")
        print("To setup: sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0")
        return

    # Start the periodic sender in a background thread
    sender_thread = threading.Thread(target=periodic_sender, args=(bus,), daemon=True)
    sender_thread.start()

    # Run the ISO-TP server
    isotp_server(bus)

if __name__ == "__main__":
    main()
