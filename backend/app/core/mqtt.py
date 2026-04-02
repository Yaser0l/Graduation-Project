import asyncio
import json
from gmqtt import Client as MQTTClient
from app.core.config import settings

class MqttService:
    def __init__(self, on_report_created_cb=None):
        self.client = MQTTClient("carbrain-backend")
        self.on_report_created_cb = on_report_created_cb

    def on_connect(self, client, flags, rc, properties):
        print("[MQTT] Connected")
        self.client.subscribe(settings.MQTT_TOPIC_DTC)

    def on_message(self, client, topic, payload, qos, properties):
        print(f"[MQTT] Message received on {topic}: {payload.decode()}")
        try:
            data = json.loads(payload.decode())
            # Logic to process DTC and create report
            # In a real app, you'd save to DB here and then call the callback
            # For now, we simulate the callback trigger
            if self.on_report_created_cb:
                # Assuming data contains userId and report
                user_id = data.get("userId")
                report = data.get("report")
                if user_id and report:
                    asyncio.create_task(self.on_report_created_cb(user_id, report))
        except Exception as e:
            print(f"[MQTT] Error processing message: {e}")

    async def connect(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        if settings.MQTT_USER:
            self.client.set_auth_credentials(settings.MQTT_USER, settings.MQTT_PASSWORD)
            
        await self.client.connect(settings.MQTT_HOST, settings.MQTT_PORT)

    async def disconnect(self):
        await self.client.disconnect()

mqtt_service = None # Will be initialized in lifespan
