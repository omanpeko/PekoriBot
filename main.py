# -*- coding: utf-8 -*-
import os
import logging
import random
import itertools
import discord
from discord.ext import commands
from discord.commands import slash_command

logging.basicConfig(level=logging.INFO)

# ---- Intents ----
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

# ---- Bot ----
bot = commands.Bot(command_prefix="!", intents=intents)

# 即時反映サーバー
GUILD_IDS = [1357655899212349490]

# ---- ランクポイントテーブル ----
RANK_POINTS = {
    "アイアン1": 1, "アイアン2": 2, "アイアン3": 3,
    "ブロンズ1": 4, "ブロンズ2": 5, "ブロンズ3": 6,
    "シルバー1": 7, "シルバー2": 8, "シルバー3": 9,
    "ゴールド1": 10, "ゴールド2": 11, "ゴールド3": 12,
    "プラチナ1": 13, "プラチナ2": 14, "プラチナ3": 15,
    "ダイヤ1": 16, "ダイヤ2": 17, "ダイヤ3": 18,
    "アセンダント1": 19, "アセンダント2": 20, "アセンダント3": 21,
    "イモータル1": 22, "イモータル2": 23, "イモータル3": 24,
    "レディアント": 25
}

# ---- Utility: チーム分けアルゴリズム ----
def generate_balanced_teams(players):
    """
    players: [(name, point), ...] 10人分
    """
    valid_combinations = []
    all_combos = list(itertools.combinations(range(10), 5))  # 10C5 = 252
    seen = set()

    for combo in all_combos:
        complement = tuple(sorted(set(range(10)) - set(combo)))
        key = tuple(sorted(combo))
        if key in seen or complement in seen:
            continue
        seen.add(key)

        teamA = [players[i] for i in combo]
        teamB = [players[i] for i in range(10) if i not in combo]
        sumA = sum(p[1] for p in teamA)
        sumB = sum(p[1] for p in teamB)
        diff = abs(sumA - sumB)
        if diff <= 1:
            valid_combinations.append((teamA, teamB, diff))

    if not valid_combinations:
        return None, None, None, 0, 0

    total = len(valid_combinations)
    selected_index = random.randint(0, total - 1)
    teamA, teamB, diff = valid_combinations[selected_index]
    return teamA, teamB, diff, selected_index + 1, total


# ---- /peko teamtest ----
@slash_command(
    name="peko",
    description="PekoriBotコマンド集",
    guild_ids=GUILD_IDS
)
async def peko(ctx):
    pass  # ダミー（コマンドグループとして使う）


@peko.subcommand(
    name="teamtest",
    description="ランダム10人でチーム分けをテスト",
    guild_ids=GUILD_IDS
)
async def teamtest(ctx):
    """テストモード：ランダム10人生成してチーム分け"""
    await ctx.defer()

    # ランダム10人とランクポイント生成
    ranks = list(RANK_POINTS.keys())
    players = []
    for i in range(10):
        name = chr(65 + i)  # A〜J
        rank = random.choice(ranks)
        point = RANK_POINTS[rank]
        players.append((name, point))

    teamA, teamB, diff, idx, total = generate_balanced_teams(players)

    if not teamA:
        await ctx.respond("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    # Embed出力
    embed = discord.Embed(title="チーム分け結果", color=discord.Color.from_rgb(255, 140, 0))

    attacker_names = "\n".join([p[0] for p in teamA])
    defender_names = "\n".join([p[0] for p in teamB])

    embed.add_field(name="アタッカー", value=attacker_names, inline=True)
    embed.add_field(name="ディフェンダー", value=defender_names, inline=True)
    embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)

    await ctx.respond(embed=embed)


# ---- 起動 ----
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/peko teamtest"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です（Railway の Variables に設定してください）。")
    bot.run(token)
