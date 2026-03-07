# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio
import re
import time
import base64
import uuid

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Таймауты
AUTH_TIMEOUT = aiohttp.ClientTimeout(total=30)
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=90)

# Кэш токена (живёт 30 минут)
_token_cache = {
    "token": None,
    "expires_at": 0
}

# В начало файла добавьте импорт:


# ... затем обновите функцию get_gigachat_token:

async def get_gigachat_token():
    """Получение токена через OAuth (Client ID + Client Secret)"""
    current_time = time.time()
    
    # Проверяем кэш — если токен ещё валиден, возвращаем его
    if _token_cache["token"] and current_time < _token_cache["expires_at"]:
        print(f"✅ [AUTH] Using cached token (expires in {_token_cache['expires_at'] - current_time:.0f}s)")
        return _token_cache["token"]
    
    print("🔑 [AUTH] Requesting new token from SberCloud...")
    
    # Генерируем уникальный RqUID для этого запроса
    rq_uid = str(uuid.uuid4())
    print(f"🆔 [AUTH] RqUID: {rq_uid}")
    
    # Формируем Basic Auth
    credentials = f"{config.GIGACHAT_CLIENT_ID}:{config.GIGACHAT_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    # Добавляем RqUID в данные запроса + нужный scope
    data = {
        "scope": "GIGACHAT_API_PERS",
        "RqUID": rq_uid
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=AUTH_TIMEOUT) as session:
            async with session.post(AUTH_URL, data=data, headers=headers) as resp:
                response_text = await resp.text()
                print(f"📡 [AUTH] Status: {resp.status}")
                
                if resp.status == 200:
                    json_data = await resp.json()
                    access_token = json_data["access_token"]
                    expires_in = json_data.get("expires_in", 1800)  # 30 минут по умолчанию
                    
                    # Сохраняем в кэш (с запасом 5 минут)
                    _token_cache["token"] = access_token
                    _token_cache["expires_at"] = current_time + expires_in - 300
                    
                    print(f"✅ [AUTH] Token received, cached for {expires_in - 300}s")
                    return access_token
                else:
                    print(f"❌ [AUTH] Failed: {resp.status} - {response_text[:200]}")
                    raise Exception(f"GigaChat auth error: {resp.status} - {response_text[:200]}")
                    
    except asyncio.TimeoutError:
        print("⏰ [AUTH] Timeout")
        raise Exception("Превышено время ожидания при авторизации")
    except Exception as e:
        print(f"⚠️ [AUTH] Error: {type(e).__name__}: {e}")
        raise
    finally:
        await connector.close()

