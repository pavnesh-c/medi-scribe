from flask import Blueprint, jsonify, request
from app.models.models import Recording, Transcription
from app.services.transcription import TranscriptionService
from app.utils.db import commit_changes
import logging
from app import db

logger = logging.getLogger(__name__)
bp = Blueprint('transcription', __name__)
transcription_service = TranscriptionService()

@bp.route('/transcription/start/<int:recording_id>', methods=['POST'])
def start_transcription(recording_id):
    """Start transcription for a recording."""
    try:
        logger.info(f"[TRANSCRIPTION] Starting transcription for recording_id={recording_id}")
        
        # Get recording
        recording = Recording.query.get(recording_id)
        if not recording:
            logger.error(f"[TRANSCRIPTION] Recording not found: recording_id={recording_id}")
            return jsonify({"status": "error", "message": "Recording not found"}), 404
            
        # Create transcription record
        transcription = Transcription(
            recording_id=recording_id,
            text="",  # Will be updated when transcription is complete
            status='processing'
        )
        db.session.add(transcription)
        commit_changes()
        
        # Process transcription synchronously
        process_transcription(recording, transcription)
        
        return jsonify({
            "status": "ok",
            "message": "Transcription completed",
            "transcription_id": transcription.id
        })
        
    except Exception as e:
        logger.error(f"[TRANSCRIPTION] Error processing transcription: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/transcription/<int:transcription_id>', methods=['GET'])
def get_transcription(transcription_id):
    """Get transcription status and results."""
    try:
        logger.info(f"[TRANSCRIPTION] Getting transcription status: transcription_id={transcription_id}")
        
        transcription = Transcription.query.get(transcription_id)
        if not transcription:
            logger.error(f"[TRANSCRIPTION] Transcription not found: transcription_id={transcription_id}")
            return jsonify({"status": "error", "message": "Transcription not found"}), 404
            
        return jsonify({
            "status": "ok",
            "transcription": {
                "id": transcription.id,
                "recording_id": transcription.recording_id,
                "text": transcription.text,
                "status": transcription.status,
                "meta": transcription.meta
            }
        })
        
    except Exception as e:
        logger.error(f"[TRANSCRIPTION] Error getting transcription: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_transcription(recording: Recording, transcription: Transcription):
    """Process transcription synchronously."""
    try:
        # Get transcription from Deepgram
        result = transcription_service.transcribe_audio(recording.file_path)
        
        # Update transcription record
        transcription.text = result['text']
        transcription.words = result['words']
        transcription.diarized_text = result['diarized_text']
        transcription.meta = result['meta']
        transcription.status = 'completed'
        
        # Update recording status
        recording.status = 'completed'
        
        commit_changes()
        logger.info(f"[TRANSCRIPTION] Completed transcription for recording_id={recording.id}")
        
    except Exception as e:
        logger.error(f"[TRANSCRIPTION] Error processing transcription: {str(e)}")
        transcription.status = 'failed'
        recording.status = 'failed'
        commit_changes() 