import discord
from discord.ext import commands
import asyncio
from typing import Optional
from shellbot.job import Job
from shellbot.complete import Complete
import os
import shutil
import time


class Shellbot(discord.Bot):
    def __init__(self,
                 admins: list[int],
                 intents: Optional[discord.Intents] = None,
                 ):
        if intents is None:
            intents = discord.Intents(reactions=True)

        super().__init__(intents=intents)
        self.admins = admins
        self._jobs = set()
        self.restart = False

        @self.slash_command(description="Shuts the bot down.")
        async def shutdown(ctx):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return
            await ctx.respond("Bye!", ephemeral=True)
            await self.close()

        @self.slash_command(description="Pings the bot.")
        async def ping(ctx):
            await ctx.respond("Pong.", ephemeral=True)

        @self.slash_command(description="Restarts the bot.")
        async def restart(ctx):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return
            await ctx.respond("Restarting...", ephemeral=True)
            self.restart = True
            await self.close()

        @self.slash_command(description="Uploads a given file to Discord.")
        async def upload(ctx, path: str):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            if not os.path.exists(path):
                await ctx.respond("Could not read the file.", ephemeral=True)
                return

            await ctx.defer()
            if os.path.isdir(path):
                temp_filename = f"temp_{time.time()}"
                shutil.make_archive(temp_filename, 'zip', path)
                temp_filename += '.zip'
                display_filename = os.path.basename(path) + '.zip'
                f = open(temp_filename, 'rb')
            else:
                temp_filename = None
                display_filename = os.path.basename(path)
                f = open(path, 'rb')
        
            await ctx.respond(file=discord.File(f, filename=display_filename))
            f.close()

            if temp_filename:
                os.remove(temp_filename)

        job_group = self.create_group(name="job")

        complete_job_id = Complete(self, lambda: [job.id for job in self._jobs])
        complete_command = Complete(self)

        @job_group.command(name="run", description="Starts a new job.")
        async def job_run(ctx, 
                          command: discord.Option(str, autocomplete=complete_command.autocomplete)
                          ):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            job = Job(command.split(' '))
            self._jobs.add(job)

            complete_command.update_history(ctx, command)
            complete_job_id.update_history(ctx, job.id)

            await job.view(ctx)
            await job.start()

        @job_group.command(name="view", description="Opens a new view for a job.")
        async def job_view(ctx, 
                           job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                           ):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            id = job
            job = None
            for j in self._jobs:
                if j.id == id:
                    job = j

            if job is None:
                await ctx.respond(f"Job ID {id} not found.", ephemeral=True)
                return

            complete_job_id.update_history(ctx, id)
            await job.view(ctx)

        @job_group.command(name="dump", description="Uploads a job's entire output to Discord.")
        async def job_dump(ctx, 
                           job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                           ):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            id = job
            job = None
            for j in self._jobs:
                if j.id == id:
                    job = j

            if job is None:
                await ctx.respond(f"Job ID {id} not found.", ephemeral=True)
                return

            complete_job_id.update_history(ctx, id)
            await ctx.defer()
            temp_filename = f"temp_{time.time()}.txt"
            with open(temp_filename, 'w') as f:
                f.write(job._window._build(raw=True))
                f.close()

            with open(temp_filename, 'rb') as f:
                await ctx.respond(file=discord.File(f, filename=f"job_{id}.txt"))

            os.remove(temp_filename)

        @job_group.command(name='kill', description="Kills a job.")
        async def job_kill(ctx, 
                           job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                           ):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            id = job
            job = None
            for j in self._jobs:
                if j.id == id:
                    job = j

            if job is None:
                await ctx.respond(f"Job ID {id} not found.", ephemeral=True)
                return

            complete_job_id.update_history(ctx, id)
            await ctx.defer(ephemeral=True)
            await job.kill()
            await ctx.respond("Killed.", ephemeral=True)

        @job_group.command(name="list", description="Lists all jobs.")
        async def job_list(ctx):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            if len(self._jobs) == 0:
                await ctx.respond("No jobs found.", ephemeral=True)
                return

            pad = len(str(Job.id_counter))
            buff = []
            for j in self._jobs:
                prefix = '   '
                if j.status == 'running':
                    prefix = '>  '
                elif j.status == 'success':
                    prefix = '+  '
                elif j.status == 'fail':
                    prefix = '-  '
                buff.append(prefix + str(j.id).ljust(pad) + ' :: ' + str(j.args))

            await ctx.respond("```diff\n" + "\n".join(buff) + "\n```", ephemeral=True)

        @job_group.command(name="status", description="Shows a job's status.")
        async def job_status(ctx, 
                             job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                             ):
            if ctx.author.id not in self.admins:
                await ctx.respond("Permission not granted.", ephemeral=True)
                return

            id = job
            job = None
            for j in self._jobs:
                if j.id == id:
                    job = j

            if job is None:
                await ctx.respond(f"Job ID {id} not found.", ephemeral=True)
                return

            complete_job_id.update_history(ctx, id)

            prefix = '   '
            if job.status == 'running':
                prefix = '>  '
            elif job.status == 'success':
                prefix = '+  '
            elif job.status == 'fail':
                prefix = '-  '

            await ctx.respond("```diff\n" 
                              + prefix + str(job.id) + ' :: ' 
                              + str(job.args) + "\n```",
                              ephemeral=True)

    def job_by_view(self, message):
        for job in self._jobs:
            if job.has_view(message): 
                return job

    async def on_raw_reaction_add(self, payload):
        channel = await self.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = payload.member
        emoji = payload.emoji

        control_emojis = {'close': '🗑️',
                          'kill': '💀'}


        def is_job_control():
            if member == self.user: return False
            if message.author != self.user: return False
            if emoji.name not in control_emojis.values(): return False
            if not hasattr(message, 'interaction') or not message.interaction: return False
            appcmd = 2 # discord.InteractionType.application_command
            if message.interaction.type != appcmd: return False
            return message.interaction.name in ['job run', 'job view']

        if not is_job_control():
            return

        async def remove_reaction():
            for reaction in message.reactions:
                if reaction.emoji not in control_emojis.values(): continue
                async for user in reaction.users():
                    if user != self.user:
                        await reaction.remove(user)
            return

        if member.id not in self.admins:
            await remove_reaction()

        job = self.job_by_view(message)
        name = emoji.name

        if job is None: 
            if name == control_emojis['close']:
                await message.delete()

            return

        if name == control_emojis['close']:
            await job.close_view(message)
        elif name == control_emojis['kill']:
            await job.kill()
        await remove_reaction()
