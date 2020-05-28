import discord
from secret import api_token
from time import sleep, time
from datetime import datetime, timedelta, timezone
import asyncio

text_message_timeout = 10
voice_timeout = 5
command_prefix = "!"


class MyClient(discord.Client):
    watchlist = {}
    watched_categories = []
    whitelist = []
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.cleanup()

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))
        if(message.author == message.guild.owner):
            if(message.startswith(command_prefix + "watch ")):
                watched_categories += int(message.split(' ')[1])


    async def on_voice_state_update(self, member, before, after):

        channel = before.channel
        category = channel.category_id
        switched_channel = channel == after.channel

        current_members = channel.members

        is_empty = len(current_members) == 0
        channel_id = channel.id
        if(is_empty and category in self.watched_categories and channel_id not in self.whitelist):
            await channel.delete()
        
    async def on_guild_channel_create(self, channel):
        if (channel.category_id not in self.watched_categories):
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
                if(channel.category_id in self.watched_categories and channel.id not in self.whitelist and (channel.type != discord.ChannelType.voice or len(channel.members) == 0 )):
                    await channel.delete()




client = MyClient()
client.run(api_token)

