# -*- coding: utf-8 -*-
import aiohttp
import config
import asyncio

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=120)

async def analyze_text(text: str, agency: str = "Unknown", location: str = "Unknown") -> str:
    print("=" * 50)
    print("🚀 [GIGACHAT] Starting analyze_text()")
    print(f"   Agency: {agency}")
    print(f"   Location: {location}")
    print(f"   Text length: {len(text)}")
    print("=" * 50)
    
    system_prompt = (
    "Ты — помощник для работы с текстами. "
    "Пользователь пришёл документ. Пожалуйста: "
    "1. Кратко перескажи основное содержание документа. "
    "2. Отметь важные даты, сроки, номера документов. "
    "3. Если в тексте есть неясные формулировки — укажи на них. "
    "4. Отвечай нейтрально, без оценок и рекомендаций. "
    "5. Не давай юридических консультаций."
    )

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Орган: {agency}\nРегион: {location}\n\nТекст:\n{text[:3000]}"}
        ],
        "profanity_check": True
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {config.GIGACHAT_API_KEY}'
    }

    print(f"🔑 API Key first 10 chars: {config.GIGACHAT_API_KEY[:10]}...")
    print(f"📤 Sending POST to {CHAT_URL}")
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=CHAT_TIMEOUT) as session:
            print("⏳ Waiting for GigaChat response...")
            async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
                response_text = await resp.text()
                print(f"📡 Response Status: {resp.status}")
                print(f"📄 Response Body (first 500 chars): {response_text[:500]}")
                
                if resp.status == 200:
                    data = await resp.json()
                    result = data["choices"][0]["message"]["content"]
                    print(f"✅ SUCCESS! Result length: {len(result)}")
                    return result
                else:
                    print(f"❌ API Error: {resp.status}")
                    return f"❌ Ошибка GigaChat API: {resp.status}. Ответ: {response_text[:500]}"
                    
    except asyncio.TimeoutError:
        print("⏰ TIMEOUT: Request took too long")
        return "⏰ Запрос превысил время ожидания. Попробуйте с более коротким текстом."
    except Exception as e:
        print(f"⚠️ EXCEPTION: {type(e).__name__}: {str(e)}")
        return f"❌ Ошибка: {type(e).__name__}: {str(e)}"
    finally:
        await connector.close()
        print("🔌 Connector closed")
        print("=" * 50)

