import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector

bot = commands.Bot(
    command_prefix="s?",
    owner_id="902371374033670224",
    help_command=None,
    allowed_mentions=discord.AllowedMentions(
        replied_user=False
    ),
    intents=discord.Intents.all()
)
database = mysql.connector.connect(
    host="127.0.0.1",
    user="user",
    password="password",
    database="senjibot"
)
cursor = database.cursor()
test_guild = discord.Object(809722018953166858)

@bot.event
async def on_connect():
    bot.tree.copy_global_to(guild=test_guild)
    print("Connected")

@bot.event
async def on_ready():
    print("Ready")

@bot.event
async def on_command_error(ctx, error):
    try:
        await ctx.reply(error)
    except:
        pass
    finally:
        await commands.Bot.on_command_error(bot, ctx, error)

@bot.tree.error
async def on_error(inter, error):
    if inter.response.is_done():
        await inter.edit_original_response(content=error)
    else:
        await inter.response.send_message(error)
    await app_commands.CommandTree.on_error(bot.tree, inter, error)

@bot.command()
async def ping(ctx):
    await ctx.reply(f"Ping! {int(bot.latency*1000)}ms")

@bot.command()
async def send(ctx, channel: discord.TextChannel, *, message):
    await channel.send(message)
    await ctx.message.add_reaction("\U00002705")

@bot.command()
async def sync(ctx):
    await bot.tree.sync(guild=test_guild)
    await ctx.message.add_reaction("\U00002705")

@bot.tree.command(name="ping")
async def ping2(inter):
    await inter.response.send_message(f"Ping! {int(bot.latency*1000)}ms")

@bot.tree.command(name="send")
async def send2(inter, channel: discord.TextChannel, message: str):
    await inter.response.defer(ephemeral=True)
    await channel.send(message)
    await inter.followup.send("Sent")

person = app_commands.Group(name="person", description="...")

@person.command()
async def add(inter, first_name:str, last_name:str=None, birthdate:str=None, address:str=None):
    pass

@person.command()
async def remove(inter, first_name:str):
    pass

@person.command()
async def edit(inter, first_name:str, last_name:str=None, birthdate:str=None, address:str=None):
    pass #bleh

@person.command(name="list")
async def names(inter):
    await inter.response.defer()
    cursor.execute("SELECT * FROM person")
    await inter.response.send_message("\n".join(f"{i}" for i in cursor.fetchall()))

bot.tree.add_command(person)

bot.run("MTA0NzgzODI3MDQzMzc4NzkzNQ.GGyDiP.3fbeVqDaEWo3l2EIFgjTVm-AFIfOD0Uyw_RWgE")

