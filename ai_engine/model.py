import os
import asyncio
from openai import AsyncOpenAI
from .prompts import SYSTEM_PROMPT

class AIEngine:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("AI_API_KEY"),
            base_url="https://api-inference.huggingface.co/v1/"
        )
        self.model_name = "microsoft/Phi-3-mini-4k-instruct"

    async def _ask_ai(self, prompt: str) -> str:
        for attempt in range(3):  # 3 трая боту
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if "loading" in str(e).lower():
                    await asyncio.sleep(10) # вейт 10 сек
                    continue
                return f"ИИ немного устал, но передает: Все будет хорошо! ❤️"
        return "Модель просыпается, попробуй через минуту."