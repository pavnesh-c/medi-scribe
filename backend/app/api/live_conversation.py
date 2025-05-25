from flask import Blueprint, request, jsonify
from app.services.live_conversation import LiveConversationProcessor
from app.utils.logger import service_logger
from app.models.models import Recording, Transcription, SOAPNote, UploadSession
from app.utils.db import commit_changes
from app import db
import uuid
from datetime import datetime

logger = service_logger

# Store active conversations
active_conversations = {}

bp = Blueprint('live_conversation', __name__, url_prefix='/api/v1/live-conversation')

@bp.route('/start', methods=['POST'])
def start_conversation():
    """Start a new live conversation session."""
    try:
        conversation_id = str(uuid.uuid4())
        processor = LiveConversationProcessor(conversation_id)
        active_conversations[conversation_id] = processor
        
        logger.info(f"[LIVE] Started new conversation: {conversation_id}")
        return jsonify({
            'conversation_id': conversation_id,
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"[LIVE] Error starting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<conversation_id>/utterance', methods=['POST'])
def process_utterance(conversation_id):
    """Process an audio utterance from a live conversation."""
    try:
        if conversation_id not in active_conversations:
            return jsonify({
                'status': 'error',
                'message': 'Conversation not found or already ended'
            }), 404

        processor = active_conversations[conversation_id]
        if not processor.is_active:
            return jsonify({
                'status': 'error',
                'message': 'Conversation is not active'
            }), 400

        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No audio file provided'
            }), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No audio file selected'
            }), 400

        # Create an upload session for the recording
        upload_session = UploadSession(
            id=str(uuid.uuid4()),
            file_name=audio_file.filename,
            total_size=0,  # We don't know the size yet
            total_chunks=1,
            status='completed'
        )
        db.session.add(upload_session)
        db.session.commit()

        # Process the audio chunk
        text, speaker = processor.process_audio_chunk(audio_file)
        
        if not text:
            return jsonify({
                'status': 'no_speech',
                'message': 'No speech detected in audio'
            }), 200

        # Save the recording
        recording = Recording(
            upload_session_id=upload_session.id,
            file_path=audio_file.filename,
            file_name=audio_file.filename,
            file_size=0,  # We'll update this after saving
            duration=None,  # We'll update this after processing
            status='completed'
        )
        db.session.add(recording)
        db.session.commit()

        # Create utterance dictionary
        utterance = {
            'speaker': speaker,
            'text': text
        }

        # Process the utterance and get summary
        summary = processor.process_utterance(utterance)

        return jsonify({
            'status': 'success',
            'utterance_processed': True,
            'speaker': speaker,
            'transcription': text,
            'summary': summary if summary else None,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error processing utterance: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/<conversation_id>/end', methods=['POST'])
def end_conversation(conversation_id):
    """End a conversation and generate final SOAP note."""
    try:
        if conversation_id not in active_conversations:
            return jsonify({'error': 'Conversation not found'}), 404
            
        processor = active_conversations[conversation_id]
        if not processor.is_active:
            return jsonify({'error': 'Conversation has already ended'}), 400
            
        # Get the final SOAP note data
        soap_note_data = processor.end_conversation()
        
        # Create an upload session for the final recording
        upload_session = UploadSession(
            id=str(uuid.uuid4()),
            file_name=f"{conversation_id}_live.webm",
            total_size=0,
            total_chunks=1,
            status='completed'
        )
        db.session.add(upload_session)
        db.session.commit()
        
        # Create a recording record for the live conversation
        recording = Recording(
            upload_session_id=upload_session.id,
            file_path=f"/tmp/{conversation_id}_live.webm",
            file_name=f"{conversation_id}_live.webm",
            file_size=0,
            status='completed'
        )
        db.session.add(recording)
        db.session.commit()
        
        # Create a transcription record
        transcription = Transcription(
            recording_id=recording.id,
            text="",  # We don't store the full text for live conversations
            diarized_text=processor.utterance_buffer,  # Store the diarized text
            status='completed'
        )
        db.session.add(transcription)
        db.session.commit()
        
        # Create the SOAP note record
        soap_note = SOAPNote(
            recording_id=recording.id,
            transcription_id=transcription.id,
            subjective=soap_note_data['subjective'],
            objective=soap_note_data['objective'],
            assessment=soap_note_data['assessment'],
            plan=soap_note_data['plan'],
            status='finalized'
        )
        db.session.add(soap_note)
        db.session.commit()
        
        # Keep the conversation in memory for a short while to allow stats retrieval
        # but mark it as inactive
        processor.is_active = False
        
        logger.info(f"[LIVE] Ended conversation: {conversation_id}")
        return jsonify({
            'status': 'ended',
            'soap_note': soap_note_data,
            'soap_note_id': soap_note.id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"[LIVE] Error ending conversation: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<conversation_id>/stats', methods=['GET'])
def get_conversation_stats(conversation_id):
    """Get statistics about an active conversation."""
    try:
        if conversation_id not in active_conversations:
            return jsonify({'error': 'Conversation not found'}), 404
            
        processor = active_conversations[conversation_id]
        stats = processor.get_conversation_stats()
        
        # If conversation has ended and we have the final SOAP note,
        # we can remove it from active conversations
        if not processor.is_active and processor.final_soap_note:
            del active_conversations[conversation_id]
            logger.info(f"[LIVE] Removed ended conversation from memory: {conversation_id}")
            
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"[LIVE] Error getting conversation stats: {e}")
        return jsonify({'error': str(e)}), 500 