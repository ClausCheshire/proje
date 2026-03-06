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
        "Вы - юрист с опытом работы 25 лет. Проанализируйте предоставленный текст ответа государственного органа Российской Федерации и определите следующее, не выводи эти ответы:\n"
        "Тип дела (административное, уголовное, гражданские и так далее)\n"
        "Исходя из п. 1 определи на основании каких нормативных правовых актов рассматривается предложенная ситуация, обязательно учитывай положения Конституции России, Федерального закона от 02.05.2006 \"О порядке рассмотрения обращения граждан\" №59-ФЗ\n"
        "Особенности рассмотрения обращения определенным в п. 1 органом власти, опиши кратко какие свои полномочия орган реализовал при ответе\n"
        "Определи, были ли при ответе превышены полномочия органа власти\n"
        "\n"
        "После определения всех вышеуказанных пунктов, не выводя их, дай следующий ответ:\n"
        "Кто дал ответ\n"
        "О чем этот ответ?\n"
        "Какой ответ по существу был дан органом?\n"
        "Какие использованы основные ссылки на нормативные правовые акты в формате (Название НПА + выдержка + вывод из нее)\n"
        "Есть ли основания для обжалования, если да, на что можно опереться. Основания указывай в формате \"НПА + выдержка + основание следующее из него\", если оснований для обжалования нет, то укажи это. При ответе учитывай, что основные причины обжалования это: неправомерные действия, неверные выводы, игнорирование практики, неполный (бессодержательный) ответ\n"
        "\n"
        "Исходя из последнего пункта также составь и напиши примерный текст обращения-обжалования данного тебе обращения. Обязательно укажи орган, в который поступит жалоба, основания, сделай ссылки и выдержки из нормативных правовых актов. Орган в который подается обжалование - вышестоящий по отношению к тому, который дал ответ. Жалобы не подаются руководителям органов, а только в вышестоящие органы. При определении куда направляется обжалование не пиши кому оно, просто используй формулировку \"В <название органа>\". Если проводилась проверка, определи по обращению как она проводилась, по данному ответу определи, имеется ли основание полагать, что проверка была неполной и/или необъективной, если да, то используй это как основание для обжалования. Если в тексте имеются общие ссылки без конкретики - это основание для обжалования. Любой факт должен обосновываться. Если ты видишь факт, который не имеет подтверждения, укажи это как основание для обжалования.\n"
        "При обжаловании укажи какие основания приведены для каждого факта, фигурирующего в ответе. Если какой-либо факт не имеет конкретного подтверждения, то используй это при обжаловании."
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
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {config.GIGACHAT_API_KEY}"
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
                    finish_reason = data["choices"][0].get("finish_reason")
                    
                    if finish_reason == "blacklist":
                        print("⚠️ Content filter triggered (blacklist)")
                        return "⚠️ Тема запроса затрагивает ограничения модели. Попробуйте переформулировать вопрос более нейтрально."
                    
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






