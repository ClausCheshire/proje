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
        "👋 Привет! Я бот для анализа ответов государственных органов РФ.\n\n"
        "Используй /analysis, чтобы начать новый сеанс анализа.\n"
        "Используй /cancel, чтобы отменить текущий сеанс."
    )

@router.message(Command("analysis"))
async def cmd_analysis(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AnalysisState.agency)
    logger.info(f"CMD_ANALYSIS: State set to AGENCY for user_id={message.from_user.id}")
    await message.answer(
        "📋 **Шаг 1/3**\n\n"
        "Отправь **название государственного органа**, который прислал ответ.\n\n"
        "_(например: ФНС России, МВД, Пенсионный фонд)_ "
    )

@router.message(AnalysisState.agency, F.text)
async def process_agency(message: types.Message, state: FSMContext):
    await state.update_data(agency=message.text)
    await state.set_state(AnalysisState.location)
    logger.info(f"STATE_AGENCY: Received '{message.text}'")
    await message.answer(
        "📍 **Шаг 2/3**\n\n"
        "Отправь **регион и город**.\n\n"
        "_(например: Москва, Санкт-Петербург, Краснодарский край)_ "
    )

@router.message(AnalysisState.location, F.text)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(AnalysisState.text)
    logger.info(f"STATE_LOCATION: Received '{message.text}'")
    await message.answer(
        "📄 **Шаг 3/3**\n\n"
        "Отправь **полный текст ответа государственного органа** для анализа.\n\n"
        "⚠️ _Рекомендуется до 3000 символов для быстрого ответа_"
    )

@router.message(AnalysisState.text, F.text)
async def process_text(message: types.Message, state: FSMContext):
    logger.info(f"STATE_TEXT: Received {len(message.text)} chars from user_id={message.from_user.id}")
    
    await message.answer(f"✅ Получено {len(message.text)} символов. Начинаю анализ...")
    waiting_msg = await message.answer("⏳ Анализирую с помощью GigaChat...")
    logger.info("Sent 'Analyzing...' message")
    
    data = await state.get_data()
    agency = data.get("agency", "Не указано")
    location = data.get("location", "Не указано")
    text = message.text
    
    try:
        logger.info("Calling analyze_text()...")
        result = await analyze_text(text, agency, location)
        logger.info(f"analyze_text() returned, result length: {len(result)}")
        
        if result.startswith("❌") or result.startswith("⏰"):
            await waiting_msg.edit_text(result)
        else:
            final_text = (
                f"🏛️ **Орган:** {agency}\n"
                f"📍 **Регион:** {location}\n\n"
                f"🤖 **Результат анализа:**\n\n{result}"
            )
            await waiting_msg.edit_text(final_text)
        logger.info("Final result sent to user")
        
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {e}", exc_info=True)
        await waiting_msg.edit_text(f"❌ Неожиданная ошибка: {e}")
    finally:
        await state.clear()
        logger.info("State cleared")

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    logger.info(f"CMD_CANCEL: user_id={message.from_user.id}")
    await state.clear()
    await message.answer("❌ Сеанс анализа отменён. Используй /analysis, чтобы начать заново.")

# Ловушка для отладки — если сообщение не обработано
@router.message(F.text)
async def catch_all_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logger.warning(f"CATCH_ALL: Text not handled! Current State: {current_state}")




