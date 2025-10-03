import discord
from discord import app_commands
from discord.ext import commands
from discord import utils
import asyncpg
import typing
import random


@app_commands.guild_only()
class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db

    async def cog_load(self):
        print(f'Cog "{self.__class__.__name__}" loaded.')

    async def cog_unload(self):
        print(f'Cog "{self.__class__.__name__}" unloaded.')

    async def interaction_check(self, inter) -> bool:
        await self.db.execute(
            """INSERT INTO economy.member_data (guild_id, user_id)
VALUES ($1, $2)
ON CONFLICT (guild_id, user_id) DO NOTHING;""",
            inter.guild.id, inter.user.id
        )
        return True

    @commands.command(name='set-money', aliases=('set',))
    @commands.is_owner()
    async def set_money(self, ctx, member: typing.Optional[discord.Member]=None, amount: float=0.0):
        member = member or ctx.author
        await self.db.execute(
            """INSERT INTO economy.member_data (guild_id, user_id, wallet)
VALUES ($1, $2, $3)
ON CONFLICT (guild_id, user_id) DO UPDATE
SET wallet = $3;""",
            ctx.guild.id, member.id, amount
        )
        await ctx.reply(f'Set ${amount:.2f} to {member.mention}.')

    @app_commands.command()
    async def balance(self, inter, member: discord.Member=None):
        member = member or inter.user
        async with self.db.acquire() as conn:
            async with conn.transaction():
                if member != inter.user:
                    await conn.execute(
                        """INSERT INTO economy.member_data (guild_id, user_id)
VALUES ($1, $2)
ON CONFLICT (guild_id, user_id) DO NOTHING;""",
                        inter.guild.id, member.id
                        )
                row = await conn.fetchrow(
                    """SELECT wallet, bank
FROM economy.member_data
WHERE guild_id = $1 AND user_id = $2;""",
                    inter.guild.id, member.id
                )
                await inter.response.send_message(f"""{member.mention} Balance

Wallet: ${row["wallet"]:.2f}
Bank: ${row["bank"]:.2f}""")

    @app_commands.command()
    async def deposit(self, inter, amount: float=-1.0):
        async with self.db.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """SELECT wallet
FROM economy.member_data
WHERE guild_id = $1 AND user_id = $2;""",
                    inter.guild.id, inter.user.id
                )
                if amount < 0:
                    amount = row['wallet']
                elif amount > row['wallet']:
                    await inter.response.send_message('"Amount" must not be greater than your wallet.', ephemeral=True)
                    return

                await conn.execute(
                    """UPDATE economy.member_data
SET wallet = wallet - $3, bank = bank + $3
WHERE guild_id = $1 AND user_id = $2;""",
                    inter.guild_id, inter.user.id, amount
                )
                await inter.response.send_message(f'${amount:.2f} deposited.')

    @app_commands.command()
    async def withdraw(self, inter, amount: float=-1.0):
        async with self.db.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """SELECT bank
FROM economy.member_data
WHERE guild_id = $1 AND user_id = $2;;""",
                    inter.guild.id, inter.user.id
                )
                if amount < 0:
                    amount = row['bank']
                elif amount > row['bank']:
                    await inter.response.send_message('"Amount" must not be greater than your bank.', ephemeral=True)
                    return

                await conn.execute(
                    """UPDATE economy.member_data
SET wallet = wallet + $3, bank = bank - $3
WHERE guild_id = $1 AND user_id = $2;""",
                    inter.guild_id, inter.user.id, amount
                )
                await inter.response.send_message(f'${amount:.2f} withdrawn.')

    @app_commands.command()
    async def leaderboard(self, inter):
        rows = await self.db.fetch(
            """SELECT user_id, wallet + bank AS total
FROM economy.member_data
WHERE guild_id = $1;""",
            inter.guild.id
        )
        await inter.response.send_message(
            '\n'.join(
                f'`{self.bot.get_user(id)}`: ${total:.2f}'
                for id, total in sorted(
                    filter(
                        lambda i: i[1] > 0,
                        map(
                            lambda i: tuple(i.values()),
                            rows
                        ),
                    ),
                    key=lambda i: i[1],
                    reverse=True
                )
            )
        )

    @app_commands.command(description='Daily work')
    async def work(self, inter):
        amount = 1 + random.random() * 2  #1...3
        status = await self.db.execute(
            """UPDATE economy.member_data
SET wallet = wallet + $3, last_daily = NOW()
WHERE guild_id = $1 AND user_id = $2
AND NOW() > last_daily + INTERVAL '1 day';""",
            inter.guild.id, inter.user.id, amount
        )
        if int(status.split()[1]):
            await inter.response.send_message(f'You worked and got paid ${amount:.2f}.')
        else:
            row = await self.db.fetchrow(
                """SELECT last_daily + INTERVAL '1 day' AS date
FROM economy.member_data
WHERE guild_id = $1 AND user_id = $2;""",
                inter.guild.id, inter.user.id
            )
            await inter.response.send_message(f'Work on cooldown... Wait {utils.format_dt(row["date"], "R")}.')

async def setup(bot):
    await bot.add_cog(Economy(bot))
