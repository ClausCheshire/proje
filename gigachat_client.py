# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio
import re
import time
import base64

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

async def get_gigachat_token():
    """Получение токена через OAuth (Client ID + Client Secret)"""
    current_time = time.time()
    
    # Проверяем кэш
    if _token_cache["token"] and current_time < _token_cache["expires_at"]:
        token_preview = f"{_token_cache['token'][:20]}...{_token_cache['token'][-10:]}"
        print(f"✅ [AUTH] Using CACHED token: {token_preview}")
        print(f"✅ [AUTH] Token expires in: {_token_cache['expires_at'] - current_time:.0f}s")
        return _token_cache["token"]
    
    print("=" * 70)
    print("🔑 [AUTH] Requesting NEW token from SberCloud...")
    print("=" * 70)
    print(f"🔑 [AUTH] Client ID: {config.GIGACHAT_CLIENT_ID[:10]}...")
    print(f"🔑 [AUTH] Client Secret length: {len(config.GIGACHAT_CLIENT_SECRET)}")
    print("=" * 70)
    
    # Пробуем scope по очереди
    scopes_to_try = ["GIGACHAT_API_PERS", "GIGACHAT_API"]
    
    for scope in scopes_to_try:
        print(f"\n🔑 [AUTH] Trying scope: {scope}")
        print("-" * 70)
        
        # Формируем Basic Auth
        credentials = f"{config.GIGACHAT_CLIENT_ID}:{config.GIGACHAT_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {"scope": scope}
        
        connector = aiohttp.TCPConnector(ssl=False)
        
        try:
            async with aiohttp.ClientSession(connector=connector, timeout=AUTH_TIMEOUT) as session:
                async with session.post(AUTH_URL, data=data, headers=headers) as resp:
                    response_text = await resp.text()
                    
                    print(f"📡 [AUTH] Response Status: {resp.status}")
                    print(f"📡 [AUTH] Response Body: {response_text[:500]}")
                    print("-" * 70)
                    
                    if resp.status == 200:
                        try:
                            json_data = await resp.json()
                            access_token = json_data["access_token"]
                            expires_in = json_data.get("expires_in", 1800)
                            
                            # Сохраняем в кэш
                            _token_cache["token"] = access_token
                            _token_cache["expires_at"] = current_time + expires_in - 300
                            
                            token_preview = f"{access_token[:20]}...{access_token[-10:]}"
                            print(f"✅ [AUTH] TOKEN RECEIVED: {token_preview}")
                            print(f"✅ [AUTH] Token length: {len(access_token)} chars")
                            print(f"✅ [AUTH] Token expires in: {expires_in - 300}s")
                            print(f"✅ [AUTH] Token will expire at: {time.strftime('%H:%M:%S', time.localtime(_token_cache['expires_at']))}")
                            print("=" * 70)
                            return access_token
                        except Exception as json_err:
                            print(f"❌ [AUTH] Failed to parse JSON: {json_err}")
                            raise Exception(f"Invalid JSON response: {json_err}")
                    else:
                        print(f"❌ [AUTH] Failed with scope '{scope}': HTTP {resp.status}")
                        
        except asyncio.TimeoutError:
            print(f"⏰ [AUTH] Timeout with scope '{scope}'")
        except Exception as e:
            print(f"⚠️ [AUTH] Error with scope '{scope}': {type(e).__name__}: {str(e)}")
        finally:
            await connector.close()
    
    # Если оба scope не сработали
    print("=" * 70)
    print("❌ [AUTH] GigaChat auth failed with all scopes")
    print("=" * 70)
    raise Exception(
        "GigaChat auth failed with all scopes. Check credentials in SberCloud.\n"
        "1. Make sure you're using OAuth Client (IAM → Applications)\n"
        "2. Check role 'gigachat.ai.user' is assigned\n"
        "3. Check for spaces/quotes in Railway Variables"
    )

async def generate_question(subject: str) -> str:
    """Генерация вопроса с ЯВНОЙ передачей токена"""
    start_time = time.time()
    print(f"\n{'=' * 70}")
    print(f"🚀 [GEN] Starting question generation: subject={subject}")
    print(f"{'=' * 70}")
    
    subject_clean = subject.strip()
    if not subject_clean or len(subject_clean) < 2:
        return "❌ Не удалось определить раздел"
    
    # === ЯВНОЕ ПОЛУЧЕНИЕ ТОКЕНА ===
    print("🔑 [GEN] Requesting access token...")
    try:
        access_token = await get_gigachat_token()
        token_preview = f"{access_token[:20]}...{access_token[-10:]}"
        print(f"✅ [GEN] Access token received: {token_preview}")
    except Exception as e:
        error_msg = f"❌ Ошибка авторизации: {e}"
        print(error_msg)
        return error_msg
    
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
        "Authorization": f"Bearer {access_token}"  # ← ЯВНАЯ ПЕРЕДАЧА
    }
    
    print(f"📤 [GEN] Sending request to GigaChat API...")
    print(f"📤 [GEN] URL: {CHAT_URL}")
    print(f"📤 [GEN] Authorization: Bearer {token_preview}")  # ← ЛОГИРУЕМ
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
    """Оценка ответа с ЯВНОЙ передачей токена"""
    start_time = time.time()
    print(f"\n{'=' * 70}")
    print(f"🚀 [EVAL] Starting evaluation: subject={subject}, answer_len={len(user_answer)}")
    print(f"{'=' * 70}")
    
    # === ЯВНОЕ ПОЛУЧЕНИЕ ТОКЕНА ===
    print("🔑 [EVAL] Requesting access token...")
    try:
        access_token = await get_gigachat_token()
        token_preview = f"{access_token[:20]}...{access_token[-10:]}"
        print(f"✅ [EVAL] Access token received: {token_preview}")
    except Exception as e:
        error_msg = f"❌ Ошибка авторизации: {e}"
        print(error_msg)
        return error_msg
    
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
        "Authorization": f"Bearer {access_token}"  # ← ЯВНАЯ ПЕРЕДАЧА
    }
    
    print(f"📤 [EVAL] Sending evaluation request...")
    print(f"📤 [EVAL] URL: {CHAT_URL}")
    print(f"📤 [EVAL] Authorization: Bearer {token_preview}")  # ← ЛОГИРУЕМ
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
                    
                    # Пост-обработка
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
