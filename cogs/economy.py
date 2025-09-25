import discord
from discord import app_commands
from discord.ext import commands
import asyncpg


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self):
        print(f'Cog "{self.__class__.__name__}" loaded.')

    async def cog_unload(self):
        print(f'Cog "{self.__class__.__name__}" unloaded.')

    async def interaction_check(self, inter):
        #async with self.bot.db.acquire() as conn:
            #await conn.execute()
        return True

    @app_commands.command()
    async def balance(self, inter, member: discord.Member=None):
        member = member or inter.user
        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow('SELECT wallet, bank FROM economy.member_data WHERE guild_id = $1 AND member_id = $2;', inter.guild.id, member.id)
                if row:
                    wallet, bank = (row['wallet'], row['bank'])
                else:
                    await conn.execute('INSERT INTO economy.member_data (guild_id, member_id) VALUES ($1, $2);', inter.guild.id, member.id)
                    wallet, bank = (0.0, 0.0)
        await inter.response.send_message(f'{wallet:.2f}, {bank:.2f}')

    @app_commands.command()
    async def deposit(self, inter, amount: int):
        await inter.response.send_message('lorem ipsum')

    @app_commands.command()
    async def withdraw(self, inter, amount: int):
        await inter.response.send_message('placeholder')

    @app_commands.command()
    async def leaderboard(self, inter):
        await inter.response.send_message('yes')

async def setup(bot):
    await bot.add_cog(Economy(bot))
