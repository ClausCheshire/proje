# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio
import re
import time

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Таймаут для запросов
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=90)

async def generate_question(subject: str) -> str:
    """Генерация вопроса с ПРЯМОЙ передачей Access Token"""
    start_time = time.time()
    print(f"\n{'=' * 70}")
    print(f"🚀 [GEN] Starting question generation: subject={subject}")
    print(f"{'=' * 70}")
    
    subject_clean = subject.strip()
    if not subject_clean or len(subject_clean) < 2:
        return "❌ Не удалось определить раздел"
    
    # === Access Token из config (без OAuth) ===
    access_token = config.GIGACHAT_ACCESS_TOKEN
    token_preview = f"{access_token[:20]}...{access_token[-10:]}"
    print(f"🔑 [GEN] Using Access Token: {token_preview}")
    print(f"🔑 [GEN] Token length: {len(access_token)} chars")
    
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
    
    # === ЯВНАЯ ПЕРЕДАЧА ТОКЕНА В ЗАГОЛОВКЕ ===
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"  # ← Прямая передача
    }
    
    print(f"📤 [GEN] Sending request to GigaChat API...")
    print(f"📤 [GEN] URL: {CHAT_URL}")
    print(f"📤 [GEN] Authorization: Bearer {token_preview}")
    print(f"📤 [GEN] Model: GigaChat")
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    try:
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
                    print(f"{'=' * 70}")
                    return result
                    
                elif resp.status == 401:
                    print(f"❌ [GEN] 401 Unauthorized - Token expired or invalid!")
                    print(f"❌ [GEN] Get new token from SberCloud and update GIGACHAT_ACCESS_TOKEN")
                    return "❌ Ошибка авторизации (401). Access Token истёк или неверный. Обновите токен в SberCloud."
                    
                else:
                    print(f"❌ [GEN] API Error {resp.status}: {response_text[:200]}")
                    print(f"{'=' * 70}")
                    return f"❌ Ошибка сервиса: {resp.status}. Ответ: {response_text[:300]}"
                    
    except asyncio.TimeoutError:
        return "⏰ Запрос занял слишком много времени. Попробуй ещё раз."
    except Exception as e:
        return f"❌ Ошибка: {type(e).__name__}: {str(e)}"
    finally:
        await connector.close()

