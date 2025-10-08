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

# ============================================================
# ★複数サーバー対応
# ============================================================
GUILD_IDS = [
    1357655899212349490,  # あなたのサーバー
    932269784228306995,   # CYNTHIA
    1131436758970671104,  # ぺこ
]

# ============================================================
# ★固定プレイヤーデータ（テスト用DB）
# ============================================================
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

# ============================================================
# Discord Bot設定
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

main_color = discord.Color.from_rgb(255, 140, 0)
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"

# ============================================================
# ランク関連
# ============================================================
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

# ============================================================
# チーム分けアルゴリズム（戦力差を段階的に緩和）
# ============================================================
def generate_balanced_teams(players):
    all_combos = list(itertools.combinations(range(len(players)), len(players)//2))
    seen = set()

    for max_diff in range(1, 999):  # 戦力差1以内から徐々に緩和
        valid_combinations = []
        for combo in all_combos:
            complement = tuple(sorted(set(range(len(players))) - set(combo)))
            key = tuple(sorted(combo))
            if key in seen or complement in seen:
                continue
            seen.add(key)

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
# スラッシュコマンドグループ
# ============================================================
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)


# ============================================================
# 🎮 /peko teamtest（固定データベースでチーム分け）
# ============================================================
@peko.command(name="teamtest", description="VCを使わず固定リストから10人をチーム分けします")
async def teamtest(ctx):
    await ctx.defer()

    # ダミープレイヤー名・ランクをランダム生成
    ranks = list(RANK_POINTS.keys())
    players = []

    for pid in PLAYER_IDS:
        name = f"Player{str(pid)[-3:]}"  # 一応ユニークな名前
        rank = random.choice(ranks)
        point = RANK_POINTS[rank]
        players.append((name, rank, point))

    # 10人ちょうど
    teamA, teamB, diff, idx, total = generate_balanced_teams(players)
    if not teamA:
        await ctx.respond("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    # 戦力計算
    powerA = sum(p[2] for p in teamA)
    powerB = sum(p[2] for p in teamB)

    # Embed出力
    embed = discord.Embed(title="チーム分けテスト結果", color=main_color)
    embed.add_field(name="🟥 アタッカー＿＿＿＿", value="\n".join([f"{p[0]} ({p[1]})" for p in teamA]) + f"\n戦力：{powerA}", inline=True)
    embed.add_field(name="🟦 ディフェンダー", value="\n".join([f"{p[0]} ({p[1]})" for p in teamB]) + f"\n戦力：{powerB}", inline=True)
    embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)

    await ctx.respond(embed=embed)


# ============================================================
# 🔧 その他の既存コマンドはそのまま（rank/remove/teamなど）
# ============================================================
# （既にあなたの rank/remove/team 実装がある部分をそのまま残してください）


bot.add_application_command(peko)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/peko teamtest /peko team"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です。")
    bot.run(token)
