import os
import random
import asyncio
import urllib.parse
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables (API Key)
load_dotenv()

class AIService:
    """
    Service layer for interacting with Google Gemini AI.
    Handles prompt engineering and API communication.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found in environment variables.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    async def suggest_goal(self, user_hint: str = None) -> str:
        """
        Generates a professional, inspiring goal title.
        """
        if not self.client:
            return "Project Hercules: Become Fit (AI Unavailable)"

        # Heuristic: If the input looks like an AI-generated title (starts with known prefixes),
        # assume the user wants a completely NEW idea (Re-roll), not a refinement of the previous one.
        if user_hint and any(user_hint.strip().startswith(prefix) for prefix in ["Vision:", "Strategic Objective:", "Roadmap:", "Milestone:"]):
            user_hint = None

        if not user_hint:
            # We explicitly pick a concrete topic
            concrete_goals = [
                "Run a Marathon", "Learn French", "Save $10,000", "Write a Novel",
                "Learn Python", "Visit Japan", "Get Promoted", "Deadlift 100kg",
                "Learn Guitar", "Quit Sugar", "Read 24 Books", "Start a Business",
                "Renovate the House", "Learn to Surf", "Cook Every Day", "Meditate Daily"
            ]
            selected_goal = random.choice(concrete_goals)

            # Ensure we don't pick the same random goal if we can avoid it.
            # (In a real app, we'd store history, but here simply relying on random is usually enough given the list size.
            # The logic above ensures we actually ENTER this block on re-clicks).

            prompt = (
                f"Formulate a concise, punchy, and professional Vision Title for this goal: '{selected_goal}'. \n"
                "The title should be inspiring but direct. Avoid excessive corporate buzzwords. \n"
                "Format: 'Vision: [Short, Powerful Phrase]' or 'Strategic Objective: [Clear Outcome]'. \n"
                "Keep it under 10 words. \n"
                "Examples: 'Vision: Financial Independence', 'Vision: Fluent in French', 'Strategy: Marathon Ready'. \n"
                "Provide ONLY the title."
            )
        else:
            prompt = (
                f"Rephrase this goal into a short, punchy, and professional Vision Title. "
                "Avoid lengthy sentences. Focus on the core value. "
                "Format: 'Vision: ...' "
                f"Goal: '{user_hint}'. Provide ONLY the title, no quotes."
            )

        try:
            # Run the synchronous API call in a separate thread to avoid blocking the server
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model='gemini-2.5-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=1.0, # Max randomness
                    max_output_tokens=50
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"AI Error Details: {e}")
            return f"Error: {str(e)}"

    async def generate_subquests(self, main_quest: str) -> list:
        """
        Breaks down a main quest into actionable sub-quests using AI.
        Returns a list of dicts: [{'title': str, 'deadline': str, 'category': str}]
        """
        if not self.client:
            return []

        prompt = (
            f"Break down this Main Quest into 5 actionable sub-goals (quests): '{main_quest}'. \n"
            "Format each line exactly as: [Title] | [Estimated Duration] | [Category] \n"
            "Example: \n"
            "Research Running Shoes | 1 week | Preparation \n"
            "Run 5km without stopping | 1 month | Training \n"
            "Join a local running club | 2 weeks | Social \n"
            "Avoid introductory text. Provide ONLY the list."
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model='gemini-2.5-flash-lite',
                contents=prompt,
                 config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=300
                )
            )

            raw_text = response.text.strip()
            subquests = []

            for line in raw_text.split('\n'):
                parts = line.split('|')
                if len(parts) >= 3:
                    subquests.append({
                        "title": parts[0].strip(),
                        "deadline": parts[1].strip(), # We'll treat this as text for now
                        "category": parts[2].strip()
                    })
            return subquests

        except Exception as e:
            print(f"AI Subquest Error: {e}")
            return []

    async def generate_motivation(self, main_quest: str) -> str:
        """
        Generates a short, punchy motivational quote related to the main quest.
        """
        if not self.client:
            return "Keep moving forward. Your vision awaits."

        prompt = (
            f"Generate a single, short, profound motivational quote specifically for someone whose goal is: '{main_quest}'. \n"
            "Do not be cheesy. Be stoic, inspiring, or visionary. \n"
            "Maximum 15 words. \n"
            "Format: Just the quote text."
        )

        try:
             response = await asyncio.to_thread(
                self.client.models.generate_content,
                model='gemini-2.5-flash-lite',
                contents=prompt,
                 config=types.GenerateContentConfig(
                    temperature=1.0,
                    max_output_tokens=30
                )
            )
             return response.text.strip().replace('"', '')
        except Exception:
            return "The journey of a thousand miles begins with a single step."

    def get_vision_image(self, main_quest: str) -> str:
        """
        Returns a URL for a generated image based on the quest title.
        Uses pollinations.ai (free, no key) to generate distinct visuals.
        """
        # Clean the prompt for URL
        prompt = f"cyberpunk futuristic vision board style art for goal: {main_quest}, cinematic lighting, high quality, 8k"
        encoded_prompt = urllib.parse.quote(prompt)
        return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=400&nologo=true"

# Singleton instance
ai_service = AIService()
