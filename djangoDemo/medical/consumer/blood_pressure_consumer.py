import asyncio
import json
import random
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from sapl_base.decorators import enforce_drop_while_denied

class BloodPressureConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, bytes_data=None):

        async for i in self.customgen():
            try:
                current_time = datetime.now()
                time = current_time.strftime('%H:%M:%S')
                i.update({'time':time})
                await self.send(text_data=json.dumps(i))
            except Exception:
                pass

    @enforce_drop_while_denied
    async def customgen(self):
        while True:
            blood_pressure_1 = random.randint(95,165)
            blood_pressure_2 = random.randint(65,100)
            yield {'blood_pressure_1':blood_pressure_1,'blood_pressure_2':blood_pressure_2}
            await asyncio.sleep(5)


    async def connect(self):
        await self.accept()