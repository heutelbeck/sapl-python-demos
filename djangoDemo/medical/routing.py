# chat/routing.py
from django.urls import re_path

from medical.consumer.pulse_consumer import PulseConsumer
from medical.consumer.vital_status_consumer import VitalStatusConsumer
from medical.consumer.blood_pressure_consumer import BloodPressureConsumer

websocket_urlpatterns = [
    re_path(r"ws/pulse", PulseConsumer.as_asgi()),
    re_path(r"ws/blood_pressure", BloodPressureConsumer.as_asgi()),
    re_path(r"ws/vital_status", VitalStatusConsumer.as_asgi()),
]