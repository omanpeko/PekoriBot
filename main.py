# -*- coding: utf-8 -*-
import os
import logging
import random
import discord
from discord.ext import commands
from discord.commands import Option  # py-cord のスラッシュコマンド用

logging.basicConfig(level=logging.INFO)

# ---- Intents ----
intents = discord.Intents.default()
intents.message_content = True  # テキストコマンドも使いたい場合ON

# ---- Bot ----
bot = commands.Bot(command_prefix="!", intents=intents)

# 即時反映したいサーバー（ギルド）IDがあれば入れる（複数OK）
# 例: [932269784228306995, 1131436758970671104]
GUILD_IDS = []

@bot.event
async def on_ready():
    # ギルド限定コマンドは即時登録
    if GUILD_IDS:
        try:
            await bot.sync_commands(guild_ids=GUILD_IDS)
        except Exception as e:
            logging.warning(f"sync_commands failed: {e}")

    await bot.change_presence(activity=discord.Game(name="/hello"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")

# --- prefixコマンド（おまけ） ---
@bot.command()
async def ping(ctx):
    await ctx.send("pong!")

# --- slashコマンド（最小） ---
@bot.slash_command(
    name="hello",
    description="PekoriBotが挨拶します",
    guild_ids=GUILD_IDS if GUILD_IDS else None,  # 指定があれば即時反映
)
async def hello(
    ctx,
    name: Option(
        str, "あなたの名前（任意）", required=False,
        name_localizations={"ja": "あなたの名前"},
        description_localizations={"ja": "（任意）"},
    ),
):
    who = name.strip() if name else "みんな"
    await ctx.respond(f"こんにちは、{who}！PekoriBotです 👋")

# ---- エントリーポイント ----
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です（Railway の Variables に設定してください）。")
    bot.run(token)
