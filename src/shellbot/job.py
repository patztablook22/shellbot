import subprocess, threading
import importlib.util
import io, sys, time
import asyncio
from shellbot.window import Window

class Job:
    def __init__(self, ctx, command):
        self._command = command
        self._relay = None
        self._queue = []
        self._window = Window(ctx)

    async def start(self):
        def relay():
            ps = subprocess.Popen(args=self._command,
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
            while True:
                data = ps.stdout.readline()
                if not data: break
                self._window.update(data.decode('utf-8')[:-1])
            self._window.close()

        await self._window.init()
        self._relay = threading.Thread(target=relay)
        self._relay.start()
        while True:
            await asyncio.sleep(0.1)
            await self._window.render()

