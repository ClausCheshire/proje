# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio
import re
import time

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Таймауты (секунды)
AUTH_TIMEOUT = aiohttp.ClientTimeout(total=30)
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=90)  # Уменьшено с 120 для быстрого фидбека

async def generate_question(subject: str) -> str:
    """Генерация вопроса для подготовки к олимпиадам по обществознанию"""
    start_time = time.time()
    print(f"🚀 [GEN] Starting question generation: subject={subject}")
    
    subject_clean = subject.strip()
    if not subject_clean or len(subject_clean) < 2:
        return "❌ Не удалось определить раздел"
    
    system_prompt = (
        "Ты — опытный преподаватель обществознания. Создай вопрос с развёрнутым ответом.\n"
        f"Раздел: {subject}. Требуй анализа ситуации, аргументации, опоры на теорию. Не давай ответ."
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Создай вопрос по разделу '{subject}' для подготовки к экзамену."}
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
        print(f"📤 [GEN] Sending request to GigaChat API...")
        async with aiohttp.ClientSession(connector=connector, timeout=CHAT_TIMEOUT) as session:
            async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
                elapsed = time.time() - start_time
                response_text = await resp.text()
                print(f"📡 [GEN] Response in {elapsed:.1f}s: Status={resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    finish_reason = data["choices"][0].get("finish_reason")
                    
                    if finish_reason == "blacklist":
                        return "⚠️ Вопрос не сгенерирован из-за ограничений контента. Попробуй другой раздел."
                    
                    result = data["choices"][0]["message"]["content"].strip()
                    print(f"✅ [GEN] Success! Result length: {len(result)}")
                    return result
                else:
                    print(f"❌ [GEN] API Error {resp.status}: {response_text[:200]}")
                    return f"❌ Ошибка сервиса: {resp.status}. Попробуй ещё раз."
                    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"⏰ [GEN] TIMEOUT after {elapsed:.1f}s")
        return "⏰ Запрос занял слишком много времени. Попробуй ещё раз или выбери другой раздел."
        
    except aiohttp.ClientConnectionError as e:
        print(f"🔌 [GEN] Connection error: {e}")
        return "🔌 Ошибка соединения с сервисом. Проверь интернет или попробуй позже."
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"⚠️ [GEN] Unexpected error after {elapsed:.1f}s: {type(e).__name__}: {e}")
        return f"❌ Неожиданная ошибка: {type(e).__name__}. Попробуй ещё раз."
        
    finally:
        await connector.close()
        print("🔌 [GEN] Connector closed")

