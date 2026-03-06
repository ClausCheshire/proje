# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from gigachat_client import generate_question, evaluate_answer

logger = logging.getLogger(__name__)
router = Router()

class StudyState(StatesGroup):
    subject = State()      # Выбор раздела
    exam_name = State()    # Название олимпиады/экзамена
    waiting_answer = State()  # Ожидание ответа пользователя

# Главная клавиатура с разделами
def get_subject_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Право", callback_data="subject_law")],
        [InlineKeyboardButton(text="💰 Экономика", callback_data="subject_economy")],
        [InlineKeyboardButton(text="🎭 Культура", callback_data="subject_culture")],
    ])
    return keyboard

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    logger.info(f"CMD_START: user_id={message.from_user.id}")
    await message.answer(
        "👋 Привет! Я бот для подготовки к олимпиадам и экзаменам по обществознанию.\n\n"
        "Я помогу тебе:\n"
        "• Практиковаться в заданиях с развёрнутым ответом\n"
        "• Получать оценку от 1 до 5\n"
        "• Анализировать ошибки и улучшать ответы\n\n"
        "Нажми /study чтобы начать тренировку!"
    )

@router.message(Command("study"))
async def cmd_study(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(StudyState.subject)
    logger.info(f"CMD_STUDY: user_id={message.from_user.id}")
    await message.answer(
        "📚 **Выбери раздел обществознания:**",
        reply_markup=get_subject_keyboard()
    )

@router.callback_query(F.data.startswith("subject_"))
async def process_subject(callback: types.CallbackQuery, state: FSMContext):
    subject_map = {
        "subject_law": "Право",
        "subject_economy": "Экономика",
        "subject_culture": "Культура"
    }
    subject = subject_map.get(callback.data, "Неизвестно")
    await state.update_data(subject=subject)
    await state.set_state(StudyState.exam_name)
    logger.info(f"SUBJECT_SELECTED: {subject}")
    await callback.message.answer(
        f"✅ Выбран раздел: **{subject}**\n\n"
        "📝 Теперь напиши название олимпиады или экзамена,\n"
        "к которому ты готовишься.\n\n"
        "_(например: Всероссийская олимпиада, ЕГЭ, МГУ олимпиада)_ "
    )
    await callback.answer()

@router.message(StudyState.exam_name, F.text)
async def process_exam_name(message: types.Message, state: FSMContext):
    exam_name = message.text
    await state.update_data(exam_name=exam_name)
    
    data = await state.get_data()
    subject = data.get("subject", "Неизвестно")
    
    logger.info(f"EXAM_NAME: {exam_name}, SUBJECT: {subject}")
    
    waiting_msg = await message.answer("⏳ Генерирую вопрос...")
    
    try:
        question = await generate_question(subject, exam_name)
        await state.update_data(question=question)
        await state.set_state(StudyState.waiting_answer)
        
        await waiting_msg.edit_text(
            f"📋 **Твой вопрос:**\n\n{question}\n\n"
            "✍️ Напиши развёрнутый ответ с аргументацией.\n"
            "Оценивай ситуацию с точки зрения выбранного раздела.\n\n"
            "⏰ Не торопись, качество важнее скорости!"
        )
        logger.info("Question generated and sent")
        
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        await waiting_msg.edit_text(f"❌ Ошибка при генерации вопроса: {e}")

@router.message(StudyState.waiting_answer, F.text)
async def process_answer(message: types.Message, state: FSMContext):
    user_answer = message.text
    logger.info(f"ANSWER_RECEIVED: {len(user_answer)} chars from user_id={message.from_user.id}")
    
    await message.answer(f"✅ Получено {len(user_answer)} символов. Оцениваю ответ...")
    waiting_msg = await message.answer("⏳ Анализирую твой ответ...")
    
    data = await state.get_data()
    subject = data.get("subject", "Неизвестно")
    exam_name = data.get("exam_name", "Неизвестно")
    question = data.get("question", "")
    
    try:
        evaluation = await evaluate_answer(question, user_answer, subject, exam_name)
        
        final_text = (
            f"📊 **Результаты оценки**\n\n"
            f"{evaluation}\n\n"
            "💡 Хочешь ещё один вопрос? Нажми /study"
        )
        
        await waiting_msg.edit_text(final_text)
        logger.info("Evaluation sent to user")
        
    except Exception as e:
        logger.error(f"Error evaluating answer: {e}")
        await waiting_msg.edit_text(f"❌ Ошибка при оценке: {e}")
    finally:
        await state.clear()
        logger.info("State cleared")

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    logger.info(f"CMD_CANCEL: user_id={message.from_user.id}")
    await message.answer("❌ Тренировка отменена. Используй /study, чтобы начать заново.")

