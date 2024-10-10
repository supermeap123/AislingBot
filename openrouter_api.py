import aiohttp
import asyncio
from config import OPENROUTER_API_KEY, logger  # Import logger

API_URL = 'https://openrouter.ai/api/v1/chat/completions'

async def get_openrouter_response(messages, model='anthropic/claude-3.5-sonnet', temperature=0.7):
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                response_text = await response.text()
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content']
                else:
                    logger.error(f"OpenRouter API Error {response.status}: {response_text}")
                    return None
        except Exception as e:
            logger.exception(f"Exception occurred while calling OpenRouter API: {e}")
            return None
