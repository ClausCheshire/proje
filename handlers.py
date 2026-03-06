# -*- coding: utf-8 -*-
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from gigachat_client import analyze_text

router = Router()

# --- Машина состояний ---
class AnalysisState(StatesGroup):
    agency = State()      # Шаг 1: Орган
    location = State()    # Шаг 2: Регион/город
    text = State()        # Шаг 3: Текст обращения

# --- Команды ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Hello! I am a bot for analyzing responses from government agencies.\n"
        "Use /analysis to start a new analysis session."
    )

@router.message(Command("analysis"))
async def cmd_analysis(message: types.Message, state: FSMContext):
    # Сбрасываем предыдущее состояние
    await state.clear()
    await state.set_state(AnalysisState.agency)
    await message.answer(
        "📋 **Step 1/3**\n"
        "Please send the **name of the government agency** that sent the response.\n"
        "(e.g., 'FNS Russia', 'Ministry of Internal Affairs', etc.)"
    )

# --- Шаг 1: Получаем орган ---
@router.message(AnalysisState.agency)
async def process_agency(message: types.Message, state: FSMContext):
    await state.update_data(agency=message.text)
    await state.set_state(AnalysisState.location)
    await message.answer(
        "📍 **Step 2/3**\n"
        "Please send the **region and city**.\n"
        "(e.g., 'Moscow', 'Saint Petersburg', 'Krasnodar Krai')"
    )

# --- Шаг 2: Получаем регион ---
@router.message(AnalysisState.location)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(AnalysisState.text)
    await message.answer(
        "📄 **Step 3/3**\n"
        "Please send the **full text of the government agency's response** that you want to analyze."
    )

# --- Шаг 3: Получаем текст и запускаем анализ ---
@router.message(AnalysisState.text)
async def process_text(message: types.Message, state: FSMContext):
    logger.info(f"STATE_TEXT: Starting analysis for user_id={message.from_user.id}")
    
    await message.answer(f"✅ Received {len(message.text)} characters. Starting analysis...")
    waiting_msg = await message.answer("⏳ Analyzing with GigaChat...")
    logger.info("Sent 'Analyzing...' message")
    
    data = await state.get_data()
    agency = data.get("agency", "Unknown")
    location = data.get("location", "Unknown")
    text = message.text
    
    try:
        logger.info("Calling analyze_text()...")
        result = await analyze_text(text, agency, location)
        logger.info(f"analyze_text() returned, result length: {len(result)}")
        
        # Если результат начинается с ❌ или ⏰ — это ошибка, покажем её
        if result.startswith("❌") or result.startswith("⏰"):
            await waiting_msg.edit_text(result)
        else:
            final_text = (
                f"🏛️ **Agency:** {agency}\n"
                f"📍 **Location:** {location}\n\n"
                f"🤖 **Analysis Result:**\n\n{result}"
            )
            await waiting_msg.edit_text(final_text)
        logger.info("Final result sent to user")
        
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {e}", exc_info=True)
        await waiting_msg.edit_text(f"❌ Unexpected error: {e}")
    finally:
        await state.clear()
        logger.info("State cleared")



