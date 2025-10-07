# -*- coding: utf-8 -*-
import os
import logging
import random
import itertools
import re
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
import aiohttp  # GAS連携

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

# ---- Google Apps Script URL ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"

# ---- ランクポイント辞書 ----
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

# ---- ランク名ゆれ → 正規化テーブル ----
RANK_NORMALIZE = {
    # Iron
    r"^(iron|あいあん|アイアン)": "アイアン",
    # Bronze
    r"^(bronze|ぶろんず|ブロンズ)": "ブロンズ",
    # Silver
    r"^(silver|しるば|シルバー)": "シルバー",
    # Gold
    r"^(gold|ごーるど|ゴールド)": "ゴールド",
    # Platinum
    r"^(plat|platinum|ぷらちな|プラチナ)": "プラチナ",
    # Diamond
    r"^(dia|diamond|だいや|ダイヤ)": "ダイヤ",
    # Ascendant
    r"^(ase|ascendant|あせ|アセンダント)": "アセンダント",
    # Immortal
    r"^(imm|immortal|いも|イモータル)": "イモータル",
    # Radiant
    r"^(rad|radiant|れでぃ|レディアント)": "レディアント",
}

# ---- チーム分けアルゴリズム（前と同じ）----
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


# 📝 ランク登録コマンド（入力ゆれ対応）
@peko.command(name="rank", description="自分のランクを登録（全角・英語・略称OK）")
async def rank(ctx, rank_name: str):
    user = ctx.author
    avatar_url = user.display_avatar.url
    username = user.display_name
    user_id = str(user.id)

    # 入力整形
    input_text = rank_name.strip().lower().replace("　", "").replace(" ", "")
    input_text = re.sub(r"(\d+)", lambda m: str(int(m.group(1))), input_text)  # 全角数字→半角数字

    # --- ランク正規化 ---
    matched_rank = None
    for pattern, base in RANK_NORMALIZE.items():
        if re.match(pattern, input_text):
            # 数字がある場合は末尾に追加
            m = re.search(r"(\d+)", input_text)
            num = m.group(1) if m else ""
            matched_rank = f"{base}{num}"
            break

    # 不明ランク対応
    if not matched_rank or matched_rank not in RANK_POINTS:
        await ctx.respond(f"⚠️ `{rank_name}` は認識できませんでした。例：`ゴールド2` / `gold2` / `plat3` など")
        return

    # --- GASに送信 ---
    payload = {
        "username": username,
        "user_id": user_id,
        "avatar_url": avatar_url,
        "rank": matched_rank
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as response:
            if response.status == 200:
                await ctx.respond(f"✅ {username} さんのランク **{matched_rank}** を登録しました！")
            else:
                await ctx.respond(f"⚠️ 登録に失敗しました（{response.status}）")


bot.add_application_command(peko)


# ---- 起動 ----
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/peko rank"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です（Railway の Variables に設定してください）。")
    bot.run(token)
