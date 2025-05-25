import logging
from flask_migrate import Migrate

logger = logging.getLogger(__name__)
migrate = Migrate()

def init_db():
    """Initialize the database."""
    try:
        from app import db
        db.create_all()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def commit_changes():
    """Commit changes to the database."""
    try:
        from app import db
        db.session.commit()
    except Exception as e:
        from app import db
        db.session.rollback()
        logger.error(f"Failed to commit changes: {str(e)}")
        raise 