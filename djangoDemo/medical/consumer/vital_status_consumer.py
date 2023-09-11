import asyncio
import json
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from sapl_base.decorators import enforce_recoverable_if_denied


@enforce_recoverable_if_denied
class VitalStatusConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        elapsed_time = 0
        while True:
            current_time = datetime.now()
            time = current_time.strftime('%H:%M:%S')
            if ((elapsed_time % 60) < 45):
                await self.send(text_data=json.dumps({'time': time, 'status': "okay"}))
            else:
                await self.send(text_data=json.dumps({'time': time, 'status': "critical"}))
            await asyncio.sleep(1)
            elapsed_time += 1

    async def connect(self):
        await self.accept()