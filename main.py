# -*- coding: utf-8 -*-
import os
import re
import logging
import random
import itertools
import aiohttp
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

logging.basicConfig(level=logging.INFO)

# ---- Discord設定 ----
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- 対応する複数サーバーID ----
GUILD_IDS = [
    1357655899212349490,  # あなたのサーバー
    #932269784228306995,   # CYNTHIA
    #1131436758970671104,  # ぺこ
]

# ---- カラー設定 ----
main_color = discord.Color.from_rgb(255, 140, 0)

# ---- ランクポイント ----
RANK_POINTS = {
    "アイアン1": 1, "アイアン2": 2, "アイアン3": 3,
    "ブロンズ1": 4, "ブロンズ2": 5, "ブロンズ3": 6,
    "シルバー1": 7, "シルバー2": 8, "シルバー3": 9,
    "ゴールド1": 10, "ゴールド2": 11, "ゴールド3": 12,
    "プラチナ1": 13, "プラチナ2": 14, "プラチナ3": 15,
    "ダイヤモンド1": 16, "ダイヤモンド2": 17, "ダイヤモンド3": 18,
    "アセンダント1": 19, "アセンダント2": 20, "アセンダント3": 21,
    "イモータル1": 22, "イモータル2": 23, "イモータル3": 24,
    "レディアント": 25
}

# ---- 固定プレイヤーIDリスト（teamtest用） ----
PLAYER_IDS = [
    447824706477752321,
    845865706126180393,
    614039479392403466,
    # 除外対象: 1180887237664186454,
    390490936141938689,
    376713061492588544,
    762622138753613844,
    839719526576029696,
    766636872797519882,
    396605996816007168,
    708629437083680768,
]

# ---- GAS Webhook URL ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"


# ============================================================
# 🧮 チーム分けアルゴリズム（重複除外＋戦力差を段階的に緩和）
# ============================================================
def generate_balanced_teams(players):
    all_combos = list(itertools.combinations(range(len(players)), len(players)//2))
    seen_teams = set()

    for max_diff in range(1, 999):  # 戦力差を1から順に広げて探す
        valid_combinations = []

        for combo in all_combos:
            teamA_names = frozenset(players[i][0] for i in combo)
            if teamA_names in seen_teams:
                continue
            seen_teams.add(teamA_names)

            teamA = [players[i] for i in combo]
            teamB = [players[i] for i in range(len(players)) if i not in combo]

            sumA = sum(p[2] for p in teamA)
            sumB = sum(p[2] for p in teamB)
            diff = abs(sumA - sumB)

            if diff <= max_diff:
                valid_combinations.append((teamA, teamB, diff))

        if valid_combinations:
            total = len(valid_combinations)
            selected_index = random.randint(0, total - 1)
            teamA, teamB, diff = valid_combinations[selected_index]
            logging.info(f"✅ 戦力差 {max_diff} 以下でマッチング成功 ({len(valid_combinations)}通り)")
            return teamA, teamB, diff, selected_index + 1, total

    return None, None, None, 0, 0


# ============================================================
# 🧩 ランク→絵文字変換関数
# ============================================================
def get_rank_emoji(rank_name: str) -> str:
    if not rank_name:
        return ""
    base = re.sub(r"\d", "", rank_name)
    emoji_name = {
        "アイアン": "Iron",
        "ブロンズ": "Bronze",
        "シルバー": "Silver",
        "ゴールド": "Gold",
        "プラチナ": "Platinum",
        "ダイヤモンド": "Diamond",
        "アセンダント": "Ascendant",
        "イモータル": "Immortal",
        "レディアント": "Radiant",
    }.get(base, "")
    num = re.sub(r"\D", "", rank_name)
    return f":{emoji_name}{num}:" if emoji_name else ""


# ============================================================
# 🧩 スラッシュコマンド
# ============================================================
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)


# 🎮 チーム分けテスト（VCを無視して固定データで動作）
@peko.command(name="teamtest", description="固定データでチーム分けテストを実行します")
async def teamtest(ctx):
    await ctx.defer()

    # --- スプレッドシートからデータ取得 ---
    payload = {"action": "fetch_team_data", "user_ids": [str(i) for i in PLAYER_IDS]}

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as resp:
            if resp.status != 200:
                await ctx.followup.send(f"⚠️ スプレッドシート接続エラー ({resp.status})")
                return
            data = await resp.json()

    if not isinstance(data, list) or len(data) < 2:
        await ctx.followup.send("⚠️ データが不足しています。")
        return

    # --- 除外ユーザーを排除して10人だけ使う ---
    players = []
    for d in data:
        uid = int(d.get("user_id", 0))
        if uid == 1180887237664186454:
            continue
        name = d.get("name", "不明")
        rank = d.get("rank", "不明")
        point = RANK_POINTS.get(rank, 0)
        players.append((name, rank, point, uid))

    if len(players) < 2:
        await ctx.followup.send("⚠️ 登録データが足りません。")
        return

    # --- チーム分け実行 ---
    teamA, teamB, diff, idx, total = generate_balanced_teams(players)
    if not teamA:
        await ctx.followup.send("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    # --- 戦力計算 ---
    powerA = sum(p[2] for p in teamA)
    powerB = sum(p[2] for p in teamB)

    # --- Embed 出力 ---
    embed = discord.Embed(title="チーム分けテスト結果", color=main_color)
    embed.add_field(
        name="🟥 アタッカー",
        value="\n".join([f"{get_rank_emoji(p[1])} {p[0]}" for p in teamA]) + f"\n戦力：{powerA}",
        inline=True
    )
    embed.add_field(
        name="🟦 ディフェンダー",
        value="\n".join([f"{get_rank_emoji(p[1])} {p[0]}" for p in teamB]) + f"\n戦力：{powerB}",
        inline=True
    )
    embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)
    await ctx.followup.send(embed=embed)


# ============================================================
# 🚀 起動処理
# ============================================================
bot.add_application_command(peko)

@bot.event
async def on_ready():
    for gid in GUILD_IDS:
        try:
            guild = discord.Object(id=gid)
            await bot.sync_commands(guild)
            logging.info(f"✅ コマンド同期成功: {gid}")
        except Exception as e:
            logging.warning(f"⚠️ 同期失敗 {gid}: {e}")

    await bot.change_presence(activity=discord.Game(name="/peko teamtest"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です。")
    bot.run(token)
