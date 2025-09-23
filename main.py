import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import asyncpg
import os

class SenjibotBETA(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.test_guild = discord.Object(kwargs.pop('test_guild'))
        self.db = None
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=self.test_guild)
        self.db = await asyncpg.create_pool(
            user='bot',
            password='password',
            database='senjibot',
            host='127.0.0.1'
        )

bot = SenjibotBETA(
    command_prefix='s?',
    owner_id=902371374033670224,
    test_guild=809722018953166858,
    help_command=None,
    allowed_mentions=discord.AllowedMentions(
        replied_user=False
    ),
    intents=discord.Intents.all(),
)

@bot.event
async def on_connect():
    print('Connected')

@bot.event
async def on_ready():
    print('Ready')

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
    await ctx.reply(f'Ping! {int(bot.latency*1000)}ms')

@bot.command()
async def send(ctx, channel: discord.TextChannel, *, message):
    await channel.send(message)
    await ctx.message.add_reaction('\U00002705')

@bot.command()
async def sync(ctx):
    await bot.tree.sync(guild=bot.test_guild)
    await ctx.message.add_reaction('\U00002705')

@bot.tree.command(name='ping')
async def ping2(inter):
    await inter.response.send_message(f'Ping! {int(bot.latency*1000)}ms')

@bot.tree.command(name='send')
async def send2(inter, channel: discord.TextChannel, message: str):
    await inter.response.defer(ephemeral=True)
    await channel.send(message)
    await inter.response.send_message('Sent')

person = app_commands.Group(name='person', description='...')

@person.command()
async def add(inter, name: str, address: str=None):
    cursor.execute('INSERT INTO person (name, address) VALUES (%s, %s);', (name, address))
    db.commit()
    await inter.response.send_message(f'Added {name}.')

@person.command()
async def remove(inter, name: str):
    cursor.execute('DELETE FROM person WHERE name = %s;', (name,))
    db.commit()
    await inter.response.send_message(f'Removed {name}.')

@person.command()
async def edit(inter, name: str, address: str=None):
    cursor.execute('UPDATE person SET address = %s WHERE name = %s;', (address, name))
    db.commit()
    await inter.response.send_message(f'Edited {name}.')

@person.command(name='list')
async def names(inter):
    async with bot.db.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM person;')
    await inter.response.send_message('\n'.join(r['name']+r['email'] for r in rows))

bot.tree.add_command(person)

try:
    bot.run(os.environ['SENJIBOT_BETA_TOKEN'])
except (RuntimeError, KeyboardInterrupt):
    print('idk')
finally:
    asyncio.run(bot.db.close())
