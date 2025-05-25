import logging
import os
from flask import Blueprint, request, jsonify, current_app
from app.models.models import UploadSession, Recording, Transcription, SOAPNote
from app.utils.db import commit_changes
from app import db
from werkzeug.utils import secure_filename
from app.services.transcription import TranscriptionService
from app.services.soap_note import SOAPNoteService

logger = logging.getLogger(__name__)
bp = Blueprint('upload', __name__)

# Initialize services
transcription_service = TranscriptionService()
soap_note_service = SOAPNoteService()

# Ensure uploads directory exists
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

def combine_chunks(session_id: str, file_name: str) -> str:
    """Combine all chunks into a single file."""
    try:
        session = UploadSession.query.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        final_path = os.path.join(UPLOADS_DIR, file_name)
        with open(final_path, 'wb') as outfile:
            for i in range(session.total_chunks):
                chunk_path = os.path.join(UPLOADS_DIR, f"{session_id}_{i}")
                if not os.path.exists(chunk_path):
                    raise FileNotFoundError(f"Chunk {i} not found at {chunk_path}")
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(chunk_path)
                logger.info(f"Combined and deleted chunk {i} for session {session_id}")
        session.status = 'completed'
        commit_changes()
        logger.info(f"Successfully combined all chunks for session {session_id} into {final_path}")
        return final_path
    except Exception as e:
        logger.error(f"Error combining chunks for session {session_id}: {str(e)}")
        session.status = 'failed'
        commit_changes()
        raise

@bp.route('/upload/init', methods=['POST'])
def init_upload():
    """Initialize a new upload session."""
    try:
        data = request.get_json()
        if not data or 'filename' not in data or 'total_chunks' not in data or 'chunk_size' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required fields"
            }), 400

        session = UploadSession(
            file_name=data['filename'],
            total_size=data['chunk_size'],
            total_chunks=data['total_chunks'],
            status='uploading'
        )
        db.session.add(session)
        commit_changes()
        logger.info(f"Created upload session {session.id} for file {data['filename']}")

        return jsonify({
            "status": "ok",
            "session_id": session.id
        })
    except Exception as e:
        logger.error(f"Error initializing upload: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to initialize upload"
        }), 500

@bp.route('/upload/chunk', methods=['POST'])
def upload_chunk():
    """Upload a chunk of the file."""
    try:
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No file part"
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "No selected file"
            }), 400

        session_id = request.form.get('session_id')
        chunk_index = int(request.form.get('chunk_index', 0))

        if not session_id:
            return jsonify({
                "status": "error",
                "message": "No session ID provided"
            }), 400

        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({
                "status": "error",
                "message": "Invalid session ID"
            }), 400

        logger.info(f"Uploading chunk {chunk_index} for session {session_id} (current chunks_received={session.chunks_received}, total_chunks={session.total_chunks})")

        # Save chunk
        chunk_path = os.path.join(UPLOADS_DIR, f"{session_id}_{chunk_index}")
        file.save(chunk_path)
        session.chunks_received += 1
        commit_changes()
        logger.info(f"Saved chunk {chunk_index} for session {session_id} (new chunks_received={session.chunks_received})")

        return jsonify({
            "status": "ok",
            "chunks_received": session.chunks_received
        })
    except Exception as e:
        logger.error(f"Error uploading chunk: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to upload chunk"
        }), 500

@bp.route('/upload/finish', methods=['POST'])
def finish_upload():
    """Finish the upload and start processing."""
    try:
        data = request.get_json()
        if not data or 'session_id' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing session ID"
            }), 400

        session_id = data['session_id']
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({
                "status": "error",
                "message": "Invalid session ID"
            }), 400

        logger.info(f"Finishing upload for session {session_id}: chunks_received={session.chunks_received}, total_chunks={session.total_chunks}")
        
        if session.chunks_received != session.total_chunks:
            logger.error(f"Chunk count mismatch: received {session.chunks_received} chunks, expected {session.total_chunks} chunks")
            return jsonify({
                "status": "error",
                "message": f"Not all chunks received (received {session.chunks_received}, expected {session.total_chunks})"
            }), 400

        try:
            final_path = combine_chunks(session_id, session.file_name)
            recording = Recording(
                upload_session_id=session_id,
                file_path=final_path,
                file_name=session.file_name,
                file_size=os.path.getsize(final_path),
                status='processing'
            )
            db.session.add(recording)
            commit_changes()
            logger.info(f"Created recording record for session {session_id}")

            # Process recording synchronously
            try:
                # Transcribe audio
                transcription_result = transcription_service.transcribe_audio(recording.file_path)
                
                # Create transcription record
                transcription = Transcription(
                    recording_id=recording.id,
                    text=transcription_result['text'],
                    diarized_text=transcription_result.get('diarized_text'),
                    status='completed'
                )
                db.session.add(transcription)
                db.session.commit()

                # Generate SOAP note
                soap_note, _ = soap_note_service.generate_soap_note(transcription_result['diarized_text'])
                
                # Create SOAP note record
                soap = SOAPNote(
                    recording_id=recording.id,
                    transcription_id=transcription.id,
                    subjective=soap_note['subjective'],
                    objective=soap_note['objective'],
                    assessment=soap_note['assessment'],
                    plan=soap_note['plan'],
                    status='finalized'
                )
                db.session.add(soap)
                db.session.commit()

                # Update recording status
                recording.status = 'completed'
                db.session.commit()

                return jsonify({
                    "status": "ok",
                    "message": "Processing completed successfully",
                    "file_path": final_path,
                    "recording_id": recording.id,
                    "transcription_id": transcription.id,
                    "soap_note_id": soap.id
                })
            except Exception as e:
                logger.error(f"Error processing recording: {str(e)}")
                recording.status = 'failed'
                db.session.commit()
                raise

        except Exception as e:
            logger.error(f"Error combining chunks for session {session_id}: {str(e)}")
            session.status = 'failed'
            commit_changes()
            return jsonify({
                "status": "error",
                "message": "Failed to combine chunks"
            }), 500
    except Exception as e:
        logger.error(f"Error finishing upload: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to finish upload"
        }), 500 