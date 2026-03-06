# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from gigachat_client import analyze_text

logger = logging.getLogger(__name__)
router = Router()

class AnalysisState(StatesGroup):
    agency = State()
    location = State()
    text = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    logger.info(f"CMD_START: user_id={message.from_user.id}")
    await message.answer(
        "Hello! I am a bot for analyzing responses from government agencies.\n"
        "Use /analysis to start a new analysis session."
    )

@router.message(Command("analysis"))
async def cmd_analysis(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AnalysisState.agency)
    logger.info(f"CMD_ANALYSIS: State set to AGENCY for user_id={message.from_user.id}")
    await message.answer("📋 **Step 1/3**: Send the **name of the government agency**.")

@router.message(AnalysisState.agency, F.text)
async def process_agency(message: types.Message, state: FSMContext):
    await state.update_data(agency=message.text)
    await state.set_state(AnalysisState.location)
    logger.info(f"STATE_AGENCY: Received '{message.text}'. Switching to LOCATION.")
    await message.answer("📍 **Step 2/3**: Send the **region and city**.")

@router.message(AnalysisState.location, F.text)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(AnalysisState.text)
    logger.info(f"STATE_LOCATION: Received '{message.text}'. Switching to TEXT.")
    await message.answer("📄 **Step 3/3**: Send the **full text of the response**.")

@router.message(AnalysisState.text, F.text)
async def process_text(message: types.Message, state: FSMContext):
    logger.info(f"STATE_TEXT: Received {len(message.text)} chars. Starting analysis...")
    
    await message.answer(f"✅ Received {len(message.text)} characters. Starting analysis...")
    waiting_msg = await message.answer("⏳ Analyzing with GigaChat...")
    
    data = await state.get_data()
    agency = data.get("agency", "Unknown")
    location = data.get("location", "Unknown")
    text = message.text
    
    try:
        result = await analyze_text(text, agency, location)
        final_text = (
            f"🏛️ **Agency:** {agency}\n"
            f"📍 **Location:** {location}\n\n"
            f"🤖 **Analysis Result:**\n\n{result}"
        )
        await waiting_msg.edit_text(final_text)
        logger.info("Result sent successfully.")
    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
        await waiting_msg.edit_text(f"❌ Error: {e}")
    finally:
        await state.clear()
        logger.info("State cleared.")

# --- ОТЛАДОЧНЫЙ ОБРАБОТАТЕЛЬ (ЛОВУШКА) ---
# Сработает, если сообщение не подошло ни под один фильтр выше
@router.message(F.text)
async def catch_all_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logger.warning(f"CATCH_ALL: User sent text but no handler matched! Current State: {current_state}")
    logger.warning(f"Message content: {message.text[:50]}...")
    await message.answer(
        f"⚠️ I received your message, but I'm not sure what to do with it.\n"
        f"Current state: {current_state}\n"
        f"Try /start to reset."
    )
