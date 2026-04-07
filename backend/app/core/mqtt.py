import asyncio
import json
import logging
from json import JSONDecodeError
from gmqtt import Client as MQTTClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class MqttService:
    def __init__(self, on_report_created_cb=None):
        self.client = MQTTClient("carbrain-backend")
        self.on_report_created_cb = on_report_created_cb

    def on_connect(self, client, flags, rc, properties):
        logger.info("[MQTT] Connected")
        self.client.subscribe(settings.MQTT_TOPIC_DTC)
        logger.warning("[MQTT] Subscribed to topic pattern: %s", settings.MQTT_TOPIC_DTC)

    def on_message(self, client, topic, payload, qos, properties):
        logger.info("[MQTT] Message received on %s", topic)
        raw = payload.decode(errors="replace")
        logger.warning("[MQTT] Incoming event topic=%s payload=%s", "vehicle/+/dtc", raw)
        try:
            data = json.loads(raw)
            asyncio.create_task(self.handle_event(data))
        except JSONDecodeError:
            # Some shells wrap JSON in single quotes; strip once and retry.
            candidate = raw.strip()
            if candidate.startswith("'") and candidate.endswith("'") and len(candidate) >= 2:
                candidate = candidate[1:-1]

            try:
                data = json.loads(candidate)
                logger.warning("[MQTT] Payload required quote normalization before JSON parsing")
                asyncio.create_task(self.handle_event(data))
            except Exception as e:
                logger.error("[MQTT] Error decoding message: %s | raw=%r", e, raw)
        except Exception as e:
            logger.error("[MQTT] Error handling message: %s | raw=%r", e, raw)

    async def handle_event(self, data: dict):
        from app.db.session import SessionLocal
        from app.services.diagnostic import process_dtc_event

        logger.warning("[MQTT] Forwarding event to diagnostic service (backend pipeline)")

        async with SessionLocal() as db:
            try:
                await process_dtc_event(
                    db,
                    data,
                    on_report_created=self.on_report_created_cb
                )
            except Exception as e:
                logger.error("[MQTT] handle_event failed: %s", e)

    async def connect(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        if settings.MQTT_USER:
            self.client.set_auth_credentials(settings.MQTT_USER, settings.MQTT_PASSWORD)

        await self.client.connect(settings.MQTT_HOST, settings.MQTT_PORT)

    async def publish(self, topic: str, payload: dict, qos: int = 1, retain: bool = False):
        body = json.dumps(payload)
        self.client.publish(topic, body, qos=qos, retain=retain)
        logger.info("[MQTT] Published message to %s", topic)

    async def disconnect(self):
        await self.client.disconnect()
