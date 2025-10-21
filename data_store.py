from __future__ import annotations
import os, json, time
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from cfg import DB_PATH
from logger import logger

Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)   # Gmail msg id
    snippet = Column(Text)
    text = Column(Text)                      # preprocessed text
    label_guess = Column(String, nullable=True)
    spam_score = Column(Float, default=0.0)
    target_label = Column(String, nullable=True)
    reviewed = Column(Boolean, default=False)
    gold_label = Column(String, nullable=True)  # user feedback
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

def init_db():
    """Initialize database with error handling."""
    try:
        Base.metadata.create_all(engine)
        logger.info(f"Database initialized at {DB_PATH}")
    except SQLAlchemyError as e:
        logger.error(f"Database initialization error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing database: {e}")
        raise

def upsert_message(msg_id: str, snippet: str, text: str):
    """Insert or update a message with error handling."""
    session = Session()
    try:
        m = session.get(Message, msg_id)
        if not m:
            m = Message(id=msg_id, snippet=snippet, text=text)
            session.add(m)
            logger.debug(f"Inserted new message {msg_id}")
        else:
            m.snippet = snippet
            m.text = text
            logger.debug(f"Updated message {msg_id}")
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error upserting message {msg_id}: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error upserting message {msg_id}: {e}")
        raise
    finally:
        session.close()

def save_prediction(msg_id: str, spam_score: float, label_guess: Optional[str], target_label: Optional[str]):
    """Save prediction results with error handling."""
    session = Session()
    try:
        m = session.get(Message, msg_id)
        if not m:
            m = Message(id=msg_id)
            session.add(m)
        m.spam_score = spam_score
        m.label_guess = label_guess
        m.target_label = target_label
        session.commit()
        logger.debug(f"Saved prediction for message {msg_id}")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error saving prediction for {msg_id}: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error saving prediction for {msg_id}: {e}")
        raise
    finally:
        session.close()

def mark_review(msg_id: str, gold_label: str):
    """Mark a message as reviewed with error handling."""
    session = Session()
    try:
        m = session.get(Message, msg_id)
        if not m:
            logger.warning(f"Attempted to mark non-existent message {msg_id} as reviewed")
            return
        m.gold_label = gold_label
        m.reviewed = True
        session.commit()
        logger.debug(f"Marked message {msg_id} as reviewed with label {gold_label}")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error marking review for {msg_id}: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error marking review for {msg_id}: {e}")
        raise
    finally:
        session.close()

def fetch_for_training(limit: int = 2000):
    """Fetch reviewed messages for training with error handling."""
    session = Session()
    try:
        rows = session.query(Message).filter(Message.gold_label.isnot(None)).limit(limit).all()
        texts = [r.text for r in rows]
        y = [r.gold_label for r in rows]
        logger.info(f"Fetched {len(texts)} messages for training")
        return texts, y
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching training data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching training data: {e}")
        raise
    finally:
        session.close()

def fetch_for_prediction(limit: int = 200):
    """Fetch unreviewed messages for prediction with error handling."""
    session = Session()
    try:
        rows = session.query(Message).filter(Message.reviewed == False).limit(limit).all()
        logger.info(f"Fetched {len(rows)} messages for prediction")
        return rows
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching prediction data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching prediction data: {e}")
        raise
    finally:
        session.close()
