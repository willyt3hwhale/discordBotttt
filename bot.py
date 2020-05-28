import discord
from secret import api_token
from time import sleep, time
from datetime import datetime, timedelta, timezone
import asyncio


class MyClient(discord.Client):
    watched_categories = []
    whitelist = []
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.cleanup()

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))

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
    	if (channel.type != discord.ChannelType.voice):
    		await channel.delete()
    		return

    	await asyncio.sleep(30)
    	if(len(channel.members) == 0):
    		await channel.delete()



    async def cleanup(self):
    	for server in self.guilds:
    		for channel in server.channels:
    			if(channel.category_id in self.watched_categories and channel.id not in self.whitelist and (len(channel.members) == 0 or channel.type != discord.ChannelType.voice)):
    				await channel.delete()




client = MyClient()
client.run(api_token)

