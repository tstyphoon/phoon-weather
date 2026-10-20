"""Discord 收發。只負責接訊息、加反應、送回覆；判讀與紀錄都在別的模組。"""
from __future__ import annotations

import logging
import re

import discord
from discord import app_commands

from core import strings
from core.context import Ctx
from core.pipeline import AnalysisFailed, Pipeline, Reply
from core.queue import Job, JobQueue
from core.registry import COMMANDS, TEXT_INTENTS, coerce_arg
from core.sanitize import neutralize_mentions
from services.weather import WeatherError

log = logging.getLogger(__name__)

MAX_IMAGES_PER_MESSAGE = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
NO_MENTIONS = discord.AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)


class WeatherBot(discord.Client):
    def __init__(self, config, store, weather, claude):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, allowed_mentions=NO_MENTIONS)
        self.config, self.store, self.weather, self.claude = config, store, weather, claude
        self.pipeline = Pipeline()
        self.jobs = JobQueue()
        self.tree = app_commands.CommandTree(self)
        self._announced = False
        self._register_commands()

    # ---------- 啟動 ----------
    async def setup_hook(self):
        self.loop.create_task(self.jobs.worker())

    async def on_ready(self):
        log.info("已登入為 %s", self.user)
        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        channel = self.get_channel(self.config.channel_id)
        if channel is None:
            log.error("找不到 CHANNEL_ID 指定的頻道，請確認 bot 已在該 Server 並看得到頻道")
        elif not self._announced:
            self._announced = True
            await channel.send(strings.ONLINE)

    # ---------- 訊息 ----------
    def _ctx(self, user) -> Ctx:
        return Ctx(self.config, self.store, self.weather, self.claude, str(user.id), user.display_name)

    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != self.config.channel_id:
            return
        images = [a for a in message.attachments if (a.content_type or "").split(";")[0] in IMAGE_TYPES]
        if images:
            await self._queue_images(message, images)
            return
        if message.attachments:  # 有附件，但都不是圖片
            await self._reply(message, strings.ONLY_IMAGES)
            return
        if self.user in message.mentions:
            text = re.sub(rf"<@!?{self.user.id}>", "", message.content).strip()
            await self._queue_text(message, text)

    async def _queue_images(self, message, images):
        user_id = str(message.author.id)
        if len(images) > MAX_IMAGES_PER_MESSAGE:
            await self._reply(message, strings.TOO_MANY_IMAGES.format(n=MAX_IMAGES_PER_MESSAGE))
            images = images[:MAX_IMAGES_PER_MESSAGE]
        for att in images:
            if att.size > MAX_IMAGE_BYTES:
                await self._reply(message, strings.IMAGE_TOO_BIG.format(mb=MAX_IMAGE_BYTES // 1048576))
                continue
            if not self.jobs.can_accept(user_id):
                await self._reply(message, strings.QUEUE_FULL.format(n=self.jobs.per_user_limit))
                break
            await self._submit(message, user_id, lambda a=att: self._do_image(message, a))

    async def _queue_text(self, message, text):
        user_id = str(message.author.id)
        if not self.jobs.can_accept(user_id):
            await self._reply(message, strings.QUEUE_FULL.format(n=self.jobs.per_user_limit))
            return
        await self._submit(message, user_id, lambda: self._do_text(message, text))

    async def _submit(self, message, user_id, run):
        await self._react(message, "⏳")
        job = Job(user_id=user_id, run=run)
        job.on_start = lambda: self._on_start(message, job)
        job.on_error = lambda e: self._on_error(message, e)
        ahead = self.jobs.submit(job)
        if ahead >= 2:
            job.ahead_note = await self._reply(message, strings.QUEUE_AHEAD.format(n=ahead))

    async def _on_start(self, message, job):
        await self._unreact(message, "⏳")
        await self._react(message, "🔄")
        if job.ahead_note:
            try:
                await job.ahead_note.delete()
            except discord.HTTPException:
                pass

    async def _on_error(self, message, error):
        await self._unreact(message, "🔄")
        await self._react(message, "❌")
        if isinstance(error, AnalysisFailed):
            await self._reply(message, strings.ANALYSIS_FAILED)
        elif isinstance(error, WeatherError):
            await self._reply(message, strings.WEATHER_DOWN)
        else:
            await self._reply(message, strings.UNKNOWN_ERROR)

    async def _do_image(self, message, att):
        media = att.content_type.split(";")[0]
        image = await att.read()
        reply = await self.pipeline.handle_image(
            self._ctx(message.author), image, media, IMAGE_TYPES[media], message.content)
        await self._send_reply(message, reply)
        await self._unreact(message, "🔄")
        await self._react(message, "✅")

    async def _do_text(self, message, text):
        ctx = self._ctx(message.author)
        intent = next((t for t in TEXT_INTENTS.values() if t.keywords and any(k in text for k in t.keywords)),
                      next((t for t in TEXT_INTENTS.values() if t.keywords is None), None))
        out = await intent.func(ctx, text) if intent else strings.UNKNOWN_ERROR
        await self._reply(message, out)
        await self._unreact(message, "🔄")
        await self._react(message, "✅")

    # ---------- 送出 ----------
    async def _send_reply(self, message, reply: Reply):
        if reply.card:
            c = reply.card
            embed = discord.Embed(title=neutralize_mentions(c.title)[:256], color=c.color)
            for name, value in c.fields:
                embed.add_field(name=name[:256], value=(value or "-")[:1024], inline=False)
            embed.set_footer(text=c.footer[:2048])
            await message.reply(c.summary[:2000], embed=embed, mention_author=True,
                                allowed_mentions=NO_MENTIONS)
        else:
            await self._reply(message, reply.text or "")

    async def _reply(self, message, text: str):
        try:
            return await message.reply(text[:2000], mention_author=True, allowed_mentions=NO_MENTIONS)
        except discord.HTTPException:
            log.exception("回覆失敗")

    async def _react(self, message, emoji):
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    async def _unreact(self, message, emoji):
        try:
            await message.remove_reaction(emoji, self.user)
        except discord.HTTPException:
            pass

    # ---------- / 指令 ----------
    def _register_commands(self):
        for cmd in COMMANDS.values():
            self.tree.add_command(self._make_command(cmd))

    def _make_command(self, cmd):
        async def callback(interaction: discord.Interaction, arg: str = ""):
            if interaction.channel_id != self.config.channel_id:
                await interaction.response.send_message(strings.CHANNEL_ONLY, ephemeral=True)
                return
            await interaction.response.defer(ephemeral=cmd.ephemeral)
            ok, value = coerce_arg(cmd.func, arg)
            if not ok:
                await interaction.followup.send(strings.USAGE.format(usage=cmd.usage))
                return
            try:
                ctx = self._ctx(interaction.user)
                result = await cmd.func(ctx, value) if value is not None else await cmd.func(ctx)
            except Exception:
                log.exception("指令 %s 失敗", cmd.name)
                result = strings.UNKNOWN_ERROR
            await interaction.followup.send(str(result)[:2000], allowed_mentions=NO_MENTIONS)

        return app_commands.Command(name=cmd.name, description=(cmd.description or cmd.name)[:100],
                                    callback=callback)