async def evaluate_answer(question: str, user_answer: str, subject: str) -> str:
    """Оценка ответа с ПРЯМОЙ передачей Access Token"""
    start_time = time.time()
    print(f"\n{'=' * 70}")
    print(f"🚀 [EVAL] Starting evaluation: subject={subject}, answer_len={len(user_answer)}")
    print(f"{'=' * 70}")
    
    # === Access Token из config (без OAuth) ===
    access_token = config.GIGACHAT_ACCESS_TOKEN
    token_preview = f"{access_token[:20]}...{access_token[-10:]}"
    print(f"🔑 [EVAL] Using Access Token: {token_preview}")
    print(f"🔑 [EVAL] Token length: {len(access_token)} chars")
    
    system_prompt = (
        "⚠️ КРИТИЧЕСКИ ВАЖНО: Ты выводишь оценку ТОЛЬКО в формате 'Оценка: X/5'.\n"
        "⛔ ЗАПРЕЩЕНО: писать '100', 'баллов из 100', '/100', использовать квадратные скобки [...].\n"
        "\n"
        "Ты — строгий экзаменатор. Оценивай содержание, а не уверенность.\n"
        "🚫 ИГНОРИРУЙ: 'это правильно', 'очевидно' без доказательств.\n"
        "✅ ДАВАЙ БАЛЛЫ ТОЛЬКО ЗА: термины с определениями, ссылки на НПА, примеры.\n"
        "\n"
        "📊 ВНУТРЕННЯЯ ЛОГИКА (НЕ ВЫВОДИТЬ): 0-20→1/5, 21-40→2/5, 41-60→3/5, 61-80→4/5, 81-100→5/5\n"
        "\n"
        "📝 ФОРМАТ ОТВЕТА:\n"
        "1. 📊 Оценка: X/5\n"
        "2. ✅ Что верно: [ПИШИ КОНКРЕТНЫЕ ПУНКТЫ, если есть; если нет — ПРОПУСТИ раздел]\n"
        "3. ❌ Что не верно: [ПИШИ КОНКРЕТНЫЕ ОШИБКИ]\n"
        "4. 💡 Как улучшить: [ПИШИ КОНКРЕТНЫЕ РЕКОМЕНДАЦИИ]\n"
        "5. 🎯 Идеальный ответ: [НАПИШИ ПРИМЕР ОТВЕТА на 3-4 предложения]\n"
        "\n"
        "⛔ ПРАВИЛА: Не используй скобки [...], не пиши 'должен/следует'. Если нечего похвалить — не пиши раздел."
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Раздел: {subject}\nВопрос:\n{question}\n\nОтвет ученика:\n{user_answer[:2500]}"}
        ],
        "profanity_check": True
    }
    
    # === ЯВНАЯ ПЕРЕДАЧА ТОКЕНА В ЗАГОЛОВКЕ ===
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"  # ← Прямая передача
    }
    
    print(f"📤 [EVAL] Sending evaluation request...")
    print(f"📤 [EVAL] URL: {CHAT_URL}")
    print(f"📤 [EVAL] Authorization: Bearer {token_preview}")
    print(f"📤 [EVAL] Model: GigaChat")
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    try:
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
                    patterns_to_remove = [
                        r'Оценка:\s*\d+/100',
                        r'\d+\s*баллов?\s*из\s*100',
                        r'\d+/100\b',
                        r'\(\s*\d+/100\s*\)',
                    ]
                    for pattern in patterns_to_remove:
                        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
                    
                    def keep_only_5point(match):
                        score_100 = int(match.group(1))
                        if score_100 <= 20: return "Оценка: 1/5"
                        elif score_100 <= 40: return "Оценка: 2/5"
                        elif score_100 <= 60: return "Оценка: 3/5"
                        elif score_100 <= 80: return "Оценка: 4/5"
                        else: return "Оценка: 5/5"
                    result = re.sub(r'Оценка:\s*(\d+)/100', keep_only_5point, result)
                    
                    # Удаляем пустой раздел "Что верно"
                    if "✅ Что верно:" in result:
                        start = result.find("✅ Что верно:")
                        end = result.find("❌ Что не верно:")
                        if end == -1:
                            end = result.find("💡 Как улучшить:")
                        if end != -1 and start != -1:
                            section = result[start:end].strip()
                            if any(p in section.lower() for p in ['нет верных', 'ничего не верно']):
                                result = result[:start] + result[end:]
                    
                    result = re.sub(r'\n{3,}', '\n\n', result).strip()
                    
                    print(f"✅ [EVAL] Success! Cleaned result length: {len(result)}")
                    print(f"{'=' * 70}")
                    return result
                    
                elif resp.status == 401:
                    print(f"❌ [EVAL] 401 Unauthorized - Token expired or invalid!")
                    print(f"❌ [EVAL] Get new token from SberCloud and update GIGACHAT_ACCESS_TOKEN")
                    return "❌ Ошибка авторизации (401). Access Token истёк или неверный. Обновите токен в SberCloud."
                    
                else:
                    print(f"❌ [EVAL] API Error {resp.status}: {response_text[:200]}")
                    print(f"{'=' * 70}")
                    return f"❌ Ошибка оценки: {resp.status}. Ответ: {response_text[:300]}"
                    
    except asyncio.TimeoutError:
        return "⏰ Оценка заняла слишком много времени."
    except Exception as e:
        return f"❌ Ошибка: {type(e).__name__}: {str(e)}"
    finally:
        await connector.close()
