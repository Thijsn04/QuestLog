from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import re
from fastapi.encoders import jsonable_encoder

# Project Imports
from database.database import init_db, get_db
from database import models
from services.ai import ai_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database on Startup
    init_db()
    yield
    # Clean up resources if needed

app = FastAPI(title="QuestLog", description="Gamified Goal Tracking App", lifespan=lifespan)

# Mount static files (CSS, JS, Images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Middleware to inject theme into request state for base.html
@app.middleware("http")
async def add_theme_context(request: Request, call_next):
    # This is a bit of a hack for simple SQLite access in middleware
    # Ideally use a dependency, but middleware runs before dependencies.
    # We'll just define a default here, and let the template render handle it mostly.
    # Actually, Jinja2 context processors are better for this.
    # BUT, let's just cheat and query DB within routes or attach to request.

    # We will attach a default state
    request.state.theme = "cyberpunk"

    # We can try to peek at DB if needed, but creating a session here is heavy per request.
    # Let's rely on the route handlers passing it to templates,
    # OR simpler: Use a dependency that updates request.state
    response = await call_next(request)
    return response

# Dependency to get settings and put in request state
async def get_settings_context(request: Request, db: Session = Depends(get_db)):
    settings = db.query(models.Settings).first()
    if settings:
        request.state.theme = settings.theme_name.lower()
        request.state.hero_name = settings.hero_name
    return settings

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db), settings: models.Settings = Depends(get_settings_context)):
    """
    First Run Experience or Dashboard.
    """
    if not settings:
        return templates.TemplateResponse("index.html", {"request": request})

    # Load Main Quest and Subquests
    main_quest = db.query(models.Quest).filter(models.Quest.category == "Main").first()

    # Visual Vision Board: Ensure Main Quest has an image
    if main_quest and not main_quest.image_url:
        main_quest.image_url = ai_service.get_vision_image(main_quest.title)
        db.commit()

    subquests = []
    if main_quest:
        subquests = db.query(models.Quest).filter(models.Quest.parent_id == main_quest.id).order_by(models.Quest.position).all()

        # Check Daily Quote logic
        today = datetime.utcnow().date()
        last_date = settings.last_quote_date.date() if settings.last_quote_date else None

        if last_date != today:
            # Generate new quote
            new_quote = await ai_service.generate_motivation(main_quest.title)
            settings.daily_quote = new_quote
            settings.last_quote_date = datetime.utcnow()
            db.commit()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "main_quest": main_quest,
        "subquests": subquests,
        "settings": settings, # Pass settings which contains daily_quote
        "daily_quote": settings.daily_quote, # redundancy for template
        "level": settings.level,
        "xp": settings.xp,
        "xp_percent": (settings.xp % 500) / 500 * 100
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db), settings: models.Settings = Depends(get_settings_context)):
    if not settings:
        return "<p>Please finish onboarding first.</p>"

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "theme": settings.theme_name.lower(),
        "hero_name": settings.hero_name,
        "level": settings.level, # Pass level for unlocks
        "xp": settings.xp
    })

@app.post("/api/quest/reorder", response_class=HTMLResponse)
async def reorder_quests(item: list[str] = Form(...), db: Session = Depends(get_db)):
    """
    Updates the position of quests based on the list of IDs received.
    SortableJS sends 'item' as a list of strings "quest-{id}".
    """
    for index, item_str in enumerate(item):
        try:
            # item_str is like "quest-5"
            quest_id = int(item_str.split("-")[1])
            quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
            if quest:
                quest.position = index
        except (IndexError, ValueError):
            continue

    db.commit()
    return "" # No content needed, just 200 OK

@app.post("/api/settings/update")
async def update_settings(request: Request, theme_name: str = Form(...), hero_name: str = Form(...), db: Session = Depends(get_db)):
    settings = db.query(models.Settings).first()
    if settings:
        settings.theme_name = theme_name
        settings.hero_name = hero_name
        db.commit()

    # HTMX swap none means no content replacement, but we might want to show a toast?
    # For now, just a success header 204
    from fastapi import Response
    return Response(status_code=204)

