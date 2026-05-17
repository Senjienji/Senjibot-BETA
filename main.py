import discord
from discord.ext import commands
from discord import app_commands, utils, ui
import asyncpg
from dotenv import load_dotenv
from typing import Optional
from logging import getLogger
import asyncio
import os

load_dotenv()
logger = getLogger(__name__)


class NewTree(app_commands.CommandTree):
    async def on_error(self, inter, error):
        try:
            async with asyncio.timeout(5):
                if inter.response.is_done():
                    await inter.followup.send(f'{type(error).__name__}: {error}')
                else:
                    await inter.response.send_message(f'{type(error).__name__}: {error}', ephemeral=True)
        except asyncio.TimeoutError:
            logger.warning('Timed out trying to notify user of error in "%s"', inter.command.name)
        except discord.HTTPException:
            logger.warning('Failed trying to notify user of error in "%s"', inter.command.name)
        await super().on_error(inter, error)


class SenjibotBETA(commands.Bot):
    def __init__(self, **kwargs):
        self.test_guild = discord.Object(kwargs.pop('test_guild'))
        self.db: asyncpg.Pool | None = None
        super().__init__(**kwargs)

    async def setup_hook(self):
        self.db = await asyncpg.create_pool(
            host=os.environ['POSTGRESQL_HOST'],
            port=os.environ['POSTGRESQL_PORT'],
            password=os.environ['POSTGRESQL_PASSWORD'],
            user='bot',
            database='senjibot',
            min_size=1,
            max_size=5
        )
        for filename in os.listdir('cogs'):
            if not filename.endswith('.py'): continue
            await self.load_extension('cogs.'+filename[0:-3])

        self.tree.copy_global_to(guild=self.test_guild)
        self.launch_time = utils.utcnow()

    async def on_command_error(self, ctx, error):
        if isinstance(error, (
            commands.CheckFailure,
            commands.CommandNotFound,
            commands.DisabledCommand
        )): return

        try:
            async with asyncio.timeout(5):
                await ctx.reply(f'{type(error).__name__}: {error}')
        except asyncio.TimeoutError:
            logger.warning('Timed out trying to notify user of error in "%s"', ctx.command.name)
        except discord.HTTPException:
            logger.warning('Failed trying to notify user of error in "%s"', ctx.command.name)
        await super().on_command_error(ctx, error)

    async def close(self):
        print('\nClosing...')
        await self.db.close()
        await super().close()


bot = SenjibotBETA(
    command_prefix='s?',
    owner_id=902371374033670224,
    test_guild=809722018953166858,
    help_command=None,
    description='...',
    allowed_mentions=discord.AllowedMentions.none(),
    intents=discord.Intents(
        guilds=True,
        members=True,
        messages=True,
        message_content=True
    ),
    tree_cls=NewTree,
    activity=discord.CustomActivity(name='epok'),
    status=discord.Status.idle
)

@bot.event
async def on_connect():
    print('Connected')

@bot.event
async def on_ready():
    print('Ready')

@bot.before_invoke
async def before_invoke(ctx):
    if ctx.command.name in ('sync', 'send'): return

    await ctx.typing()

@bot.command(aliases=('p',))
async def ping(ctx):
    await ctx.reply(f'Ping! {int(bot.latency*1000)}ms.')

@bot.command()
async def send(ctx, channel: Optional[discord.TextChannel], *, message):
    channel = channel or ctx.channel
    await channel.send(message)
    await ctx.message.add_reaction('\U00002705')

@bot.command(aliases=('up',))
async def uptime(ctx):
    await ctx.reply(f'Uptime: {utils.format_dt(bot.launch_time, style="R")}')

@bot.command(aliases=('s',))
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync(guild=bot.test_guild)
    await ctx.message.add_reaction('\U00002705')

@bot.command(name='load', aliases=('l',))
@commands.is_owner()
async def load_cog(ctx, cog):
    if 'cogs.'+cog in bot.extensions:
        await bot.reload_extension('cogs.'+cog)
        await ctx.reply(f'Cog "{cog}" reloaded.')
    else:
        await bot.load_extension('cogs.'+cog)
        await ctx.reply(f'Cog "{cog}" loaded.')

@bot.command(name='unload', aliases=('u',))
@commands.is_owner()
async def unload_cog(ctx, cog):
    if 'cogs.'+cog in bot.extensions:
        await bot.unload_extension('cogs.'+cog)
        await ctx.reply(f'Cog "{cog}" unloaded.')
    else:
        await ctx.reply(f'Cog "{cog}" not loaded.')

@bot.command(name='eval', aliases=('e',))
@commands.is_owner()
async def evaluate(ctx, *, code):
    try:
        if code.startswith('await '):
            await ctx.reply(await eval(code[5:]))
        else:
            await ctx.reply(eval(code))
    except Exception as error:
        await ctx.reply(f'{type(error).__name__}: {error}')

@bot.tree.command(name='ping')
async def slashping(inter):
    await inter.response.send_message(f'Ping! {int(bot.latency*1000)}ms.')

async def main():
    utils.setup_logging()
    async with bot:
        await bot.start(os.environ['SENJIBOT_BETA_TOKEN'])

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
