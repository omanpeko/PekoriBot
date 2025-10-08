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

# ---- サーバーID ----
GUILD_IDS = [
    1357655899212349490,  # あなたのサーバー
    932269784228306995,   # CYNTHIA
    1131436758970671104,  # ぺこ
]

# ---- データベース代わりの固定リスト ----
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

# ---- GAS URL ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbztYZmisYPC_BbyY-lNG296sIQHZBo_iu1xMcf8M_5_QJX7DGUNcz5Z2HP2gWgW-RvvEg/exec"

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

# ============================================================
# 🧮 チーム分けアルゴリズム（戦力差を段階的に緩和）
# ============================================================
def generate_balanced_teams(players):
    all_combos = list(itertools.combinations(range(len(players)), len(players)//2))
    seen = set()

    for max_diff in range(1, 999):  # 1以下から順に緩和
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
# 🧩 スラッシュコマンド
# ============================================================
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)


# ✅ ランク登録
@peko.command(name="rank", description="自分のランクを登録（例：/peko rank ゴールド２）")
async def rank(ctx):
    await ctx.defer()
    user = ctx.author
    avatar_url = user.display_avatar.url
    username = user.display_name
    user_id = str(user.id)

    full_text = ctx.interaction.data.get("options")
    if not full_text:
        await ctx.followup.send("⚠️ ランクを入力してください（例：`/peko rank ゴールド2`）")
        return
    rank_name = full_text[0]["value"]

    input_text = rank_name.strip().lower().replace("　", "").replace(" ", "")
    input_text = re.sub(r"[０-９]", lambda m: chr(ord(m.group(0)) - 65248), input_text)
    input_text = re.sub(r"(\d+)", lambda m: str(int(m.group(1))), input_text)

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


# 🗑️ 登録削除
@peko.command(name="remove", description="自分のランク登録データを削除します")
async def remove(ctx):
    await ctx.defer()
    user = ctx.author
    user_id = str(user.id)

    payload = {"action": "remove", "user_id": user_id}

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as response:
            text = await response.text()
            if "REMOVED" in text:
                msg = f"🗑️ {user.display_name} さんの登録データを削除しました。"
            elif "NOT_FOUND" in text:
                msg = f"⚠️ {user.display_name} さんの登録データは見つかりませんでした。"
            else:
                msg = f"⚠️ 削除処理に失敗しました（{response.status}）"
            await ctx.followup.send(msg)


# 🎮 チーム分け（VCベース）
@peko.command(name="team", description="VC内メンバーをランクデータからチーム分けします")
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

    players = []
    for d in data:
        name = d.get("name", "不明")
        rank = d.get("rank", "不明")
        point = RANK_POINTS.get(rank, 0)
        players.append((name, rank, point, d.get("user_id")))

    registered_ids = {p[3] for p in players}
    unregistered = [m.display_name for m in members if str(m.id) not in registered_ids]
    if unregistered:
        msg = "⚠️ 以下のメンバーは未登録です：\n" + "\n".join(unregistered)
        await ctx.followup.send(msg)
        return

    teamA, teamB, diff, idx, total = generate_balanced_teams(players)
    if not teamA:
        await ctx.followup.send("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    powerA = sum(p[2] for p in teamA)
    powerB = sum(p[2] for p in teamB)

    embed = discord.Embed(title="チーム分け結果", color=main_color)
    embed.add_field(name="🟥 アタッカー＿＿＿＿", value="\n".join([f"{p[0]} ({p[1]})" for p in teamA]) + f"\n戦力：{powerA}", inline=True)
    embed.add_field(name="🟦 ディフェンダー", value="\n".join([f"{p[0]} ({p[1]})" for p in teamB]) + f"\n戦力：{powerB}", inline=True)
    embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)

    await ctx.followup.send(embed=embed)


# 🧪 チームテスト（固定データ）
@peko.command(name="teamtest", description="固定リストの10人を使ってチーム分けをテストします")
async def teamtest(ctx):
    await ctx.defer()

    test_ids = [pid for pid in PLAYER_IDS if pid != 1180887237664186454]
    payload = {"action": "fetch_team_data", "user_ids": [str(pid) for pid in test_ids]}

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as resp:
            if resp.status != 200:
                await ctx.followup.send(f"⚠️ スプレッドシート接続エラー ({resp.status})")
                return
            data = await resp.json()

    players = []
    for d in data:
        name = d.get("name", "不明")
        rank = d.get("rank", "不明")
        point = RANK_POINTS.get(rank, 0)
        players.append((name, rank, point, d.get("user_id")))

    teamA, teamB, diff, idx, total = generate_balanced_teams(players)
    if not teamA:
        await ctx.followup.send("⚠️ 条件を満たすチーム分けが見つかりませんでした。")
        return

    powerA = sum(p[2] for p in teamA)
    powerB = sum(p[2] for p in teamB)

    embed = discord.Embed(title="チーム分けテスト結果", color=main_color)
    embed.add_field(name="🟥 アタッカー＿＿＿＿", value="\n".join([f"{p[0]} ({p[1]})" for p in teamA]) + f"\n戦力：{powerA}", inline=True)
    embed.add_field(name="🟦 ディフェンダー", value="\n".join([f"{p[0]} ({p[1]})" for p in teamB]) + f"\n戦力：{powerB}", inline=True)
    embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)

    await ctx.followup.send(embed=embed)


# ============================================================
# 起動イベント
# ============================================================
bot.add_application_command(peko)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/peko rank / team / teamtest"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です。")
    bot.run(token)
