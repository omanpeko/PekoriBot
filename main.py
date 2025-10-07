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
atk_color  = discord.Color.from_rgb(255, 120, 120)  # 薄い赤
def_color  = discord.Color.from_rgb(0, 180, 170)    # 青緑
info_color = discord.Color.from_rgb(126, 126, 126)  # グレー

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

# ---- ランク名 → 絵文字名マッピング ----
RANK_TO_EMOJI = {
    "アイアン1": "Iron1", "アイアン2": "Iron2", "アイアン3": "Iron3",
    "ブロンズ1": "Bronze1", "ブロンズ2": "Bronze2", "ブロンズ3": "Bronze3",
    "シルバー1": "Silver1", "シルバー2": "Silver2", "シルバー3": "Silver3",
    "ゴールド1": "Gold1", "ゴールド2": "Gold2", "ゴールド3": "Gold3",
    "プラチナ1": "Platinum1", "プラチナ2": "Platinum2", "プラチナ3": "Platinum3",
    "ダイヤ1": "Diamond1", "ダイヤ2": "Diamond2", "ダイヤ3": "Diamond3",
    "アセンダント1": "Ascendant1", "アセンダント2": "Ascendant2", "アセンダント3": "Ascendant3",
    "イモータル1": "Immortal1", "イモータル2": "Immortal2", "イモータル3": "Immortal3",
    "レディアント": "Radiant"
}

# ---- GAS URL ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"


# ============================================================
# チーム分けアルゴリズム（戦力差1以内）
# ============================================================
def generate_balanced_teams(players):
    valid_combinations = []
    all_combos = list(itertools.combinations(range(len(players)), len(players)//2))
    seen = set()

    for combo in all_combos:
        complement = tuple(sorted(set(range(len(players))) - set(combo)))
        key = tuple(sorted(combo))
        if key in seen or complement in seen:
            continue
        seen.add(key)

        teamA = [players[i] for i in combo]
        teamB = [players[i] for i in range(len(players)) if i not in combo]
        sumA = sum(p['point'] for p in teamA)
        sumB = sum(p['point'] for p in teamB)
        diff = abs(sumA - sumB)
        if diff <= 1:
            valid_combinations.append((teamA, teamB, diff))

    if not valid_combinations:
        return None, None, None, 0, 0

    total = len(valid_combinations)
    selected_index = random.randint(0, total - 1)
    teamA, teamB, diff = valid_combinations[selected_index]
    return teamA, teamB, diff, selected_index + 1, total


# ============================================================
# スラッシュコマンド
# ============================================================
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)


# ===============================
# /peko team
# ===============================
@peko.command(name="team", description="VC内メンバーをチーム分けします")
async def team(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.respond("⚠️ ボイスチャンネルに参加してから実行してください。")
        return

    members = [m for m in ctx.author.voice.channel.members if not m.bot]
    if len(members) < 2:
        await ctx.respond("⚠️ 2人以上で実行してください。")
        return

    await ctx.defer()

    user_ids = [str(m.id) for m in members]
    payload = {"action": "fetch_team_data", "user_ids": user_ids}

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as resp:
            if resp.status != 200:
                await ctx.followup.send(f"⚠️ スプレッドシート接続エラー ({resp.status})")
                return
            data = await resp.json()

    if not isinstance(data, list):
        await ctx.followup.send(f"⚠️ データ取得エラー: {data}")
        return

    # ID統一
    registered = []
    for d in data:
        try:
            rank = d.get("rank", "不明")
            point = RANK_POINTS.get(rank, 0)
            registered.append({
                "user_id": str(d.get("user_id")),
                "name": d.get("name", "不明"),
                "rank": rank,
                "point": point
            })
        except Exception as e:
            logging.warning(f"Invalid entry: {d} ({e})")

    registered_ids = {p["user_id"] for p in registered}
    unregistered = [m.display_name for m in members if str(m.id) not in registered_ids]

    if unregistered:
        msg = "⚠️ 以下のメンバーは未登録です：\n" + "\n".join(unregistered)
        await ctx.followup.send(msg)
        return

    teamA, teamB, diff, idx, total = generate_balanced_teams(registered)

    if not teamA:
        await ctx.followup.send("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    guild = ctx.guild
    emoji_dict = {e.name: e for e in guild.emojis}

    def format_player_line(p):
        emoji_name = RANK_TO_EMOJI.get(p['rank'])
        emoji = emoji_dict.get(emoji_name)
        emoji_text = f"{emoji}" if emoji else f":{emoji_name}:"
        return f"{emoji_text} {p['name']}"

    powerA = sum(p['point'] for p in teamA)
    powerB = sum(p['point'] for p in teamB)

    embed_atk = discord.Embed(title="アタッカー", color=atk_color)
    embed_def = discord.Embed(title="ディフェンダー", color=def_color)
    embed_info = discord.Embed(color=info_color)

    embed_atk.description = "\n".join([format_player_line(p) for p in teamA]) + f"\n戦力：{powerA}"
    embed_def.description = "\n".join([format_player_line(p) for p in teamB]) + f"\n戦力：{powerB}"
    embed_info.description = f"組み合わせ候補：{idx}/{total}"

    await ctx.followup.send(embeds=[embed_atk, embed_def, embed_info])


bot.add_application_command(peko)


# ===============================
# 起動処理
# ===============================
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/peko team"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です（Railway の Variables に設定してください）。")
    bot.run(token)
