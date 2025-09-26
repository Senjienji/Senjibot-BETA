import discord
from discord import app_commands
from discord.ext import commands
import asyncpg


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        print(f'Cog "{self.__class__.__name__}" loaded.')

    async def cog_unload(self):
        print(f'Cog "{self.__class__.__name__}" unloaded.')

    async def interaction_check(self, inter) -> bool:
        return True

    @commands.command(name='add-money', aliases=('add',))
    @commands.is_owner()
    async def add_money(self, ctx, amount: float, member: discord.Member=None):
        member = member or ctx.author
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                '''INSERT INTO economy.member_data (guild_id, user_id, wallet)
VALUES ($1, $2, $3)
ON CONFLICT (guild_id, user_id) DO UPDATE
SET wallet = COALESCE(NULLIF(economy.member_data.wallet, 'NaN'), 0) + $3;''',
                ctx.guild.id, member.id, amount
            )
            await ctx.reply(f'Added ${amount:.2f} to {member.mention}.')

    @app_commands.command()
    async def balance(self, inter, member: discord.Member=None):
        member = member or inter.user
        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    '''INSERT INTO economy.member_data (guild_id, user_id)
VALUES ($1, $2)
ON CONFLICT (guild_id, user_id) DO UPDATE
SET guild_id = EXCLUDED.guild_id
RETURNING wallet, bank''',
                    inter.guild.id, member.id
                )
                await inter.response.send_message(f'''{member.mention} Balance

Wallet: ${row["wallet"]:.2f}
Bank: ${row["bank"]:.2f}''')

    @app_commands.command()
    async def deposit(self, inter, amount: float):
        if amount < 0:
            await inter.response.send_message('"Amount" must not be negative', ephemeral=True)
            return

        async with self.bot.db.acquire() as conn:
            status = await conn.execute(
                '''UPDATE economy.member_data
SET wallet = wallet - $3, bank = bank + $3
WHERE guild_id = $1 AND user_id = $2 AND $3 <= wallet;''',
                inter.guild_id, inter.user.id, amount
            )
            if int(status.split()[1]):
                await inter.response.send_message(f'${amount:.2f} deposited.')
            else:
                await inter.response.send_message('"Amount" must not be greater than your wallet.', ephemeral=True)

    @app_commands.command()
    async def withdraw(self, inter, amount: float):
        if amount < 0:
            await inter.response.send_message('"Amount" must not be negative', ephemeral=True)
            return

        async with self.bot.db.acquire() as conn:
            status = await conn.execute(
                '''UPDATE economy.member_data
SET wallet = wallet + $3, bank = bank - $3
WHERE guild_id = $1 AND user_id = $2 AND $3 <= bank;''',
                inter.guild_id, inter.user.id, amount
            )
            if int(status.split()[1]):
                await inter.response.send_message(f'${amount:.2f} withdrawn.')
            else:
                await inter.response.send_message('"Amount" must not be greater than your bank.', ephemeral=True)

    @app_commands.command()
    async def leaderboard(self, inter):
        await inter.response.send_message('yes')

async def setup(bot):
    await bot.add_cog(Economy(bot))
