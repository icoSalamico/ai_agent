from openai import OpenAI
import os
import traceback

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from dotenv import load_dotenv

load_dotenv()

async def generate_response(user_input: str, prompt: str, language: str = "Portuguese", tone: str = "formal", history: list = None) -> str:
    try:
        full_prompt = f"You are a helpful assistant. Respond in {language}, using a {tone} tone.\n\n{prompt}"
        messages = [{"role": "system", "content": full_prompt}]
        if history:
            messages += history
        messages.append({"role": "user", "content": user_input})

        completion = client.chat.completions.create(model="gpt-4o-mini",
        messages=messages)
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Error generating response:")
        traceback.print_exc()  # mostra o erro completo
        return "Sorry, I couldn't process that right now."