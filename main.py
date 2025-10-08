# main.py
import os
import logging
from valorant_bot import setup_bot  # ← 本体を外部から読み込み

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    bot = setup_bot()
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        raise RuntimeError("環境変数 DISCORD_TOKEN が未設定です。")
    bot.run(token)
