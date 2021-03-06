import discord
from discord.ext import commands
from discord.utils import get
import pymongo
from pymongo import MongoClient
from youtube_dl import YoutubeDL
import urllib.parse
import asyncio

# Keeping client token & mongodb credentials out of src
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

# Establish client connection and choose command prefix
client = commands.Bot(command_prefix='!', help_command=None, max_messages=20)

# Global vars
MSG_LIMIT = 10
song_queue = []

def add_user_to_db(ctx, message) -> bool:
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
    def check(reaction, user):
        return help_embed_message == reaction.message and user == ctx.author and (str(reaction.emoji) == "👈" or str(reaction.emoji) == "👉")
    
    help_embed = discord.Embed(title="Quote Bot Help")

    help_embed_list = []

    # Keeping one embed, removing and adding new fields, and appending to list didn't work.

    # Quote commands
    quote_help_embed = discord.Embed(title="Quote Bot Help", description="Commands for quoting.")
    quote_help_embed.add_field(name="!quote", value= "!quote @user\n!quote <message-link>\nSaves a user's quote.", inline=False)
    quote_help_embed.add_field(name="!view", value="!view @user\nDisplays all of a user's quotes.", inline=False)
    help_embed_list.append(quote_help_embed)

    # Voice Channel commands
    vc_help_embed = discord.Embed(title="Quote Bot Help", description="Commands for voice channel interaction.")
    vc_help_embed.add_field(name="!join", value="Joins the same voice channel as the author's.", inline=False)
    vc_help_embed.add_field(name="!leave", value="Leaves the voice channel, if in one.", inline=False)
    help_embed_list.append(vc_help_embed)

    # Music commands
    music_help_embed = discord.Embed(title="Quote Bot Help", description="Commands for music.")
    music_help_embed.add_field(name="!play", value="!play <youtube-link>\nPlays the linked song, or queues it if another song is playing.", inline=False)
    music_help_embed.add_field(name="!pause", value="Pauses the current song, if playing.", inline=False)
    music_help_embed.add_field(name="!resume", value="Resumes the current song, if paused.", inline=False)
    music_help_embed.add_field(name="!stop", value="Stops playing the current song.", inline=False)
    music_help_embed.add_field(name="!destroy", value="Stops playing the current song, and destroys the song queue.", inline=False)
    help_embed_list.append(music_help_embed)

    for embed in help_embed_list:
        embed.set_thumbnail(url=client.user.avatar_url)
        # put author icon url here

    help_embed_message = await ctx.channel.send(embed=help_embed_list[0])

    await help_embed_message.add_reaction("👈")
    await help_embed_message.add_reaction("👉")

    i = 0

    while True:
        try:
            reaction, user = await client.wait_for('reaction_add', timeout=15.0, check=check)

            scroll = False

            if reaction.emoji == "👈":
                await help_embed_message.remove_reaction("👈", user)
                i = (i-1) % len(help_embed_list)
                scroll = True
            if reaction.emoji == "👉":
                await help_embed_message.remove_reaction("👉", user)
                i = (i+1) % len(help_embed_list)
                scroll = True

            if scroll is True:
                await help_embed_message.edit(embed=help_embed_list[i])

        except asyncio.TimeoutError:
            break

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
    def check(reaction, user):
        return quote_confirmation == reaction.message and user == ctx.author and (str(reaction.emoji) == "✅" or str(reaction.emoji) == "⛔")

    await client.wait_until_ready()

    if arg is None:
        await ctx.channel.send("No argument provided.")
        return

    # !quote @user
    if arg[0:3] == "<@!" and arg[-1] == ">":
        user_id = int(arg[3:-1])
        user_has_messaged = False

        last_message_in_channel = await ctx.channel.fetch_message(ctx.channel.last_message_id)

        # Check channel's history for pinged user's most recent message to save as a quote
        async for message in ctx.channel.history(limit=MSG_LIMIT):
            # Always skip most recent message (the command message)
            if message == last_message_in_channel:
                continue

            if message.author.id == user_id and not user_has_messaged:
                user_has_messaged = True
                quote_confirmation = await ctx.channel.send(f"Save this quote? - {message.content}")
                await quote_confirmation.add_reaction("✅")
                await quote_confirmation.add_reaction("⛔")
                try:
                    reaction, user = await client.wait_for('reaction_add', timeout=10.0, check=check)

                    if reaction.emoji == "✅":
                        if add_user_to_db(ctx, message):
                            await ctx.channel.send("Quote saved.")
                        else:
                            await ctx.channel.send("Quote already saved or saving was unsuccessful.")
                    if reaction.emoji == "⛔":
                        return
                except asyncio.TimeoutError:
                    await ctx.channel.send("Time is up.")
                
            elif message.author.id == user_id and user_has_messaged:
                break
            else:
                print("User hasn't sent any messages.")

    #  !quote <message-link>
    elif arg.startswith("https://discord.com/channels/"):
        message_link = arg.split("/")
        message_id = int(message_link[-1])
        message = await ctx.channel.fetch_message(message_id)
        if add_user_to_db(ctx, message):
            await ctx.channel.send("Quote saved.")
        else:
            await ctx.channel.send("Quote already saved or saving was unsuccessful.")

    else:
        await ctx.channel.send(f"<@{ctx.author.id}>, cannot process command!")

