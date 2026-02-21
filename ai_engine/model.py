import os
import asyncio
from openai import AsyncOpenAI
import httpx
import logging
from .prompts import SYSTEM_PROMPT, TASK_CAPSULE

class AIEngine:
    def __init__(self):
            # используем официальный эндпоинт совместимости
        self.client = AsyncOpenAI(
            api_key=os.getenv("AI_API_KEY"),
            base_url="https://router.huggingface.co/v1" 
        )
        # модели, которые точно поддерживают этот интерфейс
        self.models = [
            "Qwen/Qwen2.5-7B-Instruct",
            "meta-llama/Llama-3.2-3B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3"
        ]
        self.current_model_idx = 0

    async def get_capsule_intro(self, context_text: str):
        """Специальный метод для генерации вступления к пасхалке"""
        # вызываем уже существующий метод генерации
        return await self.generate(
            TASK_CAPSULE, 
            user_context=context_text
        )

    def ethical_filter(self, text: str) -> bool:
        forbidden = ["ты должен", "почему ты не", "я злюсь", "ты всегда", "разлюбил"]
        return not any(phrase in text.lower() for phrase in forbidden)

    async def generate(self, prompt_template: str, **kwargs) -> str:
        prompt = prompt_template.format(**kwargs)
        return await self._ask_ai(prompt)

    async def _ask_ai(self, prompt: str) -> str:
        for attempt in range(len(self.models)):
            model_id = self.models[self.current_model_idx]
            try:
                print(f"--- Попытка через OpenAI SDK: {model_id} ---")
                response = await self.client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content.strip()
                
                if self.ethical_filter(result):
                    return result
                return "Давай просто побудем в тишине? Я рядом."

            except Exception as e:
                err_msg = str(e)
                print(f"Ошибка модели {model_id}: {err_msg}")
                
                if "loading" in err_msg.lower():
                    print("Модель загружается, ждем 20 сек...")
                    await asyncio.sleep(20)
                    return await self._ask_ai(prompt) 

                # если модель не найдена или ошибка доступа — переключаемся
                self.current_model_idx = (self.current_model_idx + 1) % len(self.models)
                continue

        return "ИИ взял небольшую паузу, но я передаю: Всё будет замечательно! ❤️"