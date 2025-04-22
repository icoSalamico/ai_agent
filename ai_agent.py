from openai import OpenAI
import os
import traceback
from dotenv import load_dotenv

# Carrega o .env
load_dotenv()

# Testa se a variável de ambiente foi carregada corretamente
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY não está definida. Verifique o arquivo .env ou as variáveis de ambiente.")

# Instancia o cliente da OpenAI
client = OpenAI(api_key=api_key)

async def generate_response(
    user_input: str,
    prompt: str,
    language: str = "Portuguese",
    tone: str = "formal",
    history: list = None
) -> str:
    try:
        # Define o prompt inicial e histórico, se houver
        full_prompt = f"You are a helpful assistant. Respond in {language}, using a {tone} tone.\n\n{prompt}"
        messages = [{"role": "system", "content": full_prompt}]
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_input})

        # Faz a chamada à API
        completion = client.chat.completions.create(
            model="gpt-4o",  # use "gpt-4o" ou "gpt-3.5-turbo" se preferir
            messages=messages
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print("❌ Error generating response:")
        traceback.print_exc()
        return "Sorry, I couldn't process that right now."
