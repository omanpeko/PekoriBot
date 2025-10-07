# -*- coding: utf-8 -*-
import os
import logging
import random
import itertools
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
main_color = discord.Color.from_rgb(255, 140, 0)  # オレンジ (#FF8C00)

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

# ---- キャラ名リスト（4〜9文字）----
CHAR_NAMES = [
    # 4文字
    "リオナ", "カレン", "ユウキ", "トウマ", "サララ",
    # 5文字
    "アキトラ", "ミナト", "レイナ", "タカオ", "シズク",
    # 6文字
    "ハルフォ", "アマリス", "カグラミ", "リベルタ", "ノアール",
    # 7文字
    "セレスティ", "ユリウスナ", "ルミナリア", "カナデアス", "アーディン",
    # 8文字
    "シグルディア", "ラファエリア", "フィオレンテ", "グランディア", "アルフォリア",
    # 9文字（新規）
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


@peko.command(name="teamtest", description="キャラ名（4〜9文字）でチーム分けをテスト")
async def teamtest(ctx):
    await ctx.defer()

    ranks = list(RANK_POINTS.keys())
    players = []

    # 10人分のキャラ名をランダムに選ぶ（重複なし）
    names = random.sample(CHAR_NAMES, 10)

    for name in names:
        rank = random.choice(ranks)
        point = RANK_POINTS[rank]
        players.append((name, rank, point))

    teamA, teamB, diff, idx, total = generate_balanced_teams(players)

    if not teamA:
        await ctx.respond("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    guild = ctx.guild
    emoji_dict = {e.name: e for e in guild.emojis}

    def format_player_line(p):
        name, rank, _ = p
        emoji_name = RANK_TO_EMOJI.get(rank)
        emoji = emoji_dict.get(emoji_name)
        emoji_text = f"{emoji}" if emoji else f":{emoji_name}:"
        return f"{emoji_text} {name}"

    # チームごとの戦力値
    powerA = sum(p[2] for p in teamA)
    powerB = sum(p[2] for p in teamB)

    # ---- Embed（横並び）----
    embed = discord.Embed(title="チーム分け結果", color=main_color)

    embed.add_field(
        name="🟥 アタッカー＿＿＿＿",
        value="\n".join([format_player_line(p) for p in teamA]) + f"\n戦力：{powerA}",
        inline=True
    )
    embed.add_field(
        name="🟦 ディフェンダー",
        value="\n".join([format_player_line(p) for p in teamB]) + f"\n戦力：{powerB}",
        inline=True
    )

    # 情報欄 → 改行代わり（全角スペース）
    embed.add_field(
        name="　",
        value=f"組み合わせ候補：{idx}/{total}",
        inline=False
    )

    await ctx.respond(embed=embed)


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
