from datetime import datetime
from app import db

class UploadSession(db.Model):
    __tablename__ = 'upload_sessions'
    
    id = db.Column(db.String(36), primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    total_size = db.Column(db.BigInteger, nullable=False)
    total_chunks = db.Column(db.Integer, nullable=False)
    chunks_received = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum('uploading', 'combining', 'completed', 'failed'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Recording(db.Model):
    __tablename__ = 'recordings'
    
    id = db.Column(db.Integer, primary_key=True)
    upload_session_id = db.Column(db.String(36), db.ForeignKey('upload_sessions.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    duration = db.Column(db.Integer)
    status = db.Column(db.Enum('processing', 'completed', 'failed'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Transcription(db.Model):
    __tablename__ = 'transcriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    recording_id = db.Column(db.Integer, db.ForeignKey('recordings.id'), nullable=False)
    raw_text = db.Column(db.Text, nullable=False)
    processed_text = db.Column(db.Text)
    confidence_score = db.Column(db.Float)
    status = db.Column(db.Enum('processing', 'completed', 'failed'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SOAPNote(db.Model):
    __tablename__ = 'soap_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    recording_id = db.Column(db.Integer, db.ForeignKey('recordings.id'), nullable=False)
    transcription_id = db.Column(db.Integer, db.ForeignKey('transcriptions.id'), nullable=False)
    subjective = db.Column(db.Text)
    objective = db.Column(db.Text)
    assessment = db.Column(db.Text)
    plan = db.Column(db.Text)
    status = db.Column(db.Enum('draft', 'finalized', 'archived'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 