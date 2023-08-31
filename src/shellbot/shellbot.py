import discord
from discord.ext import commands
import asyncio
from typing import Optional
from shellbot.job import Job


class Shellbot(discord.Bot):
    def __init__(self,
                 intents: Optional[discord.Intents] = None,
                 ):
        super().__init__(intents=intents)

        job_group = self.create_group(name="job")

        @job_group.command(name="start")
        async def job_start(ctx, command: str):
            job = Job(ctx, command)
            await job.start()
