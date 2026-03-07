# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_ACCESS_TOKEN = os.getenv("GIGACHAT_ACCESS_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")
if not GIGACHAT_ACCESS_TOKEN:
    raise ValueError("GIGACHAT_ACCESS_TOKEN not found in .env")

print(f"✅ Config loaded: BOT_TOKEN={len(BOT_TOKEN)} chars, ACCESS_TOKEN={len(GIGACHAT_ACCESS_TOKEN)} chars")