@app.post("/api/ai/suggest-goal", response_class=HTMLResponse)
async def ai_suggest_goal(goal: str = Form(None)):
    """
    Uses Google Gemini to generate a suggested goal title.
    Returns an input field swappable by HTMX.
    """
    # If the user has typed something, use it as a hint.
    # If completely empty, the service defaults to "random self-improvement".
    suggestion = await ai_service.suggest_goal(user_hint=goal)

    # Return the new input HTML to replace the old one
    # Note: We must preserve the 'id' and 'name' for the form to work on subsequent submit
    return f'<input type="text" id="goal" name="goal" value="{suggestion}" required>'

@app.post("/api/ai/architect", response_class=HTMLResponse)
async def ai_architect(db: Session = Depends(get_db)):
    """
    Generates subquests for the current main quest.
    """
    main_quest = db.query(models.Quest).filter(models.Quest.category == "Main").first()
    if not main_quest:
        return "<p>Error: No Main Quest found.</p>"

    # Call AI Service
    tasks = await ai_service.generate_subquests(main_quest.title)

    # Save to DB
    saved_quests = []
    for task in tasks:
        # Parse duration to date
        deadline_dt = None
        duration_str = task['deadline'].lower()
        days_to_add = 0

        try:
            # Simple regex parsing for "X weeks", "X months", "X days"
            num_match = re.search(r'\d+', duration_str)
            num = int(num_match.group()) if num_match else 1

            if 'month' in duration_str:
                days_to_add = num * 30
            elif 'week' in duration_str:
                days_to_add = num * 7
            elif 'day' in duration_str:
                days_to_add = num
            elif 'year' in duration_str:
                days_to_add = num * 365

            if days_to_add > 0:
                deadline_dt = datetime.now() + timedelta(days=days_to_add)
        except Exception:
            pass # Keep deadline as None if parsing fails

        q = models.Quest(
            title=task['title'],
            category=task['category'],
            parent_id=main_quest.id,
            description=f"Duration: {task['deadline']}", # Keep original text in description for reference
            deadline=deadline_dt
        )
        db.add(q)
        saved_quests.append(q)

    db.commit()

    # Return HTML for the cards
    html_output = ""
    for q in saved_quests:
        html_output += render_quest_card(q)

    return html_output

