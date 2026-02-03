from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text # Import text
from .models import Base

# Using SQLite for simplicity in this phase.
# can be swapped for PostgreSQL in production.
SQLALCHEMY_DATABASE_URL = "sqlite:///./questlog.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database tables."""
    Base.metadata.create_all(bind=engine)

    # Poor man's migration to ensure new columns exist for existing databases
    # (Safe to run multiple times, sqlite ignores 'duplicate column' errors mostly or we catch them)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE settings ADD COLUMN xp INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE settings ADD COLUMN level INTEGER DEFAULT 1"))
            conn.execute(text("ALTER TABLE settings ADD COLUMN daily_quote VARCHAR"))
            conn.execute(text("ALTER TABLE settings ADD COLUMN last_quote_date DATETIME"))
            conn.execute(text("ALTER TABLE quests ADD COLUMN image_url VARCHAR"))
            conn.execute(text("ALTER TABLE quests ADD COLUMN position INTEGER DEFAULT 0"))
            conn.commit() # Commit explicitly for some drivers
    except Exception:
        pass # Columns likely exist

def get_db():
    """Dependency for FastAPI route handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
