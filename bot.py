import discord
from discord.ext import commands
from discord.utils import get
import pymongo
from pymongo import MongoClient
from youtube_dl import YoutubeDL
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO)

# Establish client connection and choose command prefix
client = commands.Bot(command_prefix='$', help_command=None)

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

# Global vars
MSG_LIMIT = 10
song_queue = []

def add_quote_to_db(ctx, message) -> bool:
    my_query = {"_id": ctx.message.id}
    if (collection.count_documents(my_query) == 0):
        post = {
            "_id": ctx.message.id,
            "author_id": message.author.id,
            "author_name": message.author.name,
            "saved_by": ctx.author.id,
            "quote": message.content
        }
        collection.insert_one(post)
        return True
    else:
        return False

def play_next_in_queue(ctx, FFMPEG_OPTIONS):
    voice = get(client.voice_clients, guild=ctx.guild)
    if len(song_queue) > 1:
        del song_queue[0]
        voice.play(discord.FFmpegPCMAudio(song_queue[0], **FFMPEG_OPTIONS), after=lambda e : play_next_in_queue(ctx, FFMPEG_OPTIONS))
        voice.is_playing()

# Connect event handler
@client.event
async def on_ready():
    print(f"{client.user} is now connected on Discord.")

# Help command
@client.command()
async def help(ctx):
    help_embed = discord.Embed(title="Quote Bot Help")
    await ctx.channel.send(embed=help_embed)

# Join command
@client.command()
async def join(ctx):
    channel = None
    if ctx.author.voice != None:
        channel = ctx.author.voice.channel
    if channel == None:
        await ctx.channel.send(f"{ctx.author.id}, you're not connected to a voice channel!")
    elif client.voice_clients:
        await ctx.channel.send("Already connected to a voice channel!")
    else:
        await channel.connect()

# Leave command
@client.command()
async def leave(ctx):
    if not client.voice_clients:
        await ctx.channel.send("Not connected to a voice channel!")
    else:
        await ctx.voice_client.disconnect()

# Play command
@client.command()
async def play(ctx, yt_url):
    if not yt_url.startswith("https://www.youtube.com/watch?v="):
        await ctx.channel.send("Not a valid YouTube URL argument!")
        return

    if not client.voice_clients:
        await ctx.invoke(client.get_command("join"))

    YDL_OPTIONS = {
        "format": "bestaudio",
        "noplaylist": "True"
    }
    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }
    
    voice = get(client.voice_clients, guild=ctx.guild)
    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(yt_url, download=False)
        song_queue.append(info['formats'][0]['url'])

    if not voice.is_playing():
        voice.play(discord.FFmpegPCMAudio(song_queue[0], **FFMPEG_OPTIONS), after=lambda e : play_next_in_queue(ctx, FFMPEG_OPTIONS))
        del song_queue[0]
        await ctx.channel.send(f"Now playing: {info['title']}")
    else:
        await ctx.channel.send("Added to queue.")

# Pause command
@client.command()
async def pause(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
    else:
        if voice.is_paused():
            await ctx.channel.send("Already paused.")
        else:
            await ctx.channel.send("Nothing is playing.")

# Resume command
@client.command()
async def resume(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        await ctx.channel.send("Song is playing.")
    else:
        if voice.is_paused():
            voice.resume()
        else:
            await ctx.channel.send("Nothing is playing or paused.")

# Stop command
@client.command()
async def stop(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing() or voice.is_paused():
        voice.stop()
    else:
        await ctx.channel.send("Nothing is playing or paused.")

# Destroy command
@client.command()
async def destroy(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
    song_queue.clear()
    await ctx.channel.send("Playlist destroyed.")

# Quote command
@client.command()
async def quote(ctx, arg=None):
    await client.wait_until_ready()

    if arg is None:
        await ctx.channel.send("No argument provided.")
        return

    # $q @user
    if arg[0:3] == "<@!" and arg[-1] == ">":
        user_id = int(arg[3:-1])
        has_messaged = False
        async for message in ctx.channel.history(limit=MSG_LIMIT):
            last_message = await ctx.channel.fetch_message(ctx.channel.last_message_id)
            if message == last_message:
                continue
            else:
                if message.author.id == user_id and not has_messaged:
                    has_messaged = True
                    success = add_quote_to_db(ctx, message)
                    if success:
                        await ctx.channel.send("Quote saved.")
                    else:
                        await ctx.channel.send("Quote already saved or saving was unsuccessful.")
                elif message.author.id == user_id and has_messaged:
                    break
                else:
                    print("User hasn't sent any messages.")

    #  $q <message-link>
    elif arg.startswith("https://discord.com/channels/"):
        message_link = arg.split("/")
        message_id = int(message_link[-1])
        message = await ctx.channel.fetch_message(message_id)
        success = add_quote_to_db(ctx, message)
        if success:
            await ctx.channel.send("Quote saved.")
        else:
            await ctx.channel.send("Quote already saved or saving was unsuccessful.")

    else:
        await ctx.channel.send(f"<@{ctx.author.id}>, cannot process command!")    
        
# Message event handler
@client.event
async def on_message(ctx):
    #print(ctx.created_at.strftime("%m/%d/%y @ %H:%M:%S%p "), end="")
    print(f"#{ctx.channel} => {ctx.author}: {ctx.content}")

    if ctx.author == client.user:
        return

    if ctx.content == "ouo)/":
        await ctx.channel.send("\\(ouo")
    if ctx.content == "\\(ouo":
        await ctx.channel.send("ouo)/")

    # Executes user commands
    await client.process_commands(ctx)

client.run(token)