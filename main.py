# -*- coding: utf-8 -*-
import os
import logging
import random
import itertools
import aiohttp
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

logging.basicConfig(level=logging.INFO)

# ---- Intents ----
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---- サーバーID ----
GUILD_IDS = [1357655899212349490]

# ---- カラー設定 ----
main_color = discord.Color.from_rgb(255, 140, 0)  # オレンジ

# ---- GAS Webhook ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"

# ---- チーム分けアルゴリズム（奇数対応）----
def split_balanced_teams(players):
    n = len(players)
    best_diff = 999
    best_pair = ([], [])

    for r in range(n // 2, (n // 2) + 2):
        for combo in itertools.combinations(players, r):
            other = [p for p in players if p not in combo]
            sumA = sum(p['point'] for p in combo)
            sumB = sum(p['point'] for p in other)
            diff = abs(sumA - sumB)
            if diff < best_diff:
                best_diff = diff
                best_pair = (combo, other)
            if diff <= 1:
                return combo, other, diff
    return best_pair[0], best_pair[1], best_diff


# ---- /peko グループ ----
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)


@peko.command(name="team", description="VC内メンバーをチーム分け")
async def team(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.respond("⚠️ ボイスチャンネルに参加してから実行してください。")
        return

    members = [m for m in ctx.author.voice.channel.members if not m.bot]
    if len(members) < 2:
        await ctx.respond("⚠️ 2人以上で実行してください。")
        return

    user_ids = [str(m.id) for m in members]
    payload = {"action": "fetch_team_data", "user_ids": user_ids}

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as resp:
            if resp.status != 200:
                await ctx.respond(f"⚠️ スプレッドシート接続エラー ({resp.status})")
                return
            data = await resp.json()

    if not data:
        await ctx.respond("⚠️ スプレッドシートに登録されたランク情報が見つかりません。")
        return

    registered = [d for d in data if d["point"] > 0]
    unregistered = [m.display_name for m in members if str(m.id) not in [d["user_id"] for d in registered]]

    if unregistered:
        msg = "⚠️ 以下のメンバーは未登録です：\n" + "\n".join(unregistered)
        await ctx.respond(msg)
        return

    teamA, teamB, diff = split_balanced_teams(registered)

    embed = discord.Embed(title="チーム分け結果", color=main_color)
    embed.add_field(
        name="🟥 アタッカー",
        value="\n".join([f"{p['name']}（{p['rank']}）" for p in teamA]) + f"\n戦力：{sum(p['point'] for p in teamA)}",
        inline=True
    )
    embed.add_field(
        name="🟦 ディフェンダー",
        value="\n".join([f"{p['name']}（{p['rank']}）" for p in teamB]) + f"\n戦力：{sum(p['point'] for p in teamB)}",
        inline=True
    )
    embed.add_field(name="　", value=f"チーム差：{diff}", inline=False)

    await ctx.respond(embed=embed)


bot.add_application_command(peko)


# ---- 起動 ----
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/peko team"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です（Railway の Variables に設定してください）。")
    bot.run(token)
