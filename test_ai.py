import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key present: {bool(api_key)}")

if api_key:
    try:
        client = genai.Client(api_key=api_key)
        print("Attempting to generate content with gemini-2.5-flash-lite...")
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents='Hello, are you there?'
        )
        print("Response received!")
        print(f"Text: {response.text}")
    except Exception as e:
        print(f"Error occurred: {e}")
else:
    print("No API Key found.")
