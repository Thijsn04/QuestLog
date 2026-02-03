# 🛡️ QuestLog

**QuestLog** is a gamified, AI-powered "Vision Board" that transforms your life goals into an epic RPG adventure. Break down ambitious dreams into actionable "Quests", earn XP for completing tasks, and level up your life.

![QuestLog Dashboard Concept](https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80)

## ✨ Features

*   **🤖 AI Architect**: Sticky stuck? Let the AI break down your Main Quest (e.g., "Run a Marathon") into actionable, scheduled sub-quests automatically.
*   **🎮 Gamified Progression**: Earn **XP** for every task completed. Level up your hero profile from *Novice* to *Visionary*.
*   **🔮 Visual Vision Board**: The dashboard header dynamically updates with stunning, AI-generated sci-fi/cyberpunk art reflecting your specific goal.
*   **🗣️ Motivation Engine**: Receive a unique, profound motivational quote generated daily, tailored specifically to your current Main Quest.
*   **🔓 Unlockable Themes**: Start with *Cyberpunk*. Unlock *Zen Garden* at Level 3 and *Minimalist* at Level 5.
*   **🔥 Overdue Logic**: Missed a deadline? The card lights up with visual warnings to keep you accountable.
*   **🔄 Drag & Drop**: Easily reorganize your day by dragging tasks around.
*   **💾 Data Safety**: Export your entire life's progress to JSON at any time.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/questlog.git
    cd questlog
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables**:
    *   Create a file named `.env` in the root directory.
    *   Add your Google Gemini API Key (Get one [here](https://aistudio.google.com/app/apikey)):
        ```env
        GEMINI_API_KEY=your_api_key_here
        ```

## 🚀 Usage

Start the local server:

```bash
uvicorn main:app --reload
```

Open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

## 🎮 How to Play

1.  **Onboarding**: Enter your "Main Quest" (e.g., *Become a Senior Developer*). The AI will generate a Vision Board background for you.
2.  **Build the Plan**: Click "✨ Architect Plan" to let AI generate your first 5 sub-quests, or add them manually.
3.  **Execute**: Complete tasks to gain XP. Check the dashboard daily for new quotes.
4.  **Level Up**: Reach higher levels to unlock new visual themes in the Settings menu.

## 🏗️ Built With

*   **Backend**: Python, FastAPI
*   **Frontend**: HTML, CSS, [HTMX](https://htmx.org/) (No complex JS frameworks!)
*   **Database**: SQLite, SQLAlchemy
*   **AI**: Google Gemini Pro
*   **Visuals**: Pollinations.ai (Image Generation), SortableJS

## 🤝 Contributing

Contributions are welcome! Pull requests are great, but for major changes, please open an issue first to discuss what you would like to change.
