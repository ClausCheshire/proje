@router.callback_query(F.data.startswith("subject_"))
async def process_subject(callback: types.CallbackQuery, state: FSMContext):
    subject_map = {
        "subject_law": "Право",
        "subject_economy": "Экономика", 
        "subject_culture": "Культура"
    }
    subject = subject_map.get(callback.data, "Неизвестно")
    await state.update_data(subject=subject)
    
    logger.info(f"SUBJECT_SELECTED: {subject}")
    
    # Отправляем сообщение с таймаут-индикацией
    waiting_msg = await callback.message.answer("⏳ Генерирую вопрос... (это займёт до 90 секунд)")
    
    try:
        # Добавляем общий таймаут на всю операцию
        question = await asyncio.wait_for(
            generate_question(subject),
            timeout=100  # 100 секунд максимум
        )
        
        # Проверка на ошибку в результате
        if question.startswith("❌") or question.startswith("⏰") or question.startswith("🔌"):
            await waiting_msg.edit_text(
                f"{question}\n\n"
                "💡 Советы:\n"
                "• Попробуй другой раздел\n"
                "• Проверь, работает ли интернет\n"
                "• Напиши /study чтобы начать заново"
            )
            await state.clear()
            await callback.answer()
            return
        
        await state.update_data(question=question)
        await state.set_state(StudyState.waiting_answer)
        
        await waiting_msg.edit_text(
            f"📋 **Твой вопрос:**\n\n{question}\n\n"
            "✍️ Напиши развёрнутый ответ с аргументацией.\n"
            "⏰ У тебя есть время, не торопись!"
        )
        logger.info("✅ Question sent to user")
        
    except asyncio.TimeoutError:
        logger.error("⏰ Overall timeout in process_subject")
        await waiting_msg.edit_text(
            "⏰ Сервис не ответил вовремя.\n\n"
            "💡 Попробуй ещё раз или выбери другой раздел."
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        await waiting_msg.edit_text(f"❌ Ошибка: {e}\n\nПопробуй ещё раз.")
        await state.clear()
    
    await callback.answer()
