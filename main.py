# -*- coding: utf-8 -*-
import os
import re
import random
import ast
import json
import itertools
import aiohttp
import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option

CUSTOM_EMOJIS = {} 

logging.basicConfig(level=logging.INFO)

# ============================================================
# ⚙️ Discord Bot 設定
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- 対応サーバーID ----
GUILD_IDS = [
    1357655899212349490,  # あなたのサーバー
]

# ---- GAS Webhook URLs ----
GAS_RANK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"
GAS_SLIDE_URL = "https://script.google.com/macros/s/AKfycbwCRqFmTZTSLVBnIUEasJviLwjvhe1WD3XE9yC7PF3JGa28E20iqf3ivb_DRHA0leivQQ/exec"

# ---- テスト用プレイヤーID ----
PLAYER_IDS = [
    447824706477752321,
    845865706126180393,
    614039479392403466,
    390490936141938689,
    376713061492588544,
    762622138753613844,
    839719526576029696,
    766636872797519882,
    396605996816007168,
    708629437083680768,
]

main_color = discord.Color.from_rgb(255, 140, 0)

# ============================================================
# 🧮 ランクポイント
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
# ⚔️ チーム分けロジック
# ============================================================
def generate_balanced_teams(players):
    all_combos = list(itertools.combinations(range(len(players)), len(players)//2))
    seen_pairs = set()

    for max_diff in range(1, 999):
        valid_combos = []
        for combo in all_combos:
            teamA = [players[i] for i in combo]
            teamB = [players[i] for i in range(len(players)) if i not in combo]

            pair_key = frozenset([
                frozenset(p[0] for p in teamA),
                frozenset(p[0] for p in teamB)
            ])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            sumA, sumB = sum(p[2] for p in teamA), sum(p[2] for p in teamB)
            diff = abs(sumA - sumB)
            if diff <= max_diff:
                valid_combos.append((teamA, teamB, diff))

        if valid_combos:
            total = len(valid_combos)
            idx = random.randint(0, total - 1)
            teamA, teamB, diff = valid_combos[idx]
            if random.choice([True, False]):
                teamA, teamB = teamB, teamA
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
    emoji_key = f"{emoji_name}{num}".lower()

    # 🔥 str(emoji) で登録されてるので、これが直接 <::>形式で返る！
    return emoji_dict.get(emoji_key, rank_name)


# ============================================================
# 🧩 コマンドグループ
# ============================================================
peko = SlashCommandGroup("peko", "PekoriBotコマンド群", guild_ids=GUILD_IDS)

# ============================================================
# 🏅 /peko rank（ランク登録）
# ============================================================
@peko.command(name="rank", description="自分のランクを登録します（例：ゴールド2 / diamond1 / ase3など）")
async def rank(
    ctx,
    rank_name: Option(str, "ランク名を入力（例：ゴールド2 / gold2 / ダイヤモンド3 / ase1）")
):
    await ctx.defer()
    user = ctx.author
    username = user.display_name
    user_id = str(user.id)
    avatar_url = user.display_avatar.url

    if not rank_name:
        await ctx.followup.send("⚠️ ランク名を入力してください。")
        return

    # ---- 正規化処理 ----
    input_text = rank_name.strip().lower().replace("　", "").replace(" ", "")
    input_text = re.sub(r"[０-９]", lambda m: chr(ord(m.group(0)) - 65248), input_text)
    input_text = re.sub(r"(\d+)", lambda m: str(int(m.group(1))), input_text)

    RANK_NORMALIZE = {
        r"^(iron|あいあん|アイアン)": "アイアン",
        r"^(bronze|ぶろんず|ブロンズ|ブロ|ぶろ)": "ブロンズ",
        r"^(silver|しるばー|シルバー|しる|汁)": "シルバー",
        r"^(gold|ごーるど|ゴールド|ごる|ゴル)": "ゴールド",
        r"^(plat|platinum|ぷらちな|プラ|ぷら)": "プラチナ",
        r"^(dia|diamond|だいや|ダイヤ|だいやもんど)": "ダイヤモンド",
        r"^(ase|ascendant|アセ|アセンダント|汗)": "アセンダント",
        r"^(imm|immortal|いも|イモータル|imo|芋)": "イモータル",
        r"^(rad|radiant|れでぃ|レディアント|レディ)": "レディアント",
    }

    matched_rank = None
    for pattern, base in RANK_NORMALIZE.items():
        if re.match(pattern, input_text):
            m = re.search(r"(\d+)", input_text)
            num = m.group(1) if m else ""
            matched_rank = f"{base}{num}"
            break

    if not matched_rank or matched_rank not in RANK_POINTS:
        await ctx.followup.send(
            f"⚠️ `{rank_name}` は認識できませんでした。\n例：`ゴールド2` / `gold2` / `ダイヤモンド3` / `ase1`"
        )
        return

    payload = {
        "action": "add",
        "username": username,
        "user_id": user_id,
        "avatar_url": avatar_url,
        "rank": matched_rank,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_RANK_URL, json=payload) as r:
            text = await r.text()
            if "UPDATED" in text:
                msg = f"🔁 {username} さんのランクを **{matched_rank}** に更新しました！"
            elif "ADDED" in text:
                msg = f"✅ {username} さんのランク **{matched_rank}** を登録しました！"
            else:
                msg = f"✅ {username} さんのランク **{matched_rank}** を登録しました！（不明レスポンス）"
            await ctx.followup.send(msg)

# ============================================================
# 🧹 /peko remove
# ============================================================
@peko.command(name="remove", description="自分のランク登録を削除します")
async def remove(ctx):
    await ctx.defer()
    user_id = str(ctx.author.id)
    payload = {"action": "remove", "user_id": user_id}
    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_RANK_URL, json=payload) as r:
            text = await r.text()
            if "REMOVED" in text:
                msg = f"🗑️ {ctx.author.display_name} さんのデータを削除しました。"
            elif "NOT_FOUND" in text:
                msg = f"⚠️ 登録データが見つかりませんでした。"
            else:
                msg = f"⚠️ 削除失敗（{r.status}）"
            await ctx.followup.send(msg)

# ============================================================
# 🧩 共通チーム処理関数（Embed出力＋GASスライド画像埋め込み）
# ============================================================
async def process_team_result(ctx, data):
    """共通: チーム分け計算 → Embed出力 → GASへ送信して画像表示"""
    global CUSTOM_EMOJIS
    players = []
    for d in data:
        name = d.get("name", "不明")
        rank = d.get("rank", "不明")
        icon = d.get("icon") or d.get("iconUrl") or ""
        point = RANK_POINTS.get(rank, 0)
        players.append((name, rank, point, icon))

    teamA, teamB, diff, idx, total = generate_balanced_teams(players)
    powerA = sum(p[2] for p in teamA)
    powerB = sum(p[2] for p in teamB)

    # =============================
    # Embed生成（チーム結果）
    # =============================
    embed = discord.Embed(title="チーム分け結果", color=main_color)
    embed.add_field(
        name="🟥 アタッカー",
        value="\n".join(
            [f"{get_rank_emoji(p[1], CUSTOM_EMOJIS)} {p[0]}" for p in teamA]
        ) + f"\nポイント：{powerA}",
        inline=True,
    )
    embed.add_field(
        name="🟦 ディフェンダー",
        value="\n".join(
            [f"{get_rank_emoji(p[1], CUSTOM_EMOJIS)} {p[0]}" for p in teamB]
        ) + f"\nポイント：{powerB}",
        inline=True,
    )
    embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)
    await ctx.followup.send(embed=embed)

    # =============================
    # GASスライド生成（画像URL取得）
    # =============================
    payload2 = {
        "action": "update_slide",
        "teamA": [{"name": p[0], "icon": p[3], "rank": p[1]} for p in teamA],
        "teamB": [{"name": p[0], "icon": p[3], "rank": p[1]} for p in teamB],
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_SLIDE_URL, json=payload2) as r2:
            text = await r2.text()
            try:
                result = json.loads(text)
                image_url = result.get("url")
                if image_url:
                    img_embed = discord.Embed(color=main_color)
                    img_embed.set_image(url=image_url)
                    await ctx.followup.send(embed=img_embed)
                else:
                    await ctx.followup.send(f"⚠️ GAS応答にURLがありません。\n{text}")
            except Exception as e:
                await ctx.followup.send(f"⚠️ GAS応答の解析失敗: {e}\n{text}")



