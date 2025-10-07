# -*- coding: utf-8 -*-
import os
import logging
import re
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

# ---- ランク表記ゆれ対応 ----
RANK_NORMALIZE = {
    r"^(iron|あいあん|アイアン)": "アイアン",
    r"^(bronze|ぶろんず|ブロンズ|ブロ|ぶろ)": "ブロンズ",
    r"^(silver|しるば|シルバー|シル|しる)": "シルバー",
    r"^(gold|ごーるど|ゴールド|ゴル|ごる)": "ゴールド",
    r"^(plat|platinum|ぷらちな|ぷら|プラ|プラチナ)": "プラチナ",
    r"^(dia|diamond|だいや|ダイヤ)": "ダイヤ",
    r"^(ase|ascendant|あせ|汗|アセ|アセンダント)": "アセンダント",
    r"^(imm|immortal|いも|芋|イモ|イモータル|imo)": "イモータル",
    r"^(rad|radiant|れでぃ|レディ|レディアント)": "レディアント",
}

# ---- /peko グループ ----
peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)


# ✅ ランク登録コマンド
@peko.command(name="rank", description="自分のランクを登録（全角・略称・英語OK）")
async def rank(ctx, rank_name: str):
    await ctx.defer()
    user = ctx.author
    avatar_url = user.display_avatar.url
    username = user.display_name
    user_id = str(user.id)

    # --- 入力整形 ---
    input_text = rank_name.strip().lower().replace("　", "").replace(" ", "")
    input_text = re.sub(r"(\d+)", lambda m: str(int(m.group(1))), input_text)

    # --- ランク正規化 ---
    matched_rank = None
    for pattern, base in RANK_NORMALIZE.items():
        if re.match(pattern, input_text):
            m = re.search(r"(\d+)", input_text)
            num = m.group(1) if m else ""
            matched_rank = f"{base}{num}"
            break

    if not matched_rank or matched_rank not in RANK_POINTS:
        await ctx.followup.send(
            f"⚠️ `{rank_name}` は認識できませんでした。\n"
            f"例：`ゴールド2` / `gold2` / `ダイヤ3` / `ase1` など"
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


# 🗑️ 登録削除コマンド
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


# ✏️ ニックネーム変更コマンド
@peko.command(name="rename", description="登録済みのニックネームを変更します")
async def rename(ctx, new_name: str):
    await ctx.defer()
    user = ctx.author
    user_id = str(user.id)

    payload = {
        "action": "rename",
        "user_id": user_id,
        "new_name": new_name
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(GAS_WEBHOOK_URL, json=payload) as response:
            text = await response.text()
            if "UPDATED_RENAME" in text:
                msg = f"✏️ {user.display_name} さんの登録名を **{new_name}** に変更しました。"
            elif "NOT_FOUND" in text:
                msg = f"⚠️ 登録データが見つかりませんでした。まず `/peko rank` で登録してください。"
            else:
                msg = f"⚠️ 変更に失敗しました（{response.status}）"
            await ctx.followup.send(msg)


# ---- 起動 ----
bot.add_application_command(peko)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/peko rank"))
    logging.info(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です（Railway の Variables に設定してください）。")
    bot.run(token)
