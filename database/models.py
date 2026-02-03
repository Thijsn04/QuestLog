from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Quest(Base):
    """
    Represents a user's goal or task.
    Supports a hierarchy via parent_id to allow for Main Quests and Sub-Quests.
    """
    __tablename__ = 'quests'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)  # e.g., "Health", "Wealth"

    # Hierarchy
    parent_id = Column(Integer, ForeignKey('quests.id'), nullable=True)
    children = relationship("Quest", backref='parent', remote_side=[id])

    # Status
    is_completed = Column(Boolean, default=False)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Visuals
    image_url = Column(String, nullable=True)

    # Ordering
    position = Column(Integer, default=0)

class Settings(Base):
    """
    Stores user preferences like theme, hero name, etc.
    """
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, index=True)
    hero_name = Column(String, default="Hero")
    theme_name = Column(String, default="Cyberpunk") # Default theme

    # Gamification
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)

    # Motivation Engine
    daily_quote = Column(String, nullable=True)
    last_quote_date = Column(DateTime, nullable=True)