@app.post("/api/quest/{quest_id}/toggle", response_class=HTMLResponse)
async def toggle_quest(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    settings = db.query(models.Settings).first()

    if quest:
        previous_state = quest.is_completed
        quest.is_completed = not quest.is_completed

        # Gamification Logic
        xp_gain = 100 # Standard XP for subquest
        if quest.is_completed and not previous_state:
            # Gained XP
            settings.xp += xp_gain
        elif not quest.is_completed and previous_state:
            # Lost XP (unchecked)
            settings.xp = max(0, settings.xp - xp_gain)

        # Level Calculation (Simple: Level = 1 + XP // 500)
        new_level = 1 + (settings.xp // 500)
        settings.level = new_level

        db.commit()

    # Return Multiple OOB Swaps: Progress Ring AND XP Bar

    # 1. Recalculate progress for the main quest
    progress = 0
    if quest and quest.parent_id:
        parent = db.query(models.Quest).filter(models.Quest.id == quest.parent_id).first()
        total_subquests = db.query(models.Quest).filter(models.Quest.parent_id == parent.id).count()
        completed_subquests = db.query(models.Quest).filter(models.Quest.parent_id == parent.id, models.Quest.is_completed == True).count()
        progress = int((completed_subquests / total_subquests) * 100) if total_subquests > 0 else 0

    xp_percent = (settings.xp % 500) / 500 * 100

    toast_script = ""
    if quest.is_completed and not previous_state:
        # Check if leveled up logic (simplified check if xp crossed boundary recently)
        # We don't have 'previous xp' easily here without querying again or passing it.
        # For QOL, let's just toast 'XP Gained'
        toast_script = f"<script>showToast('Gained {xp_gain} XP!');</script>"

    return f"""
    <div id="progress-ring" class="progress-ring" hx-swap-oob="true">
        {progress}%
    </div>
    
    <div id="hero-stats" class="hero-stats" hx-swap-oob="true">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-weight: bold; font-size: 0.9rem;">LVL {settings.level}</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">{settings.xp} XP</span>
        </div>
        <div class="xp-bar-bg">
            <div class="xp-bar-fill" style="width: {xp_percent}%;"></div>
        </div>
    </div>
    {toast_script}
    """
@app.delete("/api/quest/{quest_id}", response_class=HTMLResponse)
async def delete_quest(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if quest:
        parent_id = quest.parent_id
        db.delete(quest)
        db.commit()

        # We should also trigger a progress update since total count changed
        # HTMX allows OOB swaps. We can return an empty string for the deleted element
        # AND a side-band update for the progress ring.

        if parent_id:
            parent = db.query(models.Quest).filter(models.Quest.id == parent_id).first()
            total_subquests = db.query(models.Quest).filter(models.Quest.parent_id == parent.id).count()
            completed_subquests = db.query(models.Quest).filter(models.Quest.parent_id == parent.id, models.Quest.is_completed == True).count()
            progress = int((completed_subquests / total_subquests) * 100) if total_subquests > 0 else 0

            return f"""
            <div id="progress-ring" class="progress-ring" hx-swap-oob="true">
                {progress}%
            </div>
            """
    return ""

@app.post("/api/quest/add", response_class=HTMLResponse)
async def add_quest(title: str = Form(...), category: str = Form("General"), db: Session = Depends(get_db)):
    # Find Main Quest (assuming single main quest for now as per design)
    main_quest = db.query(models.Quest).filter(models.Quest.category == "Main").first()
    if not main_quest:
        return ""

    # Calculate next position
    max_pos = db.query(models.Quest).filter(models.Quest.parent_id == main_quest.id).count()

    new_quest = models.Quest(
        title=title,
        category=category,
        parent_id=main_quest.id,
        description="Manual Entry",
        is_completed=False,
        position=max_pos
    )
    db.add(new_quest)
    db.commit()

    # Return the new card HTML
    return render_quest_card(new_quest)

@app.get("/api/quest/{quest_id}/edit", response_class=HTMLResponse)
async def edit_quest_form(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if not quest:
        return ""

    date_val = quest.deadline.strftime('%Y-%m-%d') if quest.deadline else ""

    return f"""
    <div class="card sub-quest-card" id="quest-{quest.id}" style="border-color: var(--primary-color);">
        <form hx-put="/api/quest/{quest.id}" hx-target="#quest-{quest.id}" hx-swap="outerHTML" style="width: 100%;">
            <div style="margin-bottom: 0.5rem;">
                <label style="font-size: 0.7rem;">Title</label>
                <input type="text" name="title" value="{quest.title}" required style="margin:0; padding: 0.5rem;">
            </div>
            <div style="margin-bottom: 0.5rem;">
                 <label style="font-size: 0.7rem;">Deadline</label>
                <input type="date" name="deadline" value="{date_val}" style="margin:0; padding: 0.5rem;">
            </div>
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button type="button" hx-get="/api/quest/{quest.id}/cancel" hx-target="#quest-{quest.id}" hx-swap="outerHTML" style="padding: 0.25rem 0.5rem; font-size: 0.8rem; background: transparent; border: 1px solid var(--text-muted); color: var(--text-muted);">Cancel</button>
                <button type="submit" style="padding: 0.25rem 0.5rem; font-size: 0.8rem;">Save</button>
            </div>
        </form>
    </div>
    """

@app.get("/api/quest/{quest_id}/cancel", response_class=HTMLResponse)
async def cancel_edit_quest(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    return render_quest_card(quest)

@app.put("/api/quest/{quest_id}", response_class=HTMLResponse)
async def update_quest(quest_id: int, title: str = Form(...), deadline: str = Form(None), db: Session = Depends(get_db)):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if quest:
        quest.title = title
        if deadline:
            try:
                quest.deadline = datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                pass
        else:
            quest.deadline = None
        db.commit()
    return render_quest_card(quest)

def render_quest_card(quest: models.Quest) -> str:
    """Helper to render a single quest card HTML to DRY up code."""
    date_display = quest.deadline.strftime('%b %d, %Y') if quest.deadline else (quest.description or 'No deadline')
    checked_attr = "checked" if quest.is_completed else ""
    completed_class = "completed" if quest.is_completed else ""

    # Overdue Logic
    is_overdue = False
    if quest.deadline and not quest.is_completed:
        if quest.deadline < datetime.utcnow():
            is_overdue = True

    overdue_class = "overdue" if is_overdue else ""
    overdue_icon = "🔥 " if is_overdue else ""

    return f"""
        <div class="card sub-quest-card {completed_class} {overdue_class}" id="quest-{quest.id}">
            <div class="quest-header">
                <div class="quest-category">{quest.category}</div>
                <button class="delete-btn" hx-delete="/api/quest/{quest.id}" hx-target="#quest-{quest.id}" hx-swap="outerHTML">×</button>
            </div>
            <div class="quest-body">
                <input type="checkbox" class="quest-checkbox" 
                       {checked_attr}
                       hx-post="/api/quest/{quest.id}/toggle" 
                       hx-target="#progress-ring" 
                       hx-swap="outerHTML">
                <h4 hx-get="/api/quest/{quest.id}/edit" 
                    hx-trigger="click" 
                    hx-target="#quest-{quest.id}" 
                    hx-swap="outerHTML" 
                    style="cursor: pointer;" 
                    title="Click to edit details">{quest.title}</h4>
            </div>
            <!-- Client-side toggle script for immediate visual feedback on the card text -->
            <script>
                htmx.on("#quest-{quest.id}", "htmx:afterRequest", function(evt) {{
                    if(evt.detail.elt.classList.contains('quest-checkbox')) {{
                       document.getElementById("quest-{quest.id}").classList.toggle("completed");
                    }}
                }});
            </script>
            <div class="quest-meta">
                <span style="font-size: 0.85rem; color: var(--text-muted);">{overdue_icon}📅 {date_display}</span>
            </div>
        </div>
    """

@app.post("/api/onboarding/submit", response_class=HTMLResponse)
async def onboarding_submit(goal: str = Form(...), deadline: str = Form(None), db: Session = Depends(get_db)):
    """
    Handles submission of the first quest.
    """

    # Parse deadline if provided
    deadline_dt = None
    if deadline:
        try:
            deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            pass # Keep as None if invalid

    # Create the Main Quest
    new_quest = models.Quest(
        title=goal,
        category="Main",
        deadline=deadline_dt,
        is_completed=False,
        image_url=ai_service.get_vision_image(goal) # Generate image on creation
    )
    db.add(new_quest)

    # Create default settings if not exists
    if not db.query(models.Settings).first():
        new_settings = models.Settings(hero_name="Hero", theme_name="Cyberpunk")
        db.add(new_settings)

    db.commit()

    # Using HTMX Redirect to refresh to dashboard
    response = HTMLResponse()
    response.headers["HX-Redirect"] = "/"
    return response

@app.get("/api/settings/export")
async def export_data(db: Session = Depends(get_db)):
    """
    Exports all user data (Quests + Settings) as a JSON file download.
    """
    quests = db.query(models.Quest).all()
    settings = db.query(models.Settings).first()

    data = {
        "settings": jsonable_encoder(settings),
        "quests": jsonable_encoder(quests),
        "exported_at": datetime.utcnow().isoformat()
    }

    return JSONResponse(content=data, headers={"Content-Disposition": "attachment; filename=questlog_backup.json"})

@app.post("/api/settings/reset", response_class=HTMLResponse)
async def reset_data(db: Session = Depends(get_db)):
    """
    Deletes all data to allow a fresh start.
    """
    # Delete all quests
    db.query(models.Quest).delete()
    # Delete settings
    db.query(models.Settings).delete()
    db.commit()

    # Redirect to home (which will show onboarding)
    response = HTMLResponse()
    # HTMX handles redirects via this header for full page reload/navigation
    response.headers["HX-Redirect"] = "/"
    return response

