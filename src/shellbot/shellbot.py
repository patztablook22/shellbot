import discord
from discord.ext import commands
import asyncio
from typing import Optional
from shellbot.job import Job
from shellbot.complete import Complete
from shellbot.idlist import IdList
import os
import shutil
import time


class PermissionError(discord.errors.CheckFailure): 
    def __init__(self):
        super().__init__("Permission denied.")

CommandError = discord.errors.ApplicationCommandError

class Shellbot(discord.Bot):
    def __init__(self,
                 roles: Optional[list | dict] = None,
                 users: Optional[list | dict] = None,
                 intents: Optional[discord.Intents] = None,
                 ):
        if intents is None:
            intents = discord.Intents(reactions=True)

        super().__init__(intents=intents)
        self._roles = IdList(roles)
        self._users = IdList(users)
        self._jobs = set()

        def permitted(ctx):
            if not self.permitted(ctx.author):
                raise PermissionError()
            return True

        def check_permission(func):
            return discord.ext.commands.check(permitted)(func)

        def job_by_id(id):
            j = self.job_by_id(id)
            if not j: raise CommandError(f"Job ID {id} not found.")
            return j

        @self.slash_command(description="Shuts the bot down.")
        @check_permission
        async def shutdown(ctx):
            await ctx.respond("Bye!", ephemeral=True)
            await self.close()

        @self.slash_command(description="Pings the bot.")
        async def ping(ctx):
            await ctx.respond("Pong.", ephemeral=True)

        @self.slash_command(description="Uploads a given file to Discord.")
        @check_permission
        async def upload(ctx, path: str):
            if not os.path.exists(path): raise CommandError("Could not read the file")
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
        @check_permission
        async def job_run(ctx, 
                          command: discord.Option(str, autocomplete=complete_command.autocomplete)
                          ):
            job = Job(command.split(' '))
            self._jobs.add(job)

            complete_command.update_history(ctx, command)
            complete_job_id.update_history(ctx, job.id)

            await job.view(ctx)
            await job.start()

        @job_group.command(name="view", description="Opens a new view for a job.")
        @check_permission
        async def job_view(ctx, 
                           job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                           ):
            j = job_by_id(job)
            complete_job_id.update_history(ctx, job)
            await j.view(ctx)

        @job_group.command(name="dump", description="Uploads a job's entire output to Discord.")
        @check_permission
        async def job_dump(ctx, 
                           job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                           ):
            j = job_by_id(job)
            complete_job_id.update_history(ctx, job)
            await ctx.defer()
            temp_filename = f"temp_{time.time()}.txt"
            with open(temp_filename, 'w') as f:
                f.write(j._window._build(raw=True))
                f.close()

            with open(temp_filename, 'rb') as f:
                await ctx.respond(file=discord.File(f, filename=f"job_{id}.txt"))

            os.remove(temp_filename)

        @job_group.command(name='kill', description="Kills a job.")
        @check_permission
        async def job_kill(ctx, 
                           job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                           ):
            j = job_by_id(job)
            complete_job_id.update_history(ctx, job)
            await ctx.defer(ephemeral=True)
            await j.kill()
            await ctx.respond("Killed.", ephemeral=True)

        @job_group.command(name="list", description="Lists all jobs.")
        @check_permission
        async def job_list(ctx):
            if len(self._jobs) == 0:
                await ctx.respond("```diff\n--- No jobs found\n```", ephemeral=True)
                return

            pad = len(str(Job.id_counter))
            buff = []
            for j in sorted(self._jobs, key=lambda j: -j.id)[:10]:
                prefix = {'running': '>',
                          'success': '+',
                          'fail': '-'}.get(j.status, '').ljust(3)
                buff.append(prefix + str(j.id).ljust(pad) + ' :: ' + str(j.args))

            await ctx.respond("```diff\n" + "\n".join(buff) + "\n```", ephemeral=True)

        @job_group.command(name="status", description="Shows a job's status.")
        @check_permission
        async def job_status(ctx, 
                             job: discord.Option(int, autocomplete=complete_job_id.autocomplete)
                             ):
            j = job_by_id(job)
            complete_job_id.update_history(ctx, job)

            prefix = {'running': '>',
                      'success': '+',
                      'fail': '-'}.get(j.status, '').ljust(3)

            await ctx.respond("```diff\n" 
                              + prefix + str(j.id) + ' :: ' 
                              + str(j.args) + "\n```",
                              ephemeral=True)

    async def on_application_command_error(self, ctx, error):
        await ctx.respond(str(error), ephemeral=True)

    def job_by_view(self, message):
        for job in self._jobs:
            if job.has_view(message): 
                return job

    def permitted(self, user):
        if user.id in self._users: return True
        if self._roles.any([i.id for i in user.roles if i]): return True
        return False

    def job_by_id(self, id):
        for job in self._jobs:
            if job.id == id:
                return job
        return None

    def set(self, **kwargs):
        if 'users' in kwargs:
            self._users = IdList(kwargs['users'])
        if 'roles' in kwargs:
            self._roles = IdList(kwargs['roles'])


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

        if not self.permitted(member):
            await remove_reaction()
            return

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

    def get_code(self, message):
        pass
        #print(message)
        #print("asdfasdf")
        #if self.user not in message.mentions: return
        #print(message.content)

    async def on_message(self, message):
        code = self.get_code(message)

    async def on_message_edit(self, before, after):
        code = self.get_code(after)
