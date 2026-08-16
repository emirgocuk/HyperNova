import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMService:
    """
    Service to handle interactions with Large Language Models via OpenRouter.
    Uses the OpenAI SDK as OpenRouter is compatible with it.
    """
    
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-exp:free")
        self.site_url = os.getenv("OR_SITE_URL", "")
        self.app_name = os.getenv("OR_APP_NAME", "HyperNova Bot")
        
        if not api_key:
            print("WARNING: OPENROUTER_API_KEY not found in .env file. LLM features will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                }
            )

    def get_response(self, prompt: str, system_prompt: str = "You are a helpful trading assistant.") -> str:
        """
        Send a prompt to the LLM and get the text response.
        """
        if not self.client:
            return "Error: LLM Service not configured."

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def check_connection(self) -> bool:
        """
        Simple connection test (Hello World).
        """
        if not self.client: return False
        try:
            print(f"Testing connection to {self.model}...")
            response = self.get_response("Say 'HyperNova connected!'", "You are a bot.")
            print(f"LLM Response: {response}")
            return "HyperNova connected" in response or len(response) > 0
        except:
            return False

if __name__ == "__main__":
    # Test script
    llm = LLMService()
    if llm.client:
        llm.check_connection()
    else:
        print("Please configure .env first.")
