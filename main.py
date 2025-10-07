# -*- coding: utf-8 -*-
import os
import logging
import random
import itertools
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
import aiohttp  # GASとの通信

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

# ---- Google Apps ScriptのURL ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyjOtoYq8zeOfA-ph9GzdUWJmGONWF0N9UNk6RffHbi6XDki58LEmFzfIZpMWkV6X1hrQ/exec"

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

# ---- キャラ名リスト ----
CHAR_NAMES = [
    "リオナ", "カレン", "ユウキ", "トウマ", "サララ",
    "アキトラ", "ミナト", "レイナ", "タカオ", "シズク",
    "ハルフォ", "アマリス", "カグラミ", "リベルタ", "ノアール",
    "セレスティ", "ユリウスナ", "ルミナリア", "カナデアス", "アーディン",
    "シグルディア", "ラファエリア", "フィオレンテ", "グランディア", "アルフォリア",
    "ミツキオリオン", "アスタルテリア", "フェルナリアン", "クロノディアス", "ヴァレリアーナ"
]

# ---- チーム分けアルゴリズム ----
def generate_balanced_teams(players):
    valid_combinations = []
    all_combos = list(itertools.combinations(range(10), 5))
    seen = set()

    for combo in all_combos:
        complement = tuple(sorted(set(range(10)) - set(combo)))
        key = tuple(sorted(combo))
        if key in seen or complement in seen:
            continue
        seen.add(key)

        teamA = [players[i] for i in combo]
        teamB = [players[i] for i in range(10) if i not in combo]
        sumA = sum(p[2] for p in teamA)
        sumB = sum(p[2] for p in teamB)
        diff = abs(sumA - sumB)
        if diff <= 1:
            valid_combinations.append((teamA, teamB, diff))

    if not valid_combinations:
        return None, None, None, 0, 0

    total = len(valid_combinations)
    selected_index = random.randint(0, total - 1)
    teamA, teamB, diff = valid_combinations[selected_index]
    return teamA, teamB, diff, selected_index + 1, total


# ---- /peko コマンドグループ ----
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)


# 🎮 チーム分け
@peko.command(name="teamtest", description="キャラ名でチーム分けをテスト")
async def teamtest(ctx):
    await ctx.defer()

    ranks = list(RANK_POINTS.keys())
    players = []
    names = random.sample(CHAR_NAMES, 10)

    for name in names:
        rank = random.choice(ranks)
        point = RANK_POINTS[rank]
        players.append((name, rank, point))

    teamA, teamB, diff, idx, total = generate_balanced_teams(players)
    if not teamA:
        await ctx.respond("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    powerA = sum(p[2] for p in teamA)
    powerB = sum(p[2] for p in teamB)

    embed = discord.Embed(title="チーム分け結果", color=main_color)
    embed.add_field(name="🟥 アタッカー＿＿＿＿", value="\n".join([f"{p[0]} ({p[1]})" for p in teamA]) + f"\n戦力：{powerA}", inline=True)
    embed.add_field(name="🟦 ディフェンダー", value="\n".join([f"{p[0]} ({p[1]})" for p in teamB]) + f"\n戦力：{powerB}", inline=True)
    embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)

    await ctx.respond(embed=embed)


# 📝 ランク登録（上書き対応）
@peko.command(name="rank", description="自分のランクを登録します（上書き対応）")
async def rank(ctx, rank_name: str):
    user = ctx.author
    avatar_url = user.display_avatar.url
    username = user.display_name
    user_id = str(user.id)

    # --- 1. 現在のデータ取得 ---
    async with aiohttp.ClientSession() as session:
        async with session.get(GAS_WEBHOOK_URL) as response:
            existing_data = await response.json()

    # --- 2. 登録情報をGASに送信 ---
    payload = {
        "username": username,
        "user_id": user_id,
        "avatar_url": avatar_url,
        "rank": rank_name
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as response:
            if response.status == 200:
                # --- 上書き or 新規メッセージ判定 ---
                if existing_data.get("user_id") == user_id:
                    msg = f"♻️ {username} さんのランクを **{rank_name}** に更新しました！"
                else:
                    msg = f"✅ {username} さんのランク **{rank_name}** を登録しました！"
                await ctx.respond(msg)
            else:
                await ctx.respond(f"⚠️ 登録に失敗しました（{response.status}）")


bot.add_application_command(peko)


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
