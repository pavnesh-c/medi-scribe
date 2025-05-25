from app import db
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

def init_db(app):
    """Initialize the database."""
    try:
        with app.app_context():
            db.create_all()
        logger.info("Database initialized successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def get_db():
    """Get database session."""
    return db.session

def commit_changes():
    """Commit changes to database."""
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Failed to commit changes: {str(e)}")
        raise 