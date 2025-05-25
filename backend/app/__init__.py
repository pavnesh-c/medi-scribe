import os
from flask import Flask
from flask_cors import CORS
from app.extensions import db, migrate
from app.api.health import bp as health_bp
from app.api.recording import bp as recording_bp
from app.api.soap_note import bp as soap_note_bp
from app.api.upload import bp as upload_bp
from app.api.live_conversation import bp as live_conversation_bp
from app.utils.logger import app_logger
import logging

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Configure app
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///medi_scribe.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configure CORS for development
    CORS(app, 
         resources={r"/*": {"origins": "*",
                          "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                          "allow_headers": ["Content-Type", "Authorization", "Accept"],
                          "expose_headers": ["Content-Type", "Authorization"],
                          "supports_credentials": True,
                          "max_age": 600}})
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(recording_bp, url_prefix='/api/v1')
    app.register_blueprint(soap_note_bp, url_prefix='/api/v1')
    app.register_blueprint(upload_bp, url_prefix='/api/v1')
    app.register_blueprint(live_conversation_bp)
    
    app_logger.info('Medi-Scribe application initialized')
    
    return app 