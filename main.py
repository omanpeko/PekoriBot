# main.py
# =============================================
# PekoriBot v1.2 - Main Entrypoint
# =============================================
import os
import logging
from valorant_bot import create_bot   # ← ここが正しい！

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")

    # Botインスタンス生成（valorant_bot.py 内の create_bot()）
    bot = create_bot()

    # トークン取得（Railway環境変数）
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です。")

    logging.info("🚀 Starting PekoriBot v1.2 ...")
    bot.run(token)
