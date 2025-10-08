# valorant_bot.py
# =============================================
# PekoriBot v1.2 - Core Logic
# =============================================
import os
import re
import logging
import random
import itertools
import aiohttp
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option

# ------------------------------------------------
# 🧩 Bot本体生成関数（main.pyから呼び出される）
# ------------------------------------------------
def create_bot():
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

    # ---- GAS Webhook URL ----
    GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwCRqFmTZTSLVBnIUEasJviLwjvhe1WD3XE9yC7PF3JGa28E20iqf3ivb_DRHA0leivQQ/exec"

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

                teamA_names = frozenset(p[0] for p in teamA)
                teamB_names = frozenset(p[0] for p in teamB)
                pair_key = frozenset([teamA_names, teamB_names])
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

                # ✅ ランダムに左右を入れ替え
                if random.choice([True, False]):
                    teamA, teamB = teamB, teamA

                return teamA, teamB, diff, idx + 1, total

        return None, None, None, 0, 0

    # ============================================================
    # 🧩 カスタム絵文字対応
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
    # 🧩 スラッシュコマンド定義
    # ============================================================
    peko = SlashCommandGroup("peko", "PekoriBotのコマンド群", guild_ids=GUILD_IDS)

    # ------------------------------------------------------------
    # 🏅 /peko rank
    # ------------------------------------------------------------
    @peko.command(name="rank", description="自分のランクを登録（例：ゴールド2 / ダイヤモンド3 / ase1）")
    async def rank(ctx, rank_name: Option(str, "ランク名を入力")):
        await ctx.defer()
        user = ctx.author
        username = user.display_name
        avatar_url = user.display_avatar.url
        user_id = str(user.id)

        if not rank_name:
            await ctx.followup.send("⚠️ ランク名を入力してください。")
            return

        text = rank_name.strip().lower().replace("　", "").replace(" ", "")
        text = re.sub(r"[０-９]", lambda m: chr(ord(m.group(0)) - 65248), text)

        matched_rank = None
        RANK_NORMALIZE = {
            r"^(iron|あいあん|アイアン)": "アイアン",
            r"^(bronze|ぶろんず|ブロンズ)": "ブロンズ",
            r"^(silver|しるばー|シルバー|しる)": "シルバー",
            r"^(gold|ごーるど|ゴールド|ごる)": "ゴールド",
            r"^(plat|platinum|ぷらち|プラチナ|ぷら)": "プラチナ",
            r"^(dia|diamond|だいや|ダイヤモンド|だいやもんど)": "ダイヤモンド",
            r"^(ase|ascendant|あせ|アセンダント)": "アセンダント",
            r"^(imm|immortal|いも|イモータル)": "イモータル",
            r"^(rad|radiant|れでぃ|レディアント)": "レディアント",
        }

        for pattern, base in RANK_NORMALIZE.items():
            if re.match(pattern, text):
                m = re.search(r"(\d+)", text)
                num = m.group(1) if m else ""
                matched_rank = f"{base}{num}"
                break

        if not matched_rank or matched_rank not in RANK_POINTS:
            await ctx.followup.send(f"⚠️ `{rank_name}` は認識できませんでした。例：`ゴールド2`, `diamond1`")
            return

        payload = {
            "action": "add",
            "username": username,
            "user_id": user_id,
            "avatar_url": avatar_url,
            "rank": matched_rank
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(GAS_WEBHOOK_URL, json=payload) as res:
                text = await res.text()
                if res.status == 200:
                    await ctx.followup.send(f"✅ {username} さんのランク **{matched_rank}** を登録しました！")
                else:
                    await ctx.followup.send(f"⚠️ 登録に失敗しました（{res.status}）")

    # ------------------------------------------------------------
    # 🧪 /peko teamtest（v1.2）
    # ------------------------------------------------------------
    @peko.command(name="teamtest", description="固定10人でチーム分けテスト＋スライド更新")
    async def teamtest(ctx):
        await ctx.defer()
        payload = {"action": "fetch_team_data", "user_ids": [str(pid) for pid in PLAYER_IDS]}

        async with aiohttp.ClientSession() as session:
            async with session.post(GAS_WEBHOOK_URL, json=payload) as resp:
                if resp.status != 200:
                    await ctx.followup.send(f"⚠️ スプレッドシート接続エラー ({resp.status})")
                    return
                data = await resp.json()

        # ---- データ整形（アイコンURLの存在チェック付き）----
        players = []
        for d in data:
            name = d.get("name", "不明")
            rank = d.get("rank", "不明")
            point = RANK_POINTS.get(rank, 0)
            icon_url = d.get("icon") or d.get("iconUrl") or ""
            if not icon_url:
                logging.warning(f"⚠️ {name} のアイコンURLが空です。")
            players.append((name, rank, point, icon_url))

        # ---- チーム分け ----
        teamA, teamB, diff, idx, total = generate_balanced_teams(players)
        powerA = sum(p[2] for p in teamA)
        powerB = sum(p[2] for p in teamB)

        emoji_dict = {e.name: e for e in ctx.guild.emojis}

        embed = discord.Embed(title="チーム分けテスト結果", color=main_color)
        embed.add_field(name="🟥 アタッカー", value="\n".join(
            [f"{get_rank_emoji(p[1], emoji_dict)} {p[0]}" for p in teamA]) + f"\nポイント：{powerA}", inline=True)
        embed.add_field(name="🟦 ディフェンダー", value="\n".join(
            [f"{get_rank_emoji(p[1], emoji_dict)} {p[0]}" for p in teamB]) + f"\nポイント：{powerB}", inline=True)
        embed.add_field(name="　", value=f"組み合わせ候補：{idx}/{total}", inline=False)
        await ctx.followup.send(embed=embed)

        # ---- Googleスライド更新処理 ----
        slide_payload = {
            "action": "update_slide",
            "teamA": [{"name": p[0], "iconUrl": p[3]} for p in teamA],
            "teamB": [{"name": p[0], "iconUrl": p[3]} for p in teamB]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(GAS_WEBHOOK_URL, json=slide_payload) as slide_resp:
                if slide_resp.status == 200:
                    await ctx.followup.send("🖼️ スライドを更新しました！")
                else:
                    await ctx.followup.send(f"⚠️ スライド更新に失敗しました（{slide_resp.status}）")

    # ------------------------------------------------------------
    # 🚀 起動時処理
    # ------------------------------------------------------------
    bot.add_application_command(peko)

    @bot.event
    async def on_ready():
        await bot.sync_commands()
        logging.info(f"✅ コマンド同期完了: {len(bot.application_commands)} 件")
        await bot.change_presence(activity=discord.Game(name="PekoriBot v1.2"))
        logging.info(f"✅ Logged in as {bot.user}")

    return bot
