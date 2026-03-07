# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")
if not GIGACHAT_CLIENT_ID:
    raise ValueError("GIGACHAT_CLIENT_ID not found in .env")
if not GIGACHAT_CLIENT_SECRET:
    raise ValueError("GIGACHAT_CLIENT_SECRET not found in .env")
