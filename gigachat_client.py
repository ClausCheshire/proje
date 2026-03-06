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
    """Оценка ответа ученика от 1 до 5 баллов"""
    start_time = time.time()
    print(f"🚀 [EVAL] Starting evaluation: subject={subject}, answer_len={len(user_answer)}")
    
    system_prompt = (
        "⚠️ ВНИМАНИЕ: Ты проверяешь работы для олимпиады. Завышение оценок вредит ученику.\n"
        "Ты — строгий экзаменатор. Оценивай содержание, а не уверенность.\n"
        "\n"
        "🚫 ИГНОРИРУЙ: 'это правильно', 'очевидно', 'моя аргументация логична' без доказательств.\n"
        "✅ ДАВАЙ БАЛЛЫ ТОЛЬКО ЗА: термины с определениями, ссылки на НПА, конкретные примеры.\n"
        "\n"
        "📊 ШКАЛА (внутренняя, не выводить): 0-20→1/5, 21-40→2/5, 41-60→3/5, 61-80→4/5, 81-100→5/5\n"
        "\n"
        "📝 ФОРМАТ ОТВЕТА:\n"
        "1. 📊 Оценка: X/5\n"
        "2. ✅ Что верно: [ТОЛЬКО если есть конкретные верные пункты, иначе ПРОПУСТИ]\n"
        "3. ❌ Что не верно: [ошибки или отсутствие доказательств]\n"
        "4. 💡 Как улучшить: [что добавить]\n"
        "5. 🎯 Идеальный ответ: [3-4 предложения]\n"
        "\n"
        "⛔ ЗАПРЕЩЕНО: выводить 100-балльную шкалу, писать 'нет верных пунктов'."
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Раздел: {subject}\nВопрос:\n{question}\n\nОтвет:\n{user_answer[:2500]}"}
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
                    
                    # Пост-обработка: убираем 100-балльную шкалу
                    result = re.sub(r'Оценка:\s*\d+/100', '', result)
                    result = re.sub(r'/100\b', '/5', result)
                    
                    # Убираем пустой раздел "Что верно"
                    if "✅ Что верно:" in result:
                        start = result.find("✅ Что верно:")
                        end = result.find("❌ Что не верно:")
                        if end == -1:
                            end = result.find("💡 Как улучшить:")
                        if end != -1:
                            section = result[start:end].strip()
                            if any(p in section.lower() for p in ['нет верных', 'ничего не верно']):
                                result = result[:start] + result[end:]
                    
                    print(f"✅ [EVAL] Success! Result length: {len(result)}")
                    return result
                else:
                    return f"❌ Ошибка оценки: {resp.status}"
                    
    except asyncio.TimeoutError:
        return "⏰ Оценка заняла слишком много времени. Попробуй с ответом покороче."
    except Exception as e:
        return f"❌ Ошибка: {type(e).__name__}: {str(e)}"
    finally:
        await connector.close()
