# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio
import re

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=120)

async def generate_question(subject: str) -> str:
    """Генерация вопроса для подготовки к олимпиадам по обществознанию"""
    print(f"🚀 Generating question: subject={subject}")
    
    # Проверка на валидность раздела
    subject_clean = subject.strip()
    if not subject_clean or len(subject_clean) < 2:
        return "❌ Не удалось определить раздел"
    
    system_prompt = (
        "Ты — опытный преподаватель обществознания, готовишь школьников к олимпиадам и экзаменам.\n"
        "Твоя задача — создать качественный вопрос с развёрнутым ответом.\n"
        "\n"
        "Требования к вопросу:\n"
        "1. Должен требовать анализа ситуации, а не простого воспроизведения фактов\n"
        "2. Должен содержать конкретную ситуацию или кейс для оценки\n"
        "3. Должен требовать аргументации с опорой на теорию\n"
        "4. Используй средний-высокий уровень сложности (универсальный для подготовки)\n"
        f"5. Фокусируйся строго на разделе: {subject}\n"
        "\n"
        "⛔ НЕ спрашивай уточнений. Просто сгенерируй вопрос."
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Создай вопрос по разделу '{subject}'. Вопрос должен требовать развёрнутого ответа с аргументацией и оценкой ситуации. Не давай ответ, только вопрос."}
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
                        return "⚠️ Не удалось сгенерировать вопрос. Попробуй другой раздел."
                    
                    result = data["choices"][0]["message"]["content"].strip()
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

async def evaluate_answer(question: str, user_answer: str, subject: str) -> str:
    """Оценка ответа ученика от 1 до 5 баллов"""
    print(f"🚀 Evaluating answer: subject={subject}")
    
    system_prompt = (
        "⚠️ ВНИМАНИЕ: Ты проверяешь реальные работы для олимпиады. Завышение оценок вредит ученику. "
        "За каждую пустую фразу без доказательств снимай баллы. "
        "Если весь ответ состоит из 'это правильно' — ставь 1/5 без колебаний.\n"
        "\n"
        "Ты — строгий экзаменатор по обществознанию. Оценивай ответ УЧЕНИКА, а не его уверенность.\n"
        "\n"
        "🚫 ИГНОРИРУЙ СЛЕДУЮЩИЕ ФРАЗЫ (они не дают баллов):\n"
        "• 'Этот ответ правильный / верный / точный'\n"
        "• 'Моя аргументация логична / убедительна'\n"
        "• 'Я использую правильные термины'\n"
        "• 'Это очевидно / ясно / понятно'\n"
        "• 'Как известно / общепризнано'\n"
        "• Любые утверждения без ссылок на конкретные нормы, факты, примеры\n"
        "\n"
        "✅ ДАВАТЬ БАЛЛЫ ТОЛЬКО ЕСЛИ:\n"
        "• Термин назван + дано его определение + применён к ситуации\n"
        "• Аргумент подкреплён ссылкой на НПА, статистику, исторический факт\n"
        "• Пример конкретен: назван закон, статья, суд, дата, имена\n"
        "\n"
        "⚠️ АВТОМАТИЧЕСКИ СНИЖАЙ ОЦЕНКУ ДО 1/5, ЕСЛИ:\n"
        "• Ответ содержит только общие фразы без доказательств\n"
        "• Присутствуют фактические ошибки в терминах или нормах\n"
        "• Пользователь просто повторяет вопрос или утверждает 'это правильно'\n"
        "\n"
        "📊 ВНУТРЕННЯЯ ШКАЛА (для себя, НЕ ВЫВОДИТЬ):\n"
        "• 0-20 баллов → Итог: 1/5 | Бред, не по теме, пустые утверждения\n"
        "• 21-40 баллов → Итог: 2/5 | Есть мысли, но нет аргументов и примеров\n"
        "• 41-60 баллов → Итог: 3/5 | Ответ по теме, но поверхностный\n"
        "• 61-80 баллов → Итог: 4/5 | Хороший ответ: структура, аргументы, минимум ошибок\n"
        "• 81-100 баллов → Итог: 5/5 | Отлично: глубина, ссылки, примеры, логика\n"
        "\n"
        "🔄 ПОРЯДОК РАБОТЫ (следуй точно):\n"
        "1. Выпиши из ответа ученика КОНКРЕТНЫЕ утверждения (без 'это правильно')\n"
        "2. Для каждого утверждения проверь: есть ли ссылка на НПА/факт/термин?\n"
        "3. Посчитай баллы по 100-балльной шкале (для себя)\n"
        "4. Переведи в 5-балльную: 0-20=1, 21-40=2, 41-60=3, 61-80=4, 81-100=5\n"
        "5. ⛔ НИКОГДА не пиши оценку в 100-балльной шкале в ответе пользователю!\n"
        "6. Сформируй финальный ответ с оценкой 1-5 и комментарием\n"
        "\n"
        "📝 ФОРМАТ ОТВЕТА (СТРОГО СОБЛЮДАТЬ):\n"
        "1. 📊 Оценка: X/5 (где X — число от 1 до 5)\n"
        "2. ✅ Что верно: [выводи этот раздел ТОЛЬКО если есть минимум 1 конкретный верный пункт с доказательством; если нет — ПРОПУСТИ раздел полностью]\n"
        "3. ❌ Что не верно: [конкретные ошибки или отсутствие доказательств]\n"
        "4. 💡 Как улучшить: [что добавить: термин, ссылку, пример]\n"
        "5. 🎯 Идеальный ответ: [3-4 предложения с примером]\n"
        "\n"
        "⛔ ЗАПРЕЩЕНО:\n"
        "• Писать 'Что верно: нет верных пунктов' — вместо этого просто НЕ ВЫВОДИ этот раздел\n"
        "• Писать оценку в формате '80/100', '100 баллов' или аналогичном\n"
        "• Упоминать 100-балльную шкалу в финальном ответе\n"
        "• Показывать промежуточные расчёты баллов\n"
        "\n"
        "Будь жёстким. Пустые утверждения = 1/5."
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Раздел: {subject}\n\nВопрос:\n{question}\n\nОтвет ученика:\n{user_answer}\n\nОцени ответ по критериям выше."}
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
                    
                    result = data["choices"][0]["message"]["content"].strip()
                    
                    # === Пост-обработка: убираем 100-балльную шкалу и пустой раздел "Что верно" ===
                    
                    # Удаляем упоминания 100-балльной шкалы
                    result = re.sub(r'Оценка:\s*\d+/100', '', result)
                    result = re.sub(r'\d+\s*баллов?\s*из\s*100', '', result)
                    result = re.sub(r'/100\b', '/5', result)
                    
                    # Удаляем пустой раздел "Что верно", если модель его вывела
                    if "✅ Что верно:" in result:
                        start = result.find("✅ Что верно:")
                        end = result.find("❌ Что не верно:")
                        if end == -1:
                            end = result.find("💡 Как улучшить:")
                        if end != -1 and start != -1:
                            section = result[start:end].strip()
                            if any(phrase in section.lower() for phrase in ['нет верных', 'ничего не верно', '-']):
                                result = result[:start] + result[end:]
                    
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
