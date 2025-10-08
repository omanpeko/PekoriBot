# -*- coding: utf-8 -*-
import aiohttp
import logging
from typing import List, Dict

# ---- Google Apps Script（GAS）のエンドポイント ----
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwCRqFmTZTSLVBnIUEasJviLwjvhe1WD3XE9yC7PF3JGa28E20iqf3ivb_DRHA0leivQQ/exec"


async def generate_team_image(players: List[Dict[str, str]]) -> str:
    """
    Googleスライド(GAS)を使ってチーム画像を生成し、PNGのURLを返す。

    Parameters
    ----------
    players : list of dict
        例: [{"name": "おまんぺこ", "iconUrl": "https://...jpg"}, ...]

    Returns
    -------
    str
        PNG画像のURL（失敗時は None）
    """
    payload = {"players": players}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GAS_WEBHOOK_URL, json=payload) as resp:
                if resp.status != 200:
                    logging.warning(f"GAS 接続失敗 ({resp.status})")
                    return None

                data = await resp.json()
                if data.get("status") == "ok":
                    logging.info("✅ スライド画像生成成功")
                    return data.get("url")
                else:
                    logging.error(f"⚠️ GASエラー: {data}")
                    return None
    except Exception as e:
        logging.error(f"❌ GAS送信エラー: {e}")
        return None
