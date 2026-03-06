# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=120)

async def generate_question(subject: str, exam_name: str) -> str:
    """Генерация вопроса для подготовки"""
    print(f"🚀 Generating question for subject={subject}, exam={exam_name}")
    
    system_prompt = (
        "Ты - опытный преподаватель обществознания, готовишь школьников к олимпиадам и экзаменам.\n"
        "Твоя задача - создать качественный вопрос с развёрнутым ответом.\n"
        "Требования к вопросу:\n"
        "1. Должен требовать анализа ситуации, а не простого воспроизведения фактов\n"
        "2. Должен содержать конкретную ситуацию или кейс для оценки\n"
        "3. Должен требовать аргументации с опорой на теорию\n"
        "4. Соответствуй уровню сложности указанной олимпиады/экзамена\n"
        "5. Фокусируйся на разделе: право, экономика или культура"
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Создай вопрос для подготовки к {exam_name} по разделу '{subject}'. Вопрос должен требовать развёрнутого ответа с аргументацией и оценкой ситуации. Не давай ответ, только вопрос."}
        ],
        "profanity_check": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {config.GIGACHAT_API_KEY}"
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=CHAT_TIMEOUT) as session:
            async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
                response_text = await resp.text()
                print(f"📡 Question Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    finish_reason = data["choices"][0].get("finish_reason")
                    
                    if finish_reason == "blacklist":
                        return "⚠️ Не удалось сгенерировать вопрос. Попробуй другой раздел или формулировку."
                    
                    result = data["choices"][0]["message"]["content"]
                    print(f"✅ Question generated, length: {len(result)}")
                    return result
                else:
                    return f"❌ Ошибка API: {resp.status}"
                    
    except asyncio.TimeoutError:
        return "⏰ Превышено время ожидания. Попробуй ещё раз."
    except Exception as e:
        return f"❌ Ошибка: {type(e).__name__}: {str(e)}"
    finally:
        await connector.close()

async def evaluate_answer(question: str, user_answer: str, subject: str, exam_name: str) -> str:
    """Оценка ответа пользователя от 0 до 100"""
    print(f"🚀 Evaluating answer for subject={subject}, exam={exam_name}")
    
    system_prompt = (
system_prompt = (
    "Ты - строгий экзаменатор по обществознанию с опытом проверки олимпиадных работ.\n"
    "Твоя задача - оценить ответ ученика от 0 до 100 баллов ОБЪЕКТИВНО.\n"
    "\n"
    "⚠️ ВАЖНО: Не завышай оценку из вежливости. Если ответ слабый - ставь низкий балл.\n"
    "\n"
    "Шкала оценок:\n"
    "• 0-20 баллов - Ответ не по теме, бессвязный, или откровенный бред\n"
    "• 21-40 баллов - Есть отдельные верные мысли, но нет структуры и аргументов\n"
    "• 41-60 баллов - Ответ по теме, но поверхностный, мало аргументов, есть ошибки\n"
    "• 61-80 баллов - Хороший ответ: раскрыта тема, есть аргументы, минимальные ошибки\n"
    "• 81-100 баллов - Отличный ответ: глубоко, аргументированно, с примерами и терминами\n"
    "\n"
    "Критерии (по 25 баллов каждый):\n"
    "1. Полнота - раскрыты ли все аспекты вопроса\n"
    "2. Теория - правильное использование терминов и понятий\n"
    "3. Аргументация - логичность и убедительность доводов\n"
    "4. Примеры - наличие конкретных примеров, норм, фактов\n"
    "\n"
    "🚩 Критические ошибки (автоматически снижают оценку до 0-30 баллов):\n"
    "• Ответ не по теме вопроса\n"
    "• Фактические ошибки в терминах или нормах\n"
    "• Отсутствие аргументов (только утверждения без доказательств)\n"
    "• Объём ответа менее 3 предложений\n"
    "\n"
    "Формат ответа:\n"
    "1. 📊 Оценка: X/100 баллов\n"
    "2. ✅ Сильные стороны (2-3 пункта)\n"
    "3. ⚠️ Ошибки и слабые места (2-3 пункта)\n"
    "4. 💡 Пример идеального ответа (3-4 предложения)\n"
    "5. 📚 Рекомендации (конкретные темы для изучения)\n"
    "\n"
    "Будь объективным. Если ответ слабый - пиши об этом прямо."
)
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Раздел: {subject}\nЭкзамен: {exam_name}\n\nВопрос:\n{question}\n\nОтвет ученика:\n{user_answer}\n\nОцени ответ по критериям выше."}
        ],
        "profanity_check": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {config.GIGACHAT_API_KEY}"
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=CHAT_TIMEOUT) as session:
            async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
                response_text = await resp.text()
                print(f"📡 Evaluation Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    finish_reason = data["choices"][0].get("finish_reason")
                    
                    if finish_reason == "blacklist":
                        return "⚠️ Не удалось оценить ответ. Попробуй переформулировать."
                    
                    result = data["choices"][0]["message"]["content"]
                    print(f"✅ Evaluation complete, length: {len(result)}")
                    return result
                else:
                    return f"❌ Ошибка API: {resp.status}. Ответ: {response_text[:200]}"
                    
    except asyncio.TimeoutError:
        return "⏰ Превышено время ожидания. Попробуй с ответом покороче."
    except Exception as e:
        return f"❌ Ошибка: {type(e).__name__}: {str(e)}"
    finally:
        await connector.close()










