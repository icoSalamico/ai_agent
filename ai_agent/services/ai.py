import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Optional, Dict

# Carrega variáveis de ambiente
load_dotenv()

# Configura logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("❌ OPENAI_API_KEY não está definida. Verifique o arquivo .env.")
    return OpenAI(api_key=api_key)

def build_messages(
    user_input: str,
    prompt: str,
    language: str,
    tone: str,
    history: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, str]]:
    messages = [{
        "role": "system",
        "content": f"You are a helpful assistant. Respond in {language}, using a {tone.lower()} tone.\n\n{prompt}"
    }]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    return messages


async def generate_response(
    user_input: str,
    prompt: str,
    language: str = "Portuguese",
    tone: str = "formal",
    history: Optional[List[Dict[str, str]]] = None
) -> str:
    try:
        # Segurança defensiva: impede passar objetos não-string
        if not isinstance(prompt, str) or not isinstance(language, str) or not isinstance(tone, str):
            raise TypeError("❌ Parâmetros inválidos: prompt, language e tone devem ser strings.")

        history = history or []
        client = get_openai_client()
        messages = build_messages(user_input, prompt, language, tone, history)

        logger.debug("🧠 Enviando mensagens para OpenAI:")
        logger.debug(messages)

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        logger.exception("❌ Erro ao gerar resposta da IA:")
        return "Desculpe, não consegui processar sua mensagem no momento."
