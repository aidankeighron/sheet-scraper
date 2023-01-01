import requests
import json
import keys

def retrieve_messages(channelID):
    headers = {
        "authorization": "Bot " + str(keys.DISCORD_AUTH)
    }
    r = requests.get(f"https://discord.com/api/v9/channels/{channelID}/messages?limit=100", headers=headers)
    data = json.loads(r.text)
    return data
        
def get_sheet_id(data):
    ids = []
    user = []
    for value in data:
        try:
            id = value["content"].split("/d/")
            id[1] = id[1].split("/edit")
            ids.append(id[1][0])
            user.append(value['author']['username'])
        except:
            ...
    return (ids, user)

def get_ids():
    return get_sheet_id(retrieve_messages(keys.CHANNEL_ID))


# bot.py
import os
import discord

client = discord.Client(intents=discord.Intents.default())
messages = []
users = []

import platform
import asyncio
if platform.system() == 'Windows':
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@client.event
async def on_ready():
    firstTime = True
    for guild in client.guilds:
        for channel in guild.channels:
            if channel.name == "spreadsheets":
                if firstTime:
                    firstTime = False
                    continue

                for thread in channel.threads:
                    async for message in thread.history(limit=100):
                        if "spreadsheets/d/" in message.content:
                            id = message.content.split("/d/")
                            id[1] = id[1].split("/edit")
                            messages.append(id[1][0])
                            users.append(message.author.name)
                            break
                break
    await client.close()


def get_forum_ids():
    client.run(keys.DISCORD_AUTH)
    return (messages, users)