# ============================================================
# 🎮 /peko team
# ============================================================
@peko.command(name="team", description="VCメンバーでチーム分け＋スライド更新")
async def team(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.respond("⚠️ ボイスチャンネルに参加してください。")
        return

    members = [m for m in ctx.author.voice.channel.members if not m.bot]
    if len(members) < 2:
        await ctx.respond("⚠️ 2人以上で実行してください。")
        return

    await ctx.defer()
    user_ids = [str(m.id) for m in members]
    await process_team_result(ctx, data)

# ============================================================
# 🧪 /peko teamtest
# ============================================================
@peko.command(name="teamtest", description="RankDatabaseから10人を取得してチーム分けテスト")
async def teamtest(ctx):
    await ctx.defer()

    payload = {"action": "fetch_team_data", "user_ids": [str(i) for i in PLAYER_IDS]}

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_RANK_URL, json=payload) as r:
            try:
                data = await r.json() 
            except Exception as e:
                text = await r.text()
                await ctx.followup.send(f"⚠️ JSON変換失敗: {e}\n{text}")
                return

    # ✅ チーム処理（共通関数）
    await process_team_result(ctx, data)

# ============================================================
# 🚀 起動
# ============================================================
bot.add_application_command(peko)

@bot.event
async def on_ready():
    await bot.sync_commands()
    logging.info("✅ PekoriBot v1.5 コマンド同期完了")

    await bot.change_presence(activity=discord.Game(name="/peko rank / team / teamtest / remove"))
    logging.info(f"✅ ログイン完了: {bot.user} ({bot.user.id})")

    # 🎨 ログイン完了後に絵文字読み込みタスクを起動
    bot.loop.create_task(load_custom_emojis())


# ============================================================
# 🎨 カスタム絵文字読み込みタスク
# ============================================================
async def load_custom_emojis():
    global CUSTOM_EMOJIS
    CUSTOM_EMOJIS.clear()

    # 少し待ってから（ギルド情報同期を安定させる）
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=3))

    emoji_count = 0
    for guild in bot.guilds:
        logging.info(f"🧩 ギルド読込中: {guild.name}")
        for emoji in guild.emojis:
            CUSTOM_EMOJIS[emoji.name.lower()] = str(emoji)
            emoji_count += 1

    logging.info(f"✅ カスタム絵文字読み込み完了: {emoji_count}個")


# ============================================================
# メインエントリポイント
# ============================================================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("DISCORD_TOKEN が未設定です。")
    bot.run(token)

