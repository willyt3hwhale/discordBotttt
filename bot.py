#!/usr/bin/env python3

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
            if (context.guild and context.guild.owner != context.user and context.user.id not in self._moderators.get(context.guild.id, [])):
                return None

            return await func(self, args, context)
        cmds[func.__name__.lower()] = _func
        return _func
    return dec


class MyClient(discord.Client):
    _watchlist = {}
    _whitelist = {}
    _moderators = {}
    _privateChannelQueue = {}
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.init_config()
        await self.cleanup()

    @command(commands)
    async def print(self, args, context):
       await context.channel.send(content=str(args))

    @admin_command(commands)
    async def watch(self, args, context, admin_for=None):
        for guild in admin_for:
            if (int(args) not in self._watchlist.setdefault(guild.id, [])) and int(args) in [x.id for x in guild.categories]:
                self._watchlist[guild.id].append(int(args))
            await self.save_config(guild)

    @admin_command(commands)
    async def unwatch(self, args, context, admin_for=None):
        for guild in admin_for:
            if (int(args) in self._watchlist.get(guild.id, [])):
                self._watchlist[guild.id].remove(int(args))
            await self.save_config(guild)

    @admin_command(commands)
    async def whitelist(self, args, context, admin_for=None):
        for guild in admin_for:
            if (int(args) not in self._whitelist.setdefault(guild.id, [])) and int(args) in [x.id for x in guild.channels]:
                self._whitelist[guild.id].append(int(args))
            await self.save_config(guild)

    @admin_command(commands)
    async def unwhitelist(self, args, context, admin_for=None):
        for guild in admin_for:
            if (int(args) in self._whitelist.get(guild.id, [])):
                self._whitelist[guild.id].remove(int(args))
            await self.save_config(guild)

    @admin_command(commands)
    async def private_queue(self, args, context, admin_for=None):
        for guild in admin_for:
            if len(args) == 0:
                self._privateChannelQueue.pop(guild.id)
            elif int(args) in [x.id for x in guild.voice_channels]:
                self._privateChannelQueue[guild.id] = int(args)
            await self.save_config(guild)

    @command(commands)
    async def join(self, args, context):
        channel = context.user.voice.channel
        await channel.connect()

    @admin_command(commands)
    async def mod(self, args, context, admin_for=None):
        for target in context.message.mentions:
            mods = self._moderators.setdefault(context.guild.id, [])
            if (target.id not in mods):
                mods.append(target.id)
        await context.channel.send(content=str(self._moderators))

    @admin_command(commands)
    async def unmod(self, args, context, admin_for=None):
        for target in context.message.mentions:
            mods = self._moderators.setdefault(context.guild.id, [])
            if (target.id in mods):
                mods.remove(target.id)
        await context.channel.send(content=str(self._moderators))

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))
        if(message.guild == None or (message.author == message.guild.owner or message.author.id in self._moderators.get(message.guild.id, []))):
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
        if before.channel:
            channel = before.channel
            category = channel.category_id
            switched_channel = channel == after.channel

            current_members = channel.members

            is_empty = len(current_members) == 0
            channel_id = channel.id
            if(is_empty and category in self._watchlist.get(channel.guild.id, []) and channel_id not in self._whitelist.get(channel.guild.id, [])):
                await channel.delete()

        if after.channel:
            for after.channel.id in [self._privateChannelQueue[after.channel.guild.id]]:
                channel = after.channel
                guild = channel.guild
                watched = self._watchlist.get(guild.id, [])
                if len(watched) is None:
                    break
                category = guild.get_channel(watched[0])
                overwrites = {
                        guild.me: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True, connect=True),
                        guild.default_role: discord.PermissionOverwrite(manage_channels=False, connect=False, create_instant_invite=True),
                        member: discord.PermissionOverwrite(move_members=True, mute_members=True, deafen_members=True),
                }
                new_voie = await category.create_voice_channel("Private channel", reason=f"Requested by {member.name}#{member.discriminator}", overwrites=overwrites)
                await member.move_to(new_voie, reason="Moved to newly created channel")

    async def on_guild_channel_create(self, channel):
        if (channel.category_id not in self._watchlist.get(channel.guild.id, [])):
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
                if(channel.category_id in self._watchlist.get(channel.guild.id, []) and channel.id not in self._whitelist.get(channel.guild.id, []) and (channel.type != discord.ChannelType.voice or len(channel.members) == 0 )):
                    await channel.delete()

    async def init_config(self):
        for guild in self.guilds:
            if guild.owner.dm_channel is None:
                await guild.owner.create_dm()
            async for config in guild.owner.dm_channel.history():
                if config.author == guild.owner:
                    continue
                print(config)
                for line in config.content.splitlines():
                    class FakeDiscordMessage:
                        pass
                    message = FakeDiscordMessage()
                    message.author = guild.owner
                    message.channel = guild.owner.dm_channel
                    message.content = line
                    message.guild = guild
                    await self.on_message(message)
                break

    def get_commands(self, guild):
        commands = "\n".join(["!watch " + str(x) for x in self._watchlist.get(guild.id, [])]
                            +["!whitelist " + str(x) for x in self._whitelist.get(guild.id, [])]
                            +["!private_queue " + str(x) for x in [self._privateChannelQueue.get(guild.id, None)] if x is not None])
        if len(commands) == 0:
            return "No config"
        return commands

    async def save_config(self, guild = None):
        guilds = [guild] if guild else self.guilds
        for guild in guilds:
            if guild.owner is not None:
                if guild.owner.dm_channel is None:
                    await guild.owner.create_dm()
                async for message in guild.owner.dm_channel.history():
                    if message.author == guild.owner:
                        continue
                    if message.content != self.get_commands(guild):
                        await message.edit(content=self.get_commands(guild))
                    break
                else:
                    guild.owner.dm_channel.send(content=self.get_commands(guild))




client = MyClient()
client.run(api_token)

