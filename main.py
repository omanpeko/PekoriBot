# -*- coding: utf-8 -*-
import os
import re
import logging
import random
import itertools
import aiohttp
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option

logging.basicConfig(level=logging.INFO)

# ============================================================
# ⚙️ Discord Bot 設定
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- 対応する複数サーバーID ----
GUILD_IDS = [
    1357655899212349490,  # あなたのサーバー
    932269784228306995,   # CYNTHIA
    1131436758970671104,  # ぺこ
]

# ---- データベース代わりの固定プレイヤーリスト ----
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

# ---- カラー設定 ----
main_color = discord.Color.from_rgb(255, 140, 0)

# ---- GAS Webhook URL ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"

# ============================================================
# 🧮 ランクポイントテーブル
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
# ⚔️ チーム分けロジック（重複除外＋ランダム反転）
# ============================================================
def generate_balanced_teams(players):
    all_combos = list(itertools.combinations(range(len(players)), len(players)//2))
    seen_pairs = set()  # A↔B同一扱い

    for max_diff in range(1, 999):
        valid_combos = []
        for combo in all_combos:
            teamA = [players[i] for i in combo]
            teamB = [players[i] for i in range(len(players)) if i not in combo]

            teamA_names = frozenset(p[0] for p in teamA)
            teamB_names = frozenset(p[0] for p in teamB)
            pair_key = frozenset([teamA_names, teamB_names])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            sumA = sum(p[2] for p in teamA)
            sumB = sum(p[2] for p in teamB)
            diff = abs(sumA - sumB)

            if diff <= max_diff:
                valid_combos.append((teamA, teamB, diff))

        if valid_combos:
            total = len(valid_combos)
            idx = random.randint(0, total - 1)
            teamA, teamB, diff = valid_combos[idx]
            # ✅ ランダムにアタッカー・ディフェンダー入れ替え
            if random.choice([True, False]):
                teamA, teamB = teamB, teamA

            logging.info(f"✅ 戦力差 {max_diff} 以下でマッチ成功 ({len(valid_combos)}通り)")
            return teamA, teamB, diff, idx + 1, total

    return None, None, None, 0, 0

# ============================================================
# 🧩 カスタム絵文字でランク表示
# ============================================================
def get_rank_emoji(rank_name: str, emoji_dict: dict) -> str:
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
    emoji_key = f"{emoji_name}{num}" if num else emoji_name
    emoji = emoji_dict.get(emoji_key)
    return str(emoji) if emoji else f":{emoji_key}:"

# ============================================================
# 🧩 /peko コマンドグループ
# ============================================================
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)

# ============================================================
# 🏅 /peko rank（入力欄付き）
# ============================================================
@peko.command(
    name="rank",
    description="自分のランクを登録（例：ゴールド2 / silver3 / ase1）"
)
async def rank(
    ctx,
    rank_name: Option(str, "ランク名を入力（例：ゴールド2 / gold2 / ダイヤモンド3 / ase1 など）")
):
    await ctx.defer()
    user = ctx.author
    avatar_url = user.display_avatar.url
    username = user.display_name
    user_id = str(user.id)

    if not rank_name:
        await ctx.followup.send("⚠️ ランク名を入力してください。")
        return

    input_text = rank_name.strip().lower().replace("　", "").replace(" ", "")
    input_text = re.sub(r"[０-９]", lambda m: chr(ord(m.group(0)) - 65248), input_text)
    input_text = re.sub(r"(\d+)", lambda m: str(int(m.group(1))), input_text)

    # ---- ランク表記ゆれ ----
    matched_rank = None
    RANK_NORMALIZE = {
        r"^(iron|あいあん|アイアン)": "アイアン",
        r"^(bronze|ぶろんず|ブロンズ|ブロ|ぶろ)": "ブロンズ",
        r"^(silver|しるばー|しる|シルバー|シル|汁)": "シルバー",
        r"^(gold|ごーるど|ゴールド|ゴル|ごる)": "ゴールド",
        r"^(plat|platinum|ぷらちな|ぷら|プラ|プラチナ)": "プラチナ",
        r"^(dia|diamond|だいや|だいやもんど|ダイヤ|ダイヤモンド)": "ダイヤモンド",
        r"^(ase|ascendant|あせ|汗|アセ|アセンダント)": "アセンダント",
        r"^(imm|immortal|いも|芋|イモ|イモータル|imo)": "イモータル",
        r"^(rad|radiant|れでぃ|レディ|レディアント)": "レディアント",
    }

    for pattern, base in RANK_NORMALIZE.items():
        if re.match(pattern, input_text):
            m = re.search(r"(\d+)", input_text)
            num = m.group(1) if m else ""
            matched_rank = f"{base}{num}"
            break

    if not matched_rank or matched_rank not in RANK_POINTS:
        await ctx.followup.send(
            f"⚠️ `{rank_name}` は認識できませんでした。\n"
            f"例：`ゴールド2` / `gold2` / `ダイヤモンド3` / `ase1` など"
        )
        return

    # ---- GASへ送信 ----
    payload = {
        "action": "add",
        "username": username,
        "user_id": user_id,
        "avatar_url": avatar_url,
        "rank": matched_rank
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as response:
            text = await response.text()
            if response.status == 200:
                if "UPDATED" in text:
                    msg = f"🔁 {username} さんのランクを **{matched_rank}** に更新しました！"
                elif "ADDED" in text:
                    msg = f"✅ {username} さんのランク **{matched_rank}** を新規登録しました！"
                else:
                    msg = f"✅ {username} さんのランク **{matched_rank}** を登録しました！（不明レスポンス）"
                await ctx.followup.send(msg)
            else:
                await ctx.followup.send(f"⚠️ 登録に失敗しました（{response.status}）")

# ============================================================
# 🚀 起動時処理
# ============================================================
bot.add_application_command(peko)

@bot.event
async def on_ready():
    await bot.sync_commands()
    logging.info(f"✅ コマンド同期完了: {len(bot.application_commands)} 件")
    await bot.change_presence(activity=discord.Game(name="/peko rank / team / teamtest"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です。")
    bot.run(token)