async def evaluate_answer(question: str, user_answer: str, subject: str) -> str:
    """Оценка ответа ученика от 1 до 5 баллов (ТОЛЬКО 5-балльная шкала)"""
    start_time = time.time()
    print(f"🚀 [EVAL] Starting evaluation: subject={subject}, answer_len={len(user_answer)}")
    
    system_prompt = (
        "⚠️ КРИТИЧЕСКИ ВАЖНО: Ты выводишь оценку ТОЛЬКО в формате 'Оценка: X/5'.\n"
        "⛔ ЗАПРЕЩЕНО под любым предлогом:\n"
        "  • Писать '100', 'баллов из 100', '/100', 'сто баллов'\n"
        "  • Показывать промежуточные расчёты или внутреннюю шкалу\n"
        "  • Писать что-либо кроме 'Оценка: 1/5', 'Оценка: 2/5' и т.д.\n"
        "Если нарушишь — ученик получит неверную информацию.\n"
        "\n"
        "Ты — строгий экзаменатор. Оценивай содержание, а не уверенность.\n"
        "🚫 ИГНОРИРУЙ: 'это правильно', 'очевидно' без доказательств.\n"
        "✅ ДАВАЙ БАЛЛЫ ТОЛЬКО ЗА: термины с определениями, ссылки на НПА, примеры.\n"
        "\n"
        "📊 ВНУТРЕННЯЯ ЛОГИКА (НЕ ВЫВОДИТЬ): 0-20→1/5, 21-40→2/5, 41-60→3/5, 61-80→4/5, 81-100→5/5\n"
        "\n"
        "📝 ФОРМАТ ОТВЕТА (СТРОГО):\n"
        "1. 📊 Оценка: X/5  ← ЕДИНСТВЕННАЯ оценка в ответе!\n"
        "2. ✅ Что верно: [ТОЛЬКО если есть конкретные верные пункты, иначе ПРОПУСТИ РАЗДЕЛ]\n"
        "3. ❌ Что не верно: [ошибки или отсутствие доказательств]\n"
        "4. 💡 Как улучшить: [что добавить: термин, ссылку, пример]\n"
        "5. 🎯 Идеальный ответ: тот ответ, который ты хотел увидеть\n"
        "\n"
        "⛔ ФИНАЛЬНАЯ ПРОВЕРКА: Перед отправкой убедись, что в ответе НЕТ ни одного упоминания '100'."
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Раздел: {subject}\nВопрос:\n{question}\n\nОтвет ученика:\n{user_answer[:2500]}"}
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
        print(f"📤 [EVAL] Sending evaluation request...")
        async with aiohttp.ClientSession(connector=connector, timeout=CHAT_TIMEOUT) as session:
            async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
                elapsed = time.time() - start_time
                response_text = await resp.text()
                print(f"📡 [EVAL] Response in {elapsed:.1f}s: Status={resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    finish_reason = data["choices"][0].get("finish_reason")
                    
                    if finish_reason == "blacklist":
                        return "⚠️ Не удалось оценить ответ из-за ограничений контента."
                    
                    result = data["choices"][0]["message"]["content"].strip()
                    
                    # === АГРЕССИВНАЯ ПОСТ-ОБРАБОТКА ===
                    
                    # 1. Удаляем ВСЕ упоминания 100-балльной шкалы в любом формате
                    patterns_to_remove = [
                        r'Оценка:\s*\d+/100',           # "Оценка: 85/100"
                        r'\d+\s*баллов?\s*из\s*100',    # "85 баллов из 100"
                        r'\d+/100\b',                    # "85/100"
                        r'\(\s*\d+/100\s*\)',           # "(85/100)"
                        r'сто\s*баллов?',                # "сто баллов"
                        r'100-балльной?',                # "100-балльная"
                        r'шкала.*?100',                  # "шкала до 100"
                    ]
                    for pattern in patterns_to_remove:
                        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
                    
                    # 2. Удаляем двойные оценки типа "4/5 (85/100)" → оставляем только "4/5"
                    result = re.sub(r'\(\s*\d+/100\s*\)', '', result)
                    result = re.sub(r'\[\s*\d+/100\s*\]', '', result)
                    
                    # 3. Если осталась "Оценка: 85/100 (4/5)" → оставляем только "Оценка: 4/5"
                    def keep_only_5point(match):
                        score_100 = int(match.group(1))
                        if score_100 <= 20: return "Оценка: 1/5"
                        elif score_100 <= 40: return "Оценка: 2/5"
                        elif score_100 <= 60: return "Оценка: 3/5"
                        elif score_100 <= 80: return "Оценка: 4/5"
                        else: return "Оценка: 5/5"
                    result = re.sub(r'Оценка:\s*(\d+)/100', keep_only_5point, result)
                    
                    # 4. Удаляем пустой раздел "Что верно"
                    if "✅ Что верно:" in result:
                        start = result.find("✅ Что верно:")
                        end = result.find("❌ Что не верно:")
                        if end == -1:
                            end = result.find("💡 Как улучшить:")
                        if end != -1 and start != -1:
                            section = result[start:end].strip()
                            if any(p in section.lower() for p in ['нет верных', 'ничего не верно', 'верных пунктов']):
                                result = result[:start] + result[end:]
                    
                    # 5. Финальная валидация: если всё ещё есть "100" рядом с "балл" или "оценка" — чистим
                    if re.search(r'оценка.*?100|100.*?балл', result, re.IGNORECASE):
                        result = re.sub(r'\b100\b', '', result)  # Удаляем изолированные "100"
                    
                    # 6. Убираем лишние пустые строки
                    result = re.sub(r'\n{3,}', '\n\n', result).strip()
                    
                    print(f"✅ [EVAL] Success! Cleaned result length: {len(result)}")
                    return result
                    
                else:
                    return f"❌ Ошибка оценки: {resp.status}"
                    
    except asyncio.TimeoutError:
        return "⏰ Оценка заняла слишком много времени. Попробуй с ответом покороче."
    except Exception as e:
        return f"❌ Ошибка: {type(e).__name__}: {str(e)}"
    finally:
        await connector.close()


