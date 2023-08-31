import discord
from discord.ext import commands
import asyncio
from typing import Optional
from shellbot.job import Job


class Shellbot(discord.Bot):
    def __init__(self,
                 admins: list[int],
                 intents: Optional[discord.Intents] = None,
                 ):
        super().__init__(intents=intents)
        self.admins = admins
        self._jobs = set()

        job_group = self.create_group(name="job")

        @job_group.command(name="start")
        async def job_start(ctx, command: str):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            job = Job(ctx, command.split(' '))
            self._jobs.add(job)
            await job.start()
            self._jobs.remove(job)

        async def get_jobs(ctx: discord.AutocompleteContext):
            if ctx.interaction.user.id not in self.admins: return []
            return [job.id for job in self._jobs]

        @job_group.command(name='kill')
        async def job_kill(ctx, 
                           id: discord.Option(int, autocomplete=discord.utils.basic_autocomplete(get_jobs))
                           ):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            job = None
            for j in self._jobs:
                if j.id == id:
                    job = j

            if job is None:
                await ctx.respond("The job is not currently running.", ephemeral=True)

            await ctx.defer(ephemeral=True)
            await job.kill()
            await ctx.respond("Killed.", ephemeral=True)

        @job_group.command(name="list")
        async def job_list(ctx):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            if len(self._jobs) == 0:
                await ctx.respond("No job is currently running.")
                return

            pad = len(str(Job.id_counter))
            buff = [f"{str(j.id).ljust(pad)} :: {j.args}" for j in self._jobs]
            await ctx.respond("```\n" + "\n".join(buff) + "\n```", ephemeral=True)

