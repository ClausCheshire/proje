# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")
if not GIGACHAT_API_KEY:
    raise ValueError("GIGACHAT_API_KEY не найден в .env")
