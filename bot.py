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
client = commands.Bot(command_prefix="$", help_command=None)

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

# For holding song playlists when single-video URLs are passed
songs_to_play = []

# Connect event handler
@client.event
async def on_ready():
    print(f"{client.user} is now connected on Discord.")

# Help command
@client.command()
async def help(ctx):
    pass

# Join command
@client.command()
async def join(ctx):

    # maybe use is_connected() instead
    
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

    YDL_OPTIONS = {"format": "bestaudio", "noplaylist": "True"}
    FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
    
    voice = get(client.voice_clients, guild=ctx.guild)

    if not voice.is_playing():
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(yt_url, download=False)
        URL = info['formats'][0]['url']
        voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
        
        await ctx.channel.send(f"Now playing: {info['title']}")
    else:
        await ctx.channel.send("Already playing song.")

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

    #if not voice.is_playing() or voice.is_paused()
    
    voice.stop()

# Destroy command
@client.command()
async def destroy(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
    songs_to_play.clear()
    await ctx.channel.send("Playlist destroyed.")

# Quote command
@client.command()
async def q(ctx, *args): # *args so I can add 2-arg $q command later on
    await client.wait_until_ready()

    if len(args) > 2:
        await ctx.channel.send(f"<@{ctx.author.id}>, cannot process command!")
    else:
        if len(args) == 1:
            # $q <@user>
            if args[0][0:3] == "<@!" and args[0][-1] == ">":
                user_id = int(args[0][3:-1])
                has_messaged = False
                async for message in ctx.channel.history(limit=MSG_LIMIT):
                    if message.author.id == user_id and not has_messaged:
                        has_messaged = True
                        print(message.created_at.strftime("%m/%d/%y @ %H:%M:%S %p"))
                        print(f"\t[ {message.content} ]")
                        
                        post = {
                            "author_id": message.author.id,
                            "author_name": message.author.name,
                            "time": message.created_at.time(),
                            "date": message.created_at.date(),
                            "quote": message.content,
                            "saved_by": ctx.author.id
                        }

                        await ctx.channel.send(f"{message.content} - {message.author.name}")
                    elif message.author.id == user_id and has_messaged:
                        break
                    else:
                        print("User hasn't sent any messages.")
                
                #await ctx.channel.history(limit=20).find(lambda m : m.author.id == user_id)

            # $q 

            '''
            elif args[0].startswith("https://discord.com/channels/"):
                message_link = args[0].split("/")

                guild_id = int(message_link[4])
                channel_id = int(message_link[6])
                message_id = int(message_link[5])

                guild = client.get_guild(guild_id)
                channel = guild.get_channel(channel_id) # NoneType for some reason, related to on_ready()
                message = await channel.fetch_message(message_id)
                await ctx.channel.send(message)
            '''

        else:
            await ctx.channel.send(f"<@{ctx.author.id}>, command received!")

# Message event handler
@client.event
async def on_message(ctx):
    if ctx.author == client.user:
        return

    print(f"#{ctx.channel}: {ctx.author}: {ctx.content}")

    # Coroutine - triggers registered commands
    await client.process_commands(ctx)

client.run(token)