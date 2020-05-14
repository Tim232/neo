import re
from contextlib import suppress
import asyncio

from discord.ext import commands
import discord

import utils.paginator as pages


class Context(commands.Context):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def prompt(self, message):
        emojis = {
            '<:c_:710356775701970987>': True,
            '<:x_:710356782957985823>': False}
        msg = await self.send(message)
        for e in emojis.keys():
            await msg.add_reaction(e)
        payload = await self.bot.wait_for(
            'raw_reaction_add',
            check=lambda p: str(p.emoji) in emojis.keys()
            and p.user_id == self.author.id and p.message_id == msg.id)
        if emojis[str(payload.emoji)] is True:
            await msg.edit(content='Confirmed!')
            return True
        else:
            await msg.edit(content='Cancelled!')
            return False

    async def safe_send(self, content=None, **kwargs):
        if content:
            if match := re.search(re.compile(r'([a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}|mfa\.[a-zA-Z0-9_\-]{84})'), content):
                content = content.replace(match.group(0), '[token omitted]')
            if len(content) > 2000:
                async with self.bot.session.post(
                        "https://mystb.in/documents",
                        data=content.encode('utf-8')) as post:
                    post = await post.json()
                    url = f"https://mystb.in/{post['key']}"
                    await self.send(
                        f'Output: <{url}>'
                    )
            else:
                return await self.send(content, **kwargs)
        else:
            await self.send(**kwargs)

    def tick(self, opt, label=None):
        lookup = {
            True: '<:c_:710356775701970987>',
            False: '<:x_:710356782957985823>',
            None: '<:unicode_neutral:710356848447979671>',
        }
        emoji = lookup.get(opt, '<:x_:710356782957985823>')
        if label is not None:
            return f'{emoji}: {label}'
        return emoji

    @staticmethod
    def codeblock(content, hl_lang=None):
        return f'```{hl_lang or ""}\n' + content + '\n```'

    def tab(self, repeat=1):
        tabs = []
        for i in range(repeat):
            tabs.append(' \u200b')
        return ''.join(tabs)

    async def quick_menu(self, entries, per_page, *, template: discord.Embed = None, **kwargs):
        source = pages.BareBonesMenu(entries, per_page=per_page, embed=template)
        menu = pages.CSMenu(source, **kwargs)
        await menu.start(self)

    @staticmethod
    async def propagate_to_eh(bot, ctx, error):
        with suppress(Exception):
            await ctx.message.add_reaction('<:bwarn:710356862142513172>')
            try:
                reaction, user = await bot.wait_for(
                    'reaction_add',
                    check=lambda r, u: r.message.id == ctx.message.id
                    and u.id in [ctx.author.id, 680835476034551925], timeout=30.0
                )
            except asyncio.TimeoutError:
                await ctx.message.remove_reaction('<:bwarn:710356862142513172>', ctx.me)
                return
            if str(reaction.emoji) == '<:bwarn:710356862142513172>':
                return await ctx.send(error)

    class ExHandler:
        """
        Handles exceptions and returns True if there is no error
        or False if there is an error. A specific error type can be passed,
        defaults to Exception

        Usage:
            async with ctx.ExHandler(commands.MissingPermissions) as out:
                await bot.get_command('lock').can_run(ctx)
            if out.res:
                # do a thing
            else:
                # do the failure thing

        This manager can also be used to propagate directly to the bot's
        error handler. This is accomplished by passing a tuple of values
        to the constructor.

        Usage:
            async with ctx.ExHandler(propagate=(bot, ctx)) as out:
                await bot.get_command('lock').can_run(ctx)
        """

        def __init__(
                self, *, exception_type=None,
                propagate=(None, None), message: str = None):
            self.res = False
            self.ex_type = exception_type
            self.should_prop = False
            self.message = message
            if propagate and propagate[0] is not None and propagate[1] \
                    is not None:
                self.bot, self.ctx = propagate
                self.should_prop = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, type, val, tb):
            if isinstance(val, self.ex_type or Exception):
                self.res = False
                if self.should_prop is True:
                    await Context.propagate_to_eh(
                        self.bot, self.ctx, self.message
                        or (val if str(type) != '' else type))
            else:
                self.res = True
            return True
