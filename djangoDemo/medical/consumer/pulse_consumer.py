import asyncio
import datetime
import json
import random

from channels.generic.websocket import AsyncWebsocketConsumer
from sapl_base.decorators import enforce_till_denied


@enforce_till_denied
class PulseConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        while True:
            pulse = random.randint(60,100)
            current_time = datetime.datetime.now()
            time = current_time.strftime('%H:%M:%S')
            await self.send(text_data=json.dumps({'pulse': pulse, 'time': time}))
            print("current time and pulse is " + time + ": " + str(pulse))
            await asyncio.sleep(5)

    async def connect(self):
        await self.accept()



