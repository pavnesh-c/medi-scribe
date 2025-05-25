import logging
import os
from flask import Blueprint, request, jsonify
from app.models.models import UploadSession, Recording
from app.utils.db import commit_changes
from app import db

logger = logging.getLogger(__name__)
bp = Blueprint('upload', __name__)

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
    try:
        data = request.json
        if not all(key in data for key in ['id', 'file_name', 'total_size', 'total_chunks']):
            return jsonify({
                "status": "error",
                "message": "Missing required fields: id, file_name, total_size, total_chunks"
            }), 400
        existing_session = UploadSession.query.get(data['id'])
        if existing_session:
            return jsonify({
                "status": "error",
                "message": "Session ID already exists"
            }), 409
        session = UploadSession(
            id=data['id'],
            file_name=data['file_name'],
            total_size=data['total_size'],
            total_chunks=data['total_chunks'],
            status='uploading',
            chunks_received=0
        )
        db.session.add(session)
        commit_changes()
        return jsonify({
            "status": "ok",
            "message": "Upload session initialized",
            "id": session.id
        })
    except Exception as e:
        logger.error(f"Error initializing upload session: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to initialize upload session"
        }), 500

@bp.route('/upload/chunk', methods=['POST'])
def upload_chunk():
    try:
        if 'session_id' not in request.form:
            return jsonify({
                "status": "error",
                "message": "Missing session_id"
            }), 400
        if 'chunk_number' not in request.form:
            return jsonify({
                "status": "error",
                "message": "Missing chunk_number"
            }), 400
        if 'chunk' not in request.files:
            return jsonify({
                "status": "error",
                "message": "Missing chunk file"
            }), 400
        session_id = request.form['session_id']
        chunk_number = int(request.form['chunk_number'])
        chunk = request.files['chunk']
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({
                "status": "error",
                "message": "Session not found"
            }), 404
        if session.status != 'uploading':
            return jsonify({
                "status": "error",
                "message": f"Invalid session status: {session.status}"
            }), 400
        if chunk_number >= session.total_chunks:
            return jsonify({
                "status": "error",
                "message": f"Invalid chunk number: {chunk_number}. Total chunks: {session.total_chunks}"
            }), 400
        chunk_path = os.path.join(UPLOADS_DIR, f"{session_id}_{chunk_number}")
        chunk.save(chunk_path)
        logger.info(f"Saved chunk {chunk_number} for session {session_id} to {chunk_path}")
        session.chunks_received += 1
        commit_changes()
        return jsonify({
            "status": "ok",
            "message": "Chunk uploaded successfully",
            "chunks_received": session.chunks_received,
            "total_chunks": session.total_chunks
        })
    except Exception as e:
        logger.error(f"Error uploading chunk: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to upload chunk"
        }), 500

@bp.route('/upload/finish', methods=['POST'])
def finish_upload():
    try:
        data = request.json
        if 'session_id' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing session_id"
            }), 400
        session_id = data['session_id']
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({
                "status": "error",
                "message": "Session not found"
            }), 404
        if session.chunks_received != session.total_chunks:
            return jsonify({
                "status": "error",
                "message": f"Not all chunks uploaded: {session.chunks_received}/{session.total_chunks}"
            }), 400
        session.status = 'combining'
        commit_changes()
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
        except Exception as e:
            logger.error(f"Error combining chunks for session {session_id}: {str(e)}")
            session.status = 'failed'
            commit_changes()
            return jsonify({
                "status": "error",
                "message": "Failed to combine chunks"
            }), 500
        return jsonify({
            "status": "ok",
            "message": "Chunks combined successfully",
            "file_path": final_path,
            "recording_id": recording.id
        })
    except Exception as e:
        logger.error(f"Error finishing upload: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to finish upload"
        }), 500

@bp.route('/upload/<session_id>', methods=['DELETE'])
def delete_upload(session_id):
    try:
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({
                "status": "error",
                "message": "Session not found"
            }), 404
        for i in range(session.total_chunks):
            chunk_path = os.path.join(UPLOADS_DIR, f"{session_id}_{i}")
            if os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    logger.info(f"Deleted chunk file: {chunk_path}")
                except Exception as e:
                    logger.error(f"Error deleting chunk file {chunk_path}: {str(e)}")
        final_path = os.path.join(UPLOADS_DIR, session.file_name)
        if os.path.exists(final_path):
            try:
                os.remove(final_path)
                logger.info(f"Deleted combined file: {final_path}")
            except Exception as e:
                logger.error(f"Error deleting combined file {final_path}: {str(e)}")
        db.session.delete(session)
        commit_changes()
        logger.info(f"Deleted upload session: {session_id}")
        return jsonify({
            "status": "ok",
            "message": "Upload session deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting upload session: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to delete upload session"
        }), 500 