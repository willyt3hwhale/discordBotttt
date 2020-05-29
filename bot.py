import discord
from secret import api_token
from time import sleep, time
from datetime import datetime, timedelta, timezone
import asyncio
from dataclasses import dataclass
from typing import Optional

text_message_timeout = 10
voice_timeout = 5
command_prefix = "!"

#kolla server owner -> öppna dm_channel -> kolla history -> config

commands = {}

@dataclass
class CommandtCtx:
    user: discord.User
    channel: Optional[discord.abc.GuildChannel]
    guild: Optional[discord.Guild]
    message: Optional[discord.Message]

def command(cmds):
    def dec(func):
        async def _func(self, args, context):
            print(f"{context.user.name}: Ran function '{func.__name__}({context})'")
            return await func(self,  args, context)
        cmds[func.__name__.lower()] = _func
        return _func
    return dec

def admin_command(cmds):
    def dec(func):
        async def _func(self, args, context):
            admin_for = filter(lambda x: x.owner == context.user, self.guilds)
            return await func(self, args, context, admin_for=admin_for)
        cmds[func.__name__.lower()] = _func
        return _func
    return dec

def mod_command(cmds):
    def dec(func):
        async def _func(self, args, context):
            if (context.guild and context.guild.owner != context.user and context.user.id not in self.moderators.get(context.guild.id, [])):
                return None

            return await func(self, args, context)
        cmds[func.__name__.lower()] = _func
        return _func
    return dec


class MyClient(discord.Client):
    watchlist = {}
    whitelist = {}
    moderators = {}
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.cleanup()

    @command(commands)
    async def print(self, args, context):
       await context.channel.send(content=str(args))

    @mod_command(commands)
    async def watch(self, args, context, mod_for=None):
        if (int(args) not in self.watchlist.setdefault(context.channel.guild.id, [])):
            self.watchlist[context.channel.guild.id].append(int(args))
        await context.channel.send(content=str(self.watchlist))

    @mod_command(commands)
    async def unwatch(self, args, context, mod_for=None):
        if (int(args) in self.watchlist.get(context.channel.guild.id, [])):
            self.watchlist[context.channel.guild.id].remove(int(args))
        await context.channel.send(content=str(self.watchlist))

    @command(commands)
    async def join(self, args, context):
        channel = context.user.voice.channel
        await channel.connect()

    @admin_command(commands)
    async def mod(self, args, context, admin_for=None):
        for target in context.message.mentions:
            mods = self.moderators.setdefault(context.guild.id, [])
            if (target.id not in mods):
                mods.append(target.id)
        await context.channel.send(content=str(self.moderators))

    @admin_command(commands)
    async def unmod(self, args, context, admin_for=None):
        for target in context.message.mentions:
            mods = self.moderators.setdefault(context.guild.id, [])
            if (target.id in mods):
                mods.remove(target.id)
        await context.channel.send(content=str(self.moderators))

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))
        if(message.guild == None or (message.author == message.guild.owner or message.author.id in self.moderators.get(message.guild.id, []))):
            if (message.content.startswith(command_prefix)):
                msg = message.content[len(command_prefix):].lower()
                if (' ' in msg):
                    cmd, args = msg.split(' ', 1)
                else:
                    cmd = msg
                    args = ""
                if (cmd in commands):
                    context = CommandtCtx(channel=message.channel, user=message.author, guild=message.guild, message=message)
                    await commands[cmd](self, args, context)


    async def on_voice_state_update(self, member, before, after):
        if (not before.channel):
            return
        channel = before.channel
        category = channel.category_id
        switched_channel = channel == after.channel

        current_members = channel.members

        is_empty = len(current_members) == 0
        channel_id = channel.id
        if(is_empty and category in self.watchlist.get(channel.guild.id, []) and channel_id not in self.whitelist.get(channel.guild.id, [])):
            await channel.delete()
        
    async def on_guild_channel_create(self, channel):
        if (channel.category_id not in self.watchlist.get(channel.guild.id, [])):
            return

        if (channel.type == discord.ChannelType.voice):
            await asyncio.sleep(voice_timeout)
            if(len(channel.members) == 0):
                await channel.delete()

        elif (channel.type == discord.ChannelType.text):
            await asyncio.sleep(text_message_timeout)
            while(len(messages := await channel.history(limit=1, oldest_first=False).flatten()) > 0):
                created_at = messages[0].created_at if messages[0].edited_at is None else messages[0].edited_at
                timeout = ((created_at + timedelta(seconds=text_message_timeout)) - datetime.utcnow()).total_seconds()
                if(timeout <= 0):
                    break
                await asyncio.sleep(timeout)
            await channel.delete()



    async def cleanup(self):
        for server in self.guilds:
            for channel in server.channels:
                if(channel.category_id in self.watchlist.get(channel.guild.id, []) and channel.id not in self.whitelist.get(channel.guild.id, []) and (channel.type != discord.ChannelType.voice or len(channel.members) == 0 )):
                    await channel.delete()

    async def init_config(self):
        admins = {}
        for guild in self.guilds:
            if guild.owner is not None:
                admins.setdefault(guild.owner, []).append(guild)

        for (admin, guilds) in admins.items():
            if admin.dm_channel is None:
                await admin.create_dm()
            config = admin.dm_channel.history(limit=1, oldest_first=True)

        return config




client = MyClient()
client.run(api_token)