@client.command()
async def view(ctx, arg):
    # Check that user reacted to right message
    def check(reaction, user):
        return reaction.message == quote_embed_message and user == ctx.author and (str(reaction.emoji) == "👉" or str(reaction.emoji) == "👈")
    
    if arg[0:3] == "<@!" and arg[-1] == ">":
        pinged_user_id = int(arg[3:-1])
        
        # Fetching user's quotes from db
        find_query = { "_id": pinged_user_id }
        user_collection = collection.find_one(find_query)
        user_quotes = user_collection['quotes']

        # Getting user's pfp
        user_id = await client.fetch_user(user_collection['_id'])
        user_avatar_url = user_id.avatar_url

        # Prepping embed to show quotes
        quote_embed = discord.Embed(title=user_collection['author_name'])
        quote_embed.add_field(name="Quote", value=user_quotes[0], inline=False)
        quote_embed.set_footer(text=f"Quote 1/{len(user_quotes)}", icon_url=user_avatar_url)
        
        # Send and save embed to focus on it later
        quote_embed_message = await ctx.channel.send(embed=quote_embed)

        # "Buttons" for scrolling
        await quote_embed_message.add_reaction("👈")
        await quote_embed_message.add_reaction("👉")

        # Keeping track of which quote is displayed
        i = 0

        while True:
            try:
                # Wait for user to scroll...
                reaction, user = await client.wait_for('reaction_add', timeout=15.0, check=check)
                
                scroll = False

                # Scroll left
                if reaction.emoji == "👈":
                    await quote_embed_message.remove_reaction("👈", user)
                    i = (i-1) % len(user_quotes) # prevents out-of-range indexing
                    scroll = True

                # Scroll right
                if reaction.emoji == "👉":
                    await quote_embed_message.remove_reaction("👉", user)
                    i = (i+1) % len(user_quotes)
                    scroll = True
                
                # This would've gone in both above if's, but brought it out to not have duplicate code
                if scroll:
                    quote_embed.set_field_at(index=0, name="Quote", value=user_quotes[i], inline=False)
                    quote_embed.set_footer(text=f"Quote {i+1}/{len(user_quotes)}", icon_url=user_avatar_url)
                    await quote_embed_message.edit(embed=quote_embed)

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
    print(ctx.created_at.strftime("[%m/%d/%y @ %H:%M:%S%p] "), end="")
    print(f"#{ctx.channel} => {ctx.author}: {ctx.content}")

    # \(ouo)/
    if ctx.content == "ouo)/":
        await ctx.channel.send(r"\\(ouo")
    if ctx.content == r"\\(ouo":
        await ctx.channel.send("ouo)/")

    # :pleading_face:
    awam = "awam"
    if awam in ctx.content:
        await ctx.channel.send("Please respond...")

    # Executes user commands
    await client.process_commands(ctx)

client.run(token)