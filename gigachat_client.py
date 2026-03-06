# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Таймаут для запроса к GigaChat (секунды)
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=120)

async def analyze_text(text: str, agency: str = "Unknown", location: str = "Unknown") -> str:
    """
    Отправка запроса к GigaChat API с использованием API Key (без OAuth)
    """
    print(f"🚀 Starting GigaChat analysis for agency={agency}, location={location}")
    
    system_prompt = (
        "Ты — юридический ассистент, специализирующийся на российском административном праве. "
        "Проанализируй ответ государственного органа. "
        "1. Кратко выдели суть ответа (главные тезисы). "
        "2. Найди возможные основания для обжалования (нарушения сроков, отписки, "
        "отсутствие ответов на вопросы, ссылки на недействующие нормы). "
        "3. Если нарушений нет, напиши об этом. "
        "4. Ответ должен быть структурированным, без воды. "
        "5. ВАЖНО: Добавь дисклеймер, что это не является официальной юридической консультацией."
    )

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Орган: {agency}\nРегион: {location}\n\nТекст ответа:\n{text[:3000]}"}
        ],
        "profanity_check": True
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {config.GIGACHAT_API_KEY}'
    }

    connector = aiohttp.TCPConnector(ssl=False)  # Для Railway
    
    try:
        print("📤 Sending request to GigaChat API...")
        async with aiohttp.ClientSession(connector=connector, timeout=CHAT_TIMEOUT) as session:
            async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
                response_text = await resp.text()
                print(f"📡 GigaChat Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    result = data["choices"][0]["message"]["content"]
                    print(f"✅ Received result, length: {len(result)}")
                    return result
                else:
                    print(f"❌ GigaChat API error: {resp.status} - {response_text[:300]}")
                    return f"❌ Ошибка GigaChat API: {resp.status}. Ответ: {response_text[:300]}"
                    
    except asyncio.TimeoutError:
        print("⏰ GigaChat request timed out")
        return "⏰ Запрос превысил время ожидания. Попробуйте с более коротким текстом."
    except Exception as e:
        print(f"⚠️ GigaChat request error: {type(e).__name__}: {e}")
        return f"❌ Ошибка при анализе: {type(e).__name__}: {e}"
    finally:
        await connector.close()
        print("🔌 Connector closed")


