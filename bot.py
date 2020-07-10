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
    _privateChannelSpawn = {}
    _privateChannelQueue = {}
    _privateCategory = {}
    _privateChannelMessages = {}
    _startupCompleted = False

    def allWatchlist(self, guild_id):
        return self._watchlist.get(guild_id, []) + [x for x in [self._privateCategory.get(guild_id, None)] if x is not None]

    def allWhitelist(self, guild_id):
        return self._whitelist.get(guild_id, []) + [x for x in [self._privateChannelSpawn.get(guild_id, None)
                                                               ,self._privateChannelQueue.get(guild_id, None)
                                                               ,self._privateChannelMessages.get(guild_id, None)] if x is not None]

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.init_config()
        await self.cleanup()
        self._startupCompleted = True

    # @command(commands)
    # async def print(self, args, context):
    #    await context.channel.send(content=str(args))

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
    async def private_spawn(self, args, context, admin_for=None):
        for guild in admin_for:
            if len(args) == 0:
                self._privateChannelSpawn.pop(guild.id)
            elif int(args) in [x.id for x in guild.voice_channels]:
                self._privateChannelSpawn[guild.id] = int(args)
            await self.save_config(guild)

    @admin_command(commands)
    async def private_control(self, args, context, admin_for=None):
        for guild in admin_for:
            if len(args) == 0:
                self._privateChannelMessages.pop(guild.id)
            elif int(args) in [x.id for x in guild.text_channels]:
                self._privateChannelMessages[guild.id] = int(args)
            await self.save_config(guild)

    @admin_command(commands)
    async def private_category(self, args, context, admin_for=None):
        for guild in admin_for:
            if len(args) == 0:
                self._privateCategory.pop(guild.id)
            elif int(args) in [x.id for x in guild.categories]:
                self._privateCategory[guild.id] = int(args)
            await self.save_config(guild)

    @admin_command(commands)
    async def private_waitroom(self, args, context, admin_for=None):
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
            for line in message.content.splitlines():
                if (line.startswith(command_prefix)):
                    msg = line[len(command_prefix):].lower()
                    if (' ' in msg):
                        cmd, args = msg.split(' ', 1)
                    else:
                        cmd = msg
                        args = ""
                    if (cmd in commands):
                        context = CommandtCtx(channel=message.channel, user=message.author, guild=message.guild, message=message)
                        await commands[cmd](self, args, context)

    async def on_message_edit(self, before, after):
        if type(after.channel) == discord.DMChannel and before.content != after.content:
            return await self.on_message(after)

    async def on_reaction_add(self, reaction, user):
        if reaction.message.author == reaction.message.channel.guild.me and \
           user != reaction.message.channel.guild.me and \
           reaction.message.channel.id == self._privateChannelMessages.get(reaction.message.channel.guild.id, None):
            if reaction.emoji == '👍':
                try:
                    [invitee] = reaction.message.mentions
                    [channel] = reaction.message.channel_mentions
                    if user in channel.members:
                        await channel.set_permissions(invitee, connect=True, speak=True, stream=True, reason=f"User was accepted to join the group by {user.name}#{user.discriminator}")
                        await reaction.message.clear_reactions()
                        await reaction.message.edit(content=f"User {invitee.mention} can now join the voice channel.", delete_after=300)
                        queueChannel = self._privateChannelQueue.get(reaction.message.channel.guild.id)
                        if queueChannel is not None:
                            queueChannel = reaction.message.channel.guild.get_channel(queueChannel)
                            if queueChannel is not None:
                                member = next((x for x in queueChannel.members if x == invitee), None)
                                if member is not None:
                                    await member.move_to(channel)
                    else:
                        await reaction.remove(user)
                except ValueError:
                    await reaction.remove(user)
            else:
                await reaction.remove(user)

    async def on_voice_state_update(self, member, before, after):
        if not self._startupCompleted:
            return

        if before.channel:
            channel = before.channel
            category = channel.category_id

            current_members = channel.members

            is_empty = len(current_members) == 0
            channel_id = channel.id
            if(is_empty and category in self.allWatchlist(channel.guild.id) and channel_id not in self.allWhitelist(channel.guild.id)):
                try:
                    await channel.delete()
                except:
                    pass

        if after.channel and member is not None:
            channel = after.channel
            guild = channel.guild
            if after.channel.id == self._privateChannelSpawn[after.channel.guild.id]:
                for privateMember in [x for x in [member]]:
                    category_id = self._privateCategory.get(guild.id, (self.allWatchlist(guild.id) + [None])[0])
                    if category_id is None:
                        break
                    category = guild.get_channel(category_id)
                    overwrites = {
                            guild.me: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True, connect=True),
                            guild.default_role: discord.PermissionOverwrite(manage_channels=False, connect=True, speak=False, stream=False),
                            privateMember: discord.PermissionOverwrite(manage_channels=True, move_members=True, speak=True, stream=True),
                    }
                    new_voice = await category.create_voice_channel(f"{member.nick or member.name}'s private channel", reason=f"Requested by {privateMember.name}#{privateMember.discriminator}", overwrites=overwrites)
                    await privateMember.move_to(new_voice, reason="Moved to newly created channel")
            elif after.channel.id == self._privateChannelQueue.get(guild.id, None):
                pass
            elif after.channel.category_id == self._privateCategory.get(guild.id, None) and after.channel.overwrites_for(member).is_empty():
                channelMention = after.channel.mention
                await after.channel.set_permissions(member, connect=False)
                waitroom = self._privateChannelQueue.get(guild.id, None)
                if waitroom is not None:
                    waitroom = guild.get_channel(waitroom)
                await member.move_to(waitroom, reason="Awaiting acceptance to the private group")
                msgChannel = self._privateChannelMessages.get(guild.id, None)
                if msgChannel is not None:
                    msgChannel = guild.get_channel(msgChannel)
                    if msgChannel is not None:
                        message = await msgChannel.send(content=f"User {member.mention} wants to join private {channelMention}. Allow?", delete_after=600)
                        await message.add_reaction('👍')

    async def on_guild_channel_create(self, channel):
        if (channel.category_id not in self._watchlist.get(channel.guild.id, [])):
            return

        if (channel.type == discord.ChannelType.voice):
            await asyncio.sleep(voice_timeout)
            if(len(channel.members) == 0):
                if channel.id not in self.allWhitelist(channel.guild.id):
                    try:
                        await channel.delete()
                    except:
                        pass

        elif (channel.type == discord.ChannelType.text):
            await asyncio.sleep(text_message_timeout)
            while(len(messages := await channel.history(limit=1, oldest_first=False).flatten()) > 0):
                created_at = messages[0].created_at if messages[0].edited_at is None else messages[0].edited_at
                timeout = ((created_at + timedelta(seconds=text_message_timeout)) - datetime.utcnow()).total_seconds()
                if(timeout <= 0):
                    break
                await asyncio.sleep(timeout)
            if channel.id not in self.allWhitelist(channel.guild.id):
                try:
                    await channel.delete()
                except:
                    pass



    async def cleanup(self):
        for server in self.guilds:
            for channel in server.channels:
                if(channel.category_id in self.allWatchlist(channel.guild.id) and channel.id not in self.allWhitelist(channel.guild.id) and (channel.type != discord.ChannelType.voice or len(channel.members) == 0 )):
                    try:
                        await channel.delete()
                    except:
                        pass
            botMsgs = self._privateChannelMessages.get(server.id, None)
            if botMsgs is not None:
                botMsgs = server.get_channel(botMsgs)
                if botMsgs is not None:
                    await botMsgs.purge(before=datetime.now() - timedelta(days=1), oldest_first=True)

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
                            +["!private_spawn " + str(x) for x in [self._privateChannelSpawn.get(guild.id, None)] if x is not None]
                            +["!private_waitroom " + str(x) for x in [self._privateChannelQueue.get(guild.id, None)] if x is not None]
                            +["!private_control " + str(x) for x in [self._privateChannelMessages.get(guild.id, None)] if x is not None]
                            +["!private_category " + str(x) for x in [self._privateCategory.get(guild.id, None)] if x is not None])
        if len(commands) == 0:
            return "No config"
        return commands

    async def save_config(self, guild = None):
        if not self._startupCompleted:
            return
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

