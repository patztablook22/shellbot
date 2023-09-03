import subprocess, threading
import importlib.util
import io, sys, time
import asyncio
from shellbot.window import Window

class Job:
    id_counter = 0

    def __init__(self, args):
        self.args = args
        self.id = Job.id_counter
        Job.id_counter += 1
        self._relay = None
        self._queue = []
        self._window = Window(self.id)
        self._ps = None
        self.status = None

    def has_view(self, message):
        return self._window.has_view(message)

    async def view(self, ctx):
        await self._window.view(ctx)

    async def close_view(self, message):
        await self._window.close_view(message)

    async def start(self):
        self.status = 'running'

        def relay():
            try:
                ps = subprocess.Popen(args=self.args,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
                self._ps = ps
            except Exception as e:
                self._window.update(str(e))
                self._window.close()
                self.status = 'fail'
                return

            while True:
                data = ps.stdout.readline()
                if not data: break
                self._window.update(data.decode('utf-8')[:-1])

            self._ps.wait()
            self._window.close(exit_status=self._ps.poll())
            self.status = 'success' if self._ps.poll() == 0 else 'fail'

        await self._window.render()
        self._relay = threading.Thread(target=relay)
        self._relay.start()
        while await self._window.render():
            await asyncio.sleep(0.1)

    async def kill(self):
        assert self._ps is not None
        self._ps.terminate()
        if self._ps.poll() is None:
            await asyncio.sleep(3)
            if self._ps.poll() is None:
                self._ps.kill()
