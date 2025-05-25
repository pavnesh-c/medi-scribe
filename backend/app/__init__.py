from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from config import Config
from app.utils.logger import setup_logger
from app.utils.db import init_db

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Setup logging
    setup_logger(app)
    
    # Initialize database
    with app.app_context():
        init_db()
    
    # Register blueprints
    from app.api.health import bp as health_bp
    app.register_blueprint(health_bp, url_prefix='/api/v1')
    
    from app.api.upload import bp as upload_bp
    app.register_blueprint(upload_bp, url_prefix='/api/v1')
    
    from app.api.recording import bp as recording_bp
    app.register_blueprint(recording_bp, url_prefix='/api/v1')
    
    from app.api.transcription import bp as transcription_bp
    app.register_blueprint(transcription_bp, url_prefix='/api/v1')
    
    from app.api.soap_note import bp as soap_note_bp
    app.register_blueprint(soap_note_bp, url_prefix='/api/v1')
    
    return app 