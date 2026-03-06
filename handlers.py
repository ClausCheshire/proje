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
    waiting_msg = await message.answer("⏳ Analyzing text with GigaChat...")
    
    # Получаем все данные из состояния
    data = await state.get_data()
    agency = data.get("agency", "Unknown")
    location = data.get("location", "Unknown")
    text = message.text
    
    try:
        # Передаем все данные в функцию анализа
        result = await analyze_text(text, agency, location)
        await waiting_msg.edit_text(
            f"🏛️ **Agency:** {agency}\n"
            f"📍 **Location:** {location}\n\n"
            f"🤖 **Analysis Result:**\n\n{result}"
        )
    except Exception as e:
        await waiting_msg.edit_text(f"❌ Error occurred: {e}")
    finally:
        # Очищаем состояние после завершения
        await state.clear()

# --- Команда отмены ---
@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Analysis session cancelled. Use /analysis to start again.")

