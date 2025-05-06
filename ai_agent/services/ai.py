from openai import OpenAI
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("❌ OPENAI_API_KEY não está definida. Verifique o arquivo .env.")
    return OpenAI(api_key=api_key)

def build_messages(user_input, prompt, language, tone, history=None):
    base = [{
        "role": "system",
        "content": f"You are a helpful assistant. Respond in {language}, using a {tone.lower()} tone.\n\n{prompt}"
    }]
    if history:
        base.extend(history)
    base.append({"role": "user", "content": user_input})
    return base

async def generate_response(
    user_input: str,
    prompt: str,
    language: str = "Portuguese",
    tone: str = "formal",
    history: list = None
) -> str:
    try:
        history = history or []
        client = get_openai_client()
        messages = build_messages(user_input, prompt, language, tone, history)

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return completion.choices[0].message.content.strip()

    except Exception:
        logger.exception("❌ Error generating response:")
        return "Desculpe, não consegui processar sua mensagem no momento."
