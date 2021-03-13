import discord
from discord.ext import commands
import pymongo
from pymongo import MongoClient
import urllib.parse

# Establish client connection and choose command prefix
client = commands.Bot(command_prefix="$")

with open("cred.txt") as file:
    lines = [line.strip() for line in file]
name = lines[0]
pw = urllib.parse.quote_plus(lines[1])

# Connect to database
mongo_url = "mongodb+srv://" + name + ":" + pw + "@discordbot.zwzas.mongodb.net/test"
cluster = MongoClient(mongo_url)
db = cluster["QuoteBot"]
collection = db["QuoteBot"]

# Fetch token id
token = open("token.txt").read()

# Connect event handler
@client.event
async def on_ready():
    print(f"{client.user} is now connected on Discord.")

# Quote command
@client.command()
async def quote(ctx, *args):
    await ctx.channel.send("{} arguments: {}".format(len(args), ", ".join(args)))

# Message event handler
@client.event
async def on_message(ctx):
    print(f"#{ctx.channel}: {ctx.author}: {ctx.content}")
    
    # Create query for user id
    myquery = {"_id": ctx.author.id}
    
    # If entity doesn't already exist, create one
    if (collection.count_documents(myquery) == 0):
        if ctx.content.lower() == "ping":
            post = {"_id": ctx.author.id, "score": 1}
            collection.insert_one(post)
            await ctx.channel.send("pong - 0")

    # If entity exists, increment by 1
    else:
        if ctx.content.lower() == "ping":
            query = {"_id": ctx.author.id}
            user = collection.find(query)
            for result in user:
                score = result["score"]
            collection.update_one({"_id": ctx.author.id}, {"$set": {"score": score + 1}})
            await ctx.channel.send(f"pong - {score}")

    # Coroutine - triggers registered commands
    await client.process_commands(ctx)

client.run(token)