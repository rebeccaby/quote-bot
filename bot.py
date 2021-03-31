import discord
from discord.ext import commands
from discord.utils import get
import pymongo
from pymongo import MongoClient
from youtube_dl import YoutubeDL
import urllib.parse
import logging
import asyncio

logging.basicConfig(level=logging.INFO)

# Establish client connection and choose command prefix
client = commands.Bot(command_prefix='!', help_command=None, max_messages=20)

# Keeping token, credentials out of src
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
    my_query = { "_id": message.author.id }

    # User isn't in db
    if (collection.count_documents(my_query) == 0):
        post = {
            "_id": message.author.id,
            "author_name": message.author.name,
            "saved_by": ctx.author.id,
            "quotes": [message.content]
        }
        collection.insert_one(post)
        return True
    # User is already in db
    else:
        collection.update_one(my_query, {"$push": {"quotes": message.content}})
        return True
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

# Help command - display information about commands/syntax
@client.command()
async def help(ctx):
    help_embed = discord.Embed(title="Quote Bot Help")
    await ctx.channel.send(embed=help_embed)

# Join command - bot joins a voice channel
@client.command()
async def join(ctx):
    channel = None
    if ctx.author.voice is not None:
        channel = ctx.author.voice.channel
    if channel is None:
        print(f">>> Failed; {ctx.author.name} not in a VC.")
        await ctx.channel.send(f"{ctx.author.id}, you're not connected to a voice channel!")
    elif client.voice_clients:
        print(f">>> Failed; already in {client.voice_clients[0].channel.name}.")
        await ctx.channel.send("Already connected to a voice channel!")
    else:
        print(f">>> Joining {ctx.author.name}'s VC - {channel.name}")
        await channel.connect()

# Leave command - bot leaves a voice channel
@client.command()
async def leave(ctx):
    if not client.voice_clients:
        print(f">>> No VC connections.")
        await ctx.channel.send("Not connected to a voice channel!")
    else:
        print(f">>> Leaving VC - {client.voice_clients[0].channel.name}")
        await ctx.voice_client.disconnect()

# Play command - bot plays a youtube video in voice channel
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

# Pause command - bot pauses the playing video
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

# Resume command - bot resumes the playing video
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

# Stop command - bot stops playing anything
@client.command()
async def stop(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing() or voice.is_paused():
        voice.stop()
    else:
        await ctx.channel.send("Nothing is playing or paused.")

# Destroy command - delete bot's video playlist
@client.command()
async def destroy(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
    song_queue.clear()
    await ctx.channel.send("Playlist destroyed.")

# Quote command - bot stores a user's quote
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
                    '''
                    quote_confirmation = await ctx.channel.send("Save this quote?")
                    quote_confirmation.add_reaction("✅")
                    '''
                    if add_quote_to_db(ctx, message):
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
        if add_quote_to_db(ctx, message):
            await ctx.channel.send("Quote saved.")
        else:
            await ctx.channel.send("Quote already saved or saving was unsuccessful.")

    else:
        await ctx.channel.send(f"<@{ctx.author.id}>, cannot process command!")

@client.command()
async def view(ctx, arg):
    # Check that user reacted to right message
    def check(reaction, user):
        return reaction.message.id == ctx.channel.last_message_id and user == ctx.author and (str(reaction.emoji == "👉") or str(reaction.emoji == "👈"))
    
    if arg[0:3] == "<@!" and arg[-1] == ">":
        pinged_user_id = int(arg[3:-1])
        
        # Fetching user's quotes from db
        find_query = { "_id": pinged_user_id }
        user_collection = collection.find_one(find_query)
        user_quotes = user_collection['quotes']
        num_of_quotes = len(user_quotes)

        # Getting user's pfp
        user_id = await client.fetch_user(user_collection['_id'])
        user_avatar_url = user_id.avatar_url

        # Prepping embed to show quotes
        embed = discord.Embed(title=user_collection['author_name'])
        embed.add_field(name="Quote", value=user_quotes[0], inline=False)
        embed.set_footer(text=f"Quote 1/{num_of_quotes}", icon_url=user_avatar_url)
        
        # Send and save embed to focus on it
        await ctx.channel.send(embed=embed)
        await asyncio.sleep(0.5)
        async for message in ctx.channel.history(limit=10):
            if message.author.bot is True:
                bot_quote_embed_message = message
                break

        # "Buttons" for scrolling
        await bot_quote_embed_message.add_reaction("👈")
        await bot_quote_embed_message.add_reaction("👉")

        i = 0

        while True:
            try:
                reaction, user = await client.wait_for('reaction_add', timeout=15.0, check=check)
                
                # Scroll left
                if reaction.emoji == "👈":
                    await bot_quote_embed_message.remove_reaction("👈", user)
                    i = (i-1) % num_of_quotes
                    embed.set_field_at(index=0, name="Quote", value=user_quotes[i], inline=False)
                    embed.set_footer(text=f"Quote {i+1}/{num_of_quotes}", icon_url=user_avatar_url)
                    await bot_quote_embed_message.edit(embed=embed)

                # Scroll right
                if reaction.emoji == "👉":
                    await bot_quote_embed_message.remove_reaction("👉", user)
                    i = (i+1) % num_of_quotes
                    embed.set_field_at(index=0, name="Quote", value=user_quotes[i], inline=False)
                    embed.set_footer(text=f"Quote {i+1}/{num_of_quotes}", icon_url=user_avatar_url)
                    await bot_quote_embed_message.edit(embed=embed)

            # Stop responding to reactions
            except asyncio.TimeoutError:
                break
    else:
        await ctx.channel.send("Must ping a valid user.")
        
# Message event handler
@client.event
async def on_message(ctx):
    if ctx.author == client.user:
        return

    # Console-logging all messages
    print(ctx.created_at.strftime("%m/%d/%y @ %H:%M:%S%p "), end="")
    print(f"#{ctx.channel} => {ctx.author}: {ctx.content}")

    # Tim
    if ctx.content == "ouo)/":
        await ctx.channel.send(r"\\(ouo")
    if ctx.content == r"\\(ouo":
        await ctx.channel.send("ouo)/")

    # Kryzl
    awam = "awam"
    if awam in ctx.content:
        await ctx.channel.send("Please respond...")

    # Executes user commands
    await client.process_commands(ctx)

client.run(token)