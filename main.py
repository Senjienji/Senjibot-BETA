import discord
from discord.ext import commands
from discord import app_commands, utils
import asyncpg
from dotenv import load_dotenv()
import datetime
import asyncio
import os

load_dotenv()


class SenjibotBETA(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.test_guild = discord.Object(kwargs.pop('test_guild'))
        self.db = None
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.db = await asyncpg.create_pool(
            host=os.environ['POSTGRESQL_HOST'],
            port=os.environ['POSTGRESQL_PORT'],
            password=os.environ['POSTGRESQL_PASSWORD',
            user='bot',
            database='senjibot'
        )
        for filename in os.listdir('cogs'):
            if filename == '__pycache__': continue
            await self.load_extension('cogs.'+filename.split('.')[0])

        self.tree.copy_global_to(guild=self.test_guild)
        self.launch_time = utils.utcnow()

bot = SenjibotBETA(
    command_prefix='s?',
    owner_id=902371374033670224,
    test_guild=809722018953166858,
    help_command=None,
    allowed_mentions=discord.AllowedMentions.none(),
    intents=discord.Intents.all(),
    activity=discord.CustomActivity(name='epok'),
    status=discord.Status.idle
)

@bot.check
async def owner_check(ctx):
    return await bot.is_owner(ctx.author)

@bot.event
async def on_connect():
    print('Connected.')

@bot.event
async def on_ready():
    print('Ready.')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure): return
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
    await ctx.reply(f'Ping! {int(bot.latency*1000)}ms.')

@bot.command()
async def send(ctx, channel: discord.TextChannel, *, message):
    await channel.send(message)
    await ctx.message.add_reaction('\U00002705')

@bot.command()
async def sync(ctx):
    await bot.tree.sync(guild=bot.test_guild)
    await ctx.message.add_reaction('\U00002705')

@bot.command()
async def uptime(ctx):
    await ctx.reply(f'Uptime: {utils.format_dt(bot.launch_time, style="R")}')

@bot.command(name='load-cog', aliases=('lc',))
async def load_cog(ctx, cog):
    if 'cogs.'+cog in bot.extensions:
        await bot.reload_extension('cogs.'+cog)
        await ctx.reply(f'Cog "{cog}" reloaded.')
    else:
        await bot.load_extension('cogs.'+cog)
        await ctx.reply(f'Cog "{cog}" loaded.')

@bot.command(name='unload-cog', aliases=('uc',))
async def unload_cog(ctx, cog):
    if 'cogs.'+cog in bot.extensions:
        await bot.unload_extension('cogs.'+cog)
        await ctx.reply(f'Cog "{cog}" unloaded.')
    else:
        await ctx.reply(f'Cog "{cog}" not loaded.')

@bot.command(name='eval', aliases=('e',))
async def evaluate(ctx, *, code):
    await ctx.reply(eval(code))

@bot.tree.command(name='ping')
async def slashping(inter):
    await inter.response.send_message(f'Ping! {int(bot.latency*1000)}ms.')

person = app_commands.Group(name='person', description='...')

@person.command()
async def add(inter, name: str, email: str=None):
    async with bot.db.acquire() as conn:
        try:
            await conn.execute('INSERT INTO person (name, email) VALUES ($1, $2);', name, email)
            await inter.response.send_message(f'Added "{name}".')
        except asyncpg.exceptions.UniqueViolationError:
            await inter.response.send_message('Error: This email has already been used. Please use another email.')

@person.command()
async def remove(inter, name: str):
    async with bot.db.acquire() as conn:
        status = await conn.execute('DELETE FROM person WHERE name = $1;', name)
        if status.split()[1]:
            await inter.response.send_message(f'Removed "{name}".')
        else:
            await inter.response.send_message(f'"{name}" not found.')

@person.command()
async def edit(inter, name: str, email: str=None):
    async with bot.db.acquire() as conn:
        status = await conn.execute('UPDATE person SET email = $2 WHERE name = $1;', name, email)
        if status.split()[1]:
            await inter.response.send_message(f'Edited "{name}".')
        else:
            await conn.execute('INSERT INTO person (name, email) VALUES ($1, $2)', (name, email))
            await inter.response.send_message(f'"{name}" not found, added instead.')

@person.command(name='list')
async def names(inter):
    async with bot.db.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM person;')
    await inter.response.send_message('\n'.join(f'{r["name"]}: `{r["email"]}`' for r in rows))

bot.tree.add_command(person)

bot.run(os.environ['SENJIBOT_BETA_TOKEN'])
asyncio.run(bot.db.close())
