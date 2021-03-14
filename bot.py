import discord
from discord.ext import commands
import pymongo
from pymongo import MongoClient
import urllib.parse
import time
import datetime

# Establish client connection and choose command prefix
client = commands.Bot(command_prefix="$")

# Separating sensitive information from src
token = open("token.txt").read()
with open("cred.txt") as file:
    lines = [line.strip() for line in file]
name = lines[0]
pw = urllib.parse.quote_plus(lines[1])

# Connect to database
mongo_url = "mongodb+srv://" + name + ":" + pw + "@discordbot.zwzas.mongodb.net/test"
cluster = MongoClient(mongo_url)
db = cluster["QuoteBot"]
collection = db["QuoteBot"]

# Global constants
MSG_LIMIT = 10

# Connect event handler
@client.event
async def on_ready():
    print(f"{client.user} is now connected on Discord.")

# Quote command
@client.command()
async def quote(ctx, *args):
    await client.wait_until_ready()

    #print("{} arguments: {}".format(len(args), ", ".join(args)))

    if len(args) > 2:
        await ctx.channel.send(f"<@{ctx.author.id}>, cannot process command!")
    else:
        if len(args) == 1:
            # $quote <@user>
            if args[0][0:3] == "<@!" and args[0][-1] == ">":
                user_id = int(args[0][3:-1])
                has_messaged = False
                async for message in ctx.channel.history(limit=MSG_LIMIT):
                    if message.author.id == user_id and not has_messaged:
                        has_messaged = True
                        print(message.created_at.strftime("%m/%d/%y @ %H:%M:%S %p"))
                        print(f"\t[ {message.content} ]")
                    elif message.author.id == user_id and has_messaged:
                        break
                    else:
                        print("User hasn't sent any messages.")
                
                #await ctx.channel.history(limit=20).find(lambda m : m.author.id == user_id)

            '''elif args[0].startswith("https://discord.com/channels/") is True:
                message_link = args[0].split("/")

                guild_id = int(message_link[4])
                channel_id = int(message_link[6])
                message_id = int(message_link[5])

                guild = client.get_guild(guild_id)
                channel = guild.get_channel(channel_id) # NoneType for some reason
                message = await channel.fetch_message(message_id) <- returns NoneType 
                await ctx.channel.send(message)'''

        else:
            await ctx.channel.send(f"<@{ctx.author.id}>, command received!")

# Message event handler
@client.event
async def on_message(ctx):
    print(f"#{ctx.channel}: {ctx.author}: {ctx.content}")

    # Coroutine - triggers registered commands
    await client.process_commands(ctx)

client.run(token)