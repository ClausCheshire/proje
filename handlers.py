# -*- coding: utf-8 -*-
from aiogram import Router, F, types
from aiogram.filters import Command
from gigachat_client import analyze_text

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Hello! I am a bot for analyzing responses from government agencies.\n"
        "Send me the text of a response or use /analysis to start."
    )

@router.message(Command("analysis"))
async def cmd_analysis(message: types.Message):
    await message.answer(
        "Please send the text of the government agency response that you want to analyze."
    )

@router.message(~Command())
async def handle_text(message: types.Message):
    if len(message.text) > 50:
        waiting_msg = await message.answer("Analyzing text with GigaChat...")
        try:
            result = await analyze_text(message.text)
            await waiting_msg.edit_text(f"Analysis result:\n\n{result}")
        except Exception as e:
            await waiting_msg.edit_text(f"Error occurred: {e}")