async def generate_question(subject: str) -> str:
    """Генерация вопроса для подготовки к олимпиадам по обществознанию"""
    start_time = time.time()
    print(f"🚀 [GEN] Starting question generation: subject={subject}")
    
    subject_clean = subject.strip()
    if not subject_clean or len(subject_clean) < 2:
        return "❌ Не удалось определить раздел"
    
    try:
        token = await get_gigachat_token()
    except Exception as e:
        return f"❌ Ошибка авторизации: {e}"
    
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
        "Authorization": f"Bearer {token}"
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
    
    try:
        token = await get_gigachat_token()
    except Exception as e:
        return f"❌ Ошибка авторизации: {e}"
    
    system_prompt = (
        "⚠️ КРИТИЧЕСКИ ВАЖНО: Ты выводишь оценку ТОЛЬКО в формате 'Оценка: X/5'.\n"
        "⛔ ЗАПРЕЩЕНО под любым предлогом:\n"
        "  • Писать '100', 'баллов из 100', '/100', 'сто баллов'\n"
        "  • Показывать промежуточные расчёты или внутреннюю шкалу\n"
        "  • Использовать квадратные скобки [...] или описывать, что 'должно быть'\n"
        "  • Писать что-либо кроме 'Оценка: 1/5', 'Оценка: 2/5' и т.д.\n"
        "Если нарушишь — ученик получит неверную информацию.\n"
        "\n"
        "Ты — строгий экзаменатор. Оценивай содержание, а не уверенность.\n"
        "🚫 ИГНОРИРУЙ: 'это правильно', 'очевидно' без доказательств.\n"
        "✅ ДАВАЙ БАЛЛЫ ТОЛЬКО ЗА: термины с определениями, ссылки на НПА, примеры.\n"
        "\n"
        "📊 ВНУТРЕННЯЯ ЛОГИКА (НЕ ВЫВОДИТЬ): 0-20→1/5, 21-40→2/5, 41-60→3/5, 61-80→4/5, 81-100→5/5\n"
        "\n"
        "📝 ФОРМАТ ОТВЕТА (ПИШИ КОНКРЕТНОЕ СОДЕРЖАНИЕ, НЕ ОПИСАНИЯ):\n"
        "1. 📊 Оценка: X/5  ← ЕДИНСТВЕННАЯ оценка в ответе!\n"
        "2. ✅ Что верно: [ПИШИ КОНКРЕТНЫЕ ПУНКТЫ, если есть что похвалить; если нет — ПРОПУСТИ раздел]\n"
        "3. ❌ Что не верно: [ПИШИ КОНКРЕТНЫЕ ОШИБКИ]\n"
        "4. 💡 Как улучшить: [ПИШИ КОНКРЕТНЫЕ РЕКОМЕНДАЦИИ]\n"
        "5. 🎯 Идеальный ответ: [НАПИШИ ПОЛНОСТЬЮ ПРИМЕР ОТВЕТА на 3-4 предложения]\n"
        "\n"
        "⛔ ПРАВИЛА НАПИСАНИЯ:\n"
        "• НИКОГДА не используй квадратные скобки [...] в финальном ответе\n"
        "• НИКОГДА не пиши 'должен', 'следует', 'нужно добавить' — пиши САМУ рекомендацию\n"
        "• Если нечего похвалить — просто НЕ ПИШИ раздел '✅ Что верно'\n"
        "\n"
        "⛔ ФИНАЛЬНАЯ ПРОВЕРКА: В ответе НЕТ упоминаний '100' и квадратных скобок."
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
        "Authorization": f"Bearer {token}"
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
                    patterns_to_remove = [
                        r'Оценка:\s*\d+/100',
                        r'\d+\s*баллов?\s*из\s*100',
                        r'\d+/100\b',
                        r'\(\s*\d+/100\s*\)',
                        r'сто\s*баллов?',
                        r'100-балльной?',
                        r'шкала.*?100',
                    ]
                    for pattern in patterns_to_remove:
                        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
                    
                    result = re.sub(r'\(\s*\d+/100\s*\)', '', result)
                    result = re.sub(r'\[\s*\d+/100\s*\]', '', result)
                    
                    def keep_only_5point(match):
                        score_100 = int(match.group(1))
                        if score_100 <= 20: return "Оценка: 1/5"
                        elif score_100 <= 40: return "Оценка: 2/5"
                        elif score_100 <= 60: return "Оценка: 3/5"
                        elif score_100 <= 80: return "Оценка: 4/5"
                        else: return "Оценка: 5/5"
                    result = re.sub(r'Оценка:\s*(\d+)/100', keep_only_5point, result)
                    
                    if "✅ Что верно:" in result:
                        start = result.find("✅ Что верно:")
                        end = result.find("❌ Что не верно:")
                        if end == -1:
                            end = result.find("💡 Как улучшить:")
                        if end != -1 and start != -1:
                            section = result[start:end].strip()
                            if any(p in section.lower() for p in ['нет верных', 'ничего не верно', 'верных пунктов']):
                                result = result[:start] + result[end:]
                    
                    if re.search(r'оценка.*?100|100.*?балл', result, re.IGNORECASE):
                        result = re.sub(r'\b100\b', '', result)
                    
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


