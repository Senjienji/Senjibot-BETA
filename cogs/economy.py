import discord
from discord import app_commands, ui, utils
from discord.ext import commands
import asyncpg
from typing import Optional
from random import random
from inspect import cleandoc
from logging import getLogger
import json
import asyncio

logger = getLogger(__name__)


class CustomView(ui.View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.message: discord.Message | None = None

    async def interaction_check(self, inter) -> bool:
        await self.db.execute(
            """INSERT INTO economy.member_data (guild_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id, user_id) DO NOTHING;""",
            inter.guild.id, inter.user.id
        )
        return True

    async def on_timeout(self):
        for i in self.walk_children():
            i.disabled = True
        await self.message.edit(view=self)

    async def on_error(self, inter, error, item):
        try:
            async with asyncio.timeout(5):
                if inter.response.is_done():
                    await inter.followup.send(f'{type(error).__name__}: {error}')
                else:
                    await inter.response.send_message(f'{type(error).__name__}: {error}', ephemeral=True)
        except asyncio.TimeoutError:
            logger.warning('Timed out trying to notify user of error')
        except discord.HTTPException:
            logger.warning('Failed trying to notify user of error')

        if isinstance(error, AssertionError): return
        await super().on_error(inter, error, item)


class AddItemModal(ui.Modal, title='Add Shop Item'):
    item_name = ui.TextInput(label='Item Name')
    item_cost = ui.TextInput(label='Item Cost', placeholder='A whole number', default='0')
    item_desc = ui.TextInput(label='Item Description', style=discord.TextStyle.paragraph, required=False, default='An item')

    def __init__(self, db: asyncpg.Pool, **kwargs):
        self.db = db
        super().__init__(**kwargs)

    async def on_error(self, inter, error):
        try:
            async with asyncio.timeout(5):
                if inter.response.is_done():
                    await inter.followup.send(f'{type(error).__name__}: {error}')
                else:
                    await inter.response.send_message(f'{type(error).__name__}: {error}', ephemeral=True)
        except asyncio.TimeoutError:
            logger.warning('Timed out trying to notify user of error')
        except discord.HTTPException:
            logger.warning('Failed trying to notify user of error')

        if isinstance(error, AssertionError): return
        await super().on_error(inter, error)

    async def on_submit(self, inter):
        name = self.item_name.value
        cost = self.item_cost.value
        desc = self.item_desc.value
        assert cost.isnumeric(), 'Please insert a valid cost value.'

        try:
            await self.db.execute(
                """INSERT INTO economy.guild_shops
                (guild_id, item_name, item_desc, item_cost)
                VALUES ($1, $2, $4, $3);""",
                inter.guild.id, name, int(cost), desc
            )
            await inter.response.send_message(f'Item "{name}" added.')
        except asyncpg.exceptions.UniqueViolationError:
            await inter.response.send_message(f'Item named "{name}" already exists. Please try another name.')


class EditItemModal(ui.Modal, title='Edit Shop Modal'):
    # TO DO:
    #  - edit cost & desc
    #  - offer new name change
    #  - take action parameters

    item_name = ui.TextInput(label='Item Name')
    item_cost = ui.TextInput(label='Item Cost', placeholder='A whole number', default='0')
    item_desc = ui.TextInput(label='Item Description', style=discord.TextStyle.paragraph, required=False, default='An item')

    def __init__(self, db: asyncpg.Pool, **kwargs):
        self.db = db
        super().__init__(**kwargs)

    async def on_error(self, inter, error):
        try:
            async with asyncio.timeout(5):
                if inter.response.is_done():
                    await inter.followup.send(f'{type(error).__name__}: {error}')
                else:
                    await inter.response.send_message(f'{type(error).__name__}: {error}', ephemeral=True)
        except asyncio.TimeoutError:
            logger.warning('Timed out trying to notify user of error')
        except discord.HTTPException:
            logger.warning('Failed trying to notify user of error')

        if isinstance(error, AssertionError): return
        await super().on_error(inter, error)

    async def on_submit(self, inter):
        name = self.item_name.value
        cost = self.item_cost.value
        desc = self.item_desc.value
        assert cost.isnumeric(), 'Please insert a valid cost value.'

        try:
            await self.db.execute(
                """INSERT INTO economy.guild_shops
                (guild_id, item_name, item_desc, item_cost)
                VALUES ($1, $2, $4, $3);""",
                inter.guild.id, name, int(cost), desc
            )
            await inter.response.send_message(f'Item "{name}" added.')
        except asyncpg.exceptions.UniqueViolationError:
            await inter.response.send_message(f'Item named "{name}" already exists. Please try another name.')


class ShopDropdown(ui.Select):
    def __init__(self, db, items, **kwargs):
        self.db = db
        options = [
            discord.SelectOption(label=f'{name} - ${cost}', description=desc, value=str(id))
            for id, name, cost, desc in items
        ]
        super().__init__(placeholder='Select an item to purchase',  options=options, **kwargs)

    async def callback(self, inter):
        async with self.db.acquire() as conn:
            async with conn.transaction():
                item_id = int(self.values[0])
                row = await conn.fetchrow(
                    """SELECT m.wallet, s.item_name, s.item_cost, s.actions
                    FROM economy.member_data m
                    JOIN economy.guild_shops s ON m.guild_id = s.guild_id
                    WHERE m.guild_id = $1 AND m.user_id = $2 AND s.item_id = $3""",
                    inter.guild.id, inter.user.id, item_id
                )
                if not row:
                    await inter.response.send_message('This item has been removed. Sorry.', ephemeral=True)
                    return

                wallet, name, cost, actions = row
                cost = int(cost)
                actions = json.loads(actions)
                if wallet < int(cost):
                    await inter.response.send_message("You don't have enough money.", ephemeral=True)
                    return

                await conn.execute(
                    """UPDATE economy.member_data
                    SET wallet = wallet - $3
                    WHERE guild_id = $1 AND user_id = $2;""",
                    inter.guild.id, inter.user.id, cost
                )
                """{
                    "add_roles": ...,
                    "remove_roles": ...,
                    "response": ...,
                    "add_money": ...
                    ...
                }"""

                if 'response' not in actions:
                    actions['response'] = '"{name}" bought.'
                    await conn.execute(
                        """UPDATE economy.guild_shops
                        SET actions = $2
                        WHERE item_id = $1;""",
                        id, json.dumps(actions)
                    )
                for key, value in actions.items():
                    if key == 'add_roles':
                        roles = map(lambda i: discord.Object(i), value)
                        await inter.user.add_roles(*roles)
                    elif key == 'remove_roles':
                        roles = map(lambda i: discord.Object(i), value)
                        await inter.user.remove_roles(*roles)
                    elif key == 'response':
                        await inter.response.send_message(value.format(name=name))
                    elif key == 'add_money':
                        await conn.execute(
                            """UPDATE economy.member_data
                            SET wallet = wallet + $3
                            WHERE guild_id = $1 AND user_id = $2;""",
                            inter.guild.id, inter.user.id, value
                        )
                 #  elif key == '...': ...


@app_commands.guild_only()
class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db

    async def cog_load(self):
        print(f'Cog "{self.__class__.__name__}" loaded.')

    async def cog_unload(self):
        print(f'Cog "{self.__class__.__name__}" unloaded.')

    # before_invoke
    async def interaction_check(self, inter) -> bool:
        await self.db.execute(
            """INSERT INTO economy.member_data (guild_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id, user_id) DO NOTHING;""",
            inter.guild.id, inter.user.id
        )
        return True

    # after_invoke
    @commands.Cog.listener()
    async def on_app_command_completion(self, inter, command):
        if not isinstance(command, app_commands.Command) or not inter.guild: return
        if True: return  # temp

        is_in_cog = False
        for i in self.walk_app_commands():
            if i == command:
                is_in_cog = True
                break
        if not is_in_cog: return

        pass

    @commands.command(name='set-money', aliases=('set',))
    @commands.is_owner()
    async def set_money(self, ctx, member: Optional[discord.Member], amount: float=0.0):
        member = member or ctx.author
        await self.db.execute(
            """INSERT INTO economy.member_data (guild_id, user_id, wallet)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id) DO UPDATE
            SET wallet = $3;""",
            ctx.guild.id, member.id, amount
        )
        await ctx.reply(f'Set ${amount:.2f} to {member.mention}.')

    @app_commands.command(description='...')
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
                await inter.response.send_message(cleandoc(
                    f"""{member.mention} Balance

                    Wallet: ${row['wallet']:.2f}
                    Bank: ${row['bank']:.2f}"""
                ))

    @app_commands.command(description='...')
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

    @app_commands.command(description='...')
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

    @app_commands.command(description='...')
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
            ) or 'Nothing as of now...'
        )

    @app_commands.command(description='Daily work')
    async def work(self, inter):
        amount = 1 + random() * 2  # 1...3
        async with self.db.acquire() as conn:
            async with conn.transaction():
                status = await conn.execute(
                    """UPDATE economy.member_data
                    SET wallet = wallet + $3, last_daily = NOW()
                    WHERE guild_id = $1 AND user_id = $2
                    AND NOW() > last_daily + INTERVAL '1 day';""",
                    inter.guild.id, inter.user.id, amount
                )
                if int(status[-1]):
                    await inter.response.send_message(f'You worked and got paid ${amount:.2f}.')
                else:
                    row = await conn.fetchrow(
                        """SELECT last_daily + INTERVAL '1 day'
                        FROM economy.member_data
                        WHERE guild_id = $1 AND user_id = $2;""",
                        inter.guild.id, inter.user.id
                    )
                    await inter.response.send_message(f'Work on cooldown... wait {utils.format_dt(row[0], "R")}.')


    shop = app_commands.Group(
        name='shop',
        description='View the shop for this server'
    )

    @shop.command(name='add', description='...')
    async def shopadd(self, inter):
        await inter.response.send_modal(AddItemModal(self.db))

    @shop.command(name='list', description='...')
    async def shoplist(self, inter):
        rows = await self.db.fetch(
            """SELECT item_id, item_name, item_cost, item_desc
            FROM economy.guild_shops
            WHERE guild_id = $1;""",
            inter.guild.id
        )
        if not rows:
            await inter.response.send_message('As of now, no items are for sale.')
            return

        view = CustomView()
        view.add_item(ShopDropdown(self.db, rows))
        await inter.response.send_message('View all the items below:', view=view)
        view.message = await inter.original_response()

    @shop.command(name='remove', description='...')
    async def shopremove(self, inter, item: str):
        item = item.split('|', 1)
        assert len(item) > 1 and item[0].isnumeric(), 'Please select one of the options.'
        id, name = item

        await self.db.execute(
            """DELETE FROM economy.guild_shops
            WHERE item_id = $1;""",
            int(id)
        )
        await inter.response.send_message(f'Item "{name}" removed.')

    @shopremove.autocomplete('item')
    async def shopremove_item_ac(self, inter, current):
        items = await self.db.fetch(
            """SELECT item_id, item_name
            FROM economy.guild_shops
            WHERE guild_id = $1;""",
            inter.guild.id
        )
        return [
            app_commands.Choice(name=name, value=f'{id}|{name}')
            for id, name in items if current.lower() in name.lower()
        ]

    @app_commands.command(name='edit', description='...')
    async def shopedit(self, inter, item: str):
        await inter.response.send_modal(EditItemModal(self.db, int(item)))

    @shopedit.autocomplete('item')
    async def shopedit_item_ac(self, inter, current):
        items = await self.db.fetch(
            """SELECT item_id, item_name
            FROM economy.guild_shops
            WHERE guild_id = $1;""",
            inter.guild.id
        )
        return [
            app_commands.Choice(name=name, value=str(id))
            for id, name in items if current.lower() in name.lower()
        ]

async def setup(bot):
    await bot.add_cog(Economy(bot))
