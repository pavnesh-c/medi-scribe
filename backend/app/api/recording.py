import logging
from flask import Blueprint, request, jsonify
from app.models.models import Recording
from app.utils.db import commit_changes
import os
from app import db

logger = logging.getLogger(__name__)
bp = Blueprint('recording', __name__)

@bp.route('/recording/upload', methods=['POST'])
def upload_recording():
    session_id = request.form['session_id']
    file = request.files['file']
    logger.info(f"[UPLOAD] Request received: session_id={session_id}, file_name={file.filename}, file_size={os.fstat(file.fileno()).st_size}")
    
    recording = Recording(
        upload_session_id=session_id,
        file_path=os.path.join('uploads', file.filename),
        file_name=file.filename,
        file_size=os.fstat(file.fileno()).st_size,
        status='processing'
    )
    logger.info(f"[UPLOAD] Recording object created: recording.id={recording.id}, file_path={recording.file_path}")
    db.session.add(recording)
    logger.info(f"[UPLOAD] Recording added to session: recording.id={recording.id}")
    commit_changes()
    logger.info(f"[UPLOAD] Changes committed: recording.id={recording.id}")
    
    file.save(recording.file_path)
    logger.info(f"[UPLOAD] File saved to {recording.file_path}")
    logger.info(f"[UPLOAD] Before return: recording.id={recording.id}")
    response = {
        "status": "ok", 
        "message": "Recording uploaded successfully",
        "recording_id": recording.id
    }
    logger.info(f"[UPLOAD] Response: {response}")
    return jsonify(response)

@bp.route('/recording/validate/<int:recording_id>', methods=['GET'])
def validate_recording(recording_id):
    logger.info(f"[VALIDATE] Request received: recording_id={recording_id}")
    recording = Recording.query.get(recording_id)
    if not recording:
        logger.error(f"[VALIDATE] Recording not found: recording_id={recording_id}")
        return jsonify({"status": "error", "message": "Recording not found"}), 404
    
    # Add validation logic here
    recording.status = 'completed'
    commit_changes()
    logger.info(f"[VALIDATE] Recording validated successfully: recording_id={recording_id}")
    return jsonify({"status": "ok", "message": "Recording validated successfully"})

@bp.route('/recording/<int:recording_id>', methods=['DELETE'])
def delete_recording(recording_id):
    logger.info(f"[DELETE] Request received: recording_id={recording_id}")
    
    # Check if recording exists before deletion
    recording = Recording.query.get(recording_id)
    logger.info(f"[DELETE] Recording query result: {recording}")
    
    if not recording:
        logger.error(f"[DELETE] Recording not found: recording_id={recording_id}")
        return jsonify({"status": "error", "message": "Recording not found"}), 404
    
    # Log recording details before deletion
    logger.info(f"[DELETE] Recording details before deletion: id={recording.id}, file_path={recording.file_path}, status={recording.status}")
    
    # Delete associated file
    if os.path.exists(recording.file_path):
        os.remove(recording.file_path)
        logger.info(f"[DELETE] File deleted: {recording.file_path}")
    else:
        logger.warning(f"[DELETE] File not found: {recording.file_path}")
    
    # Delete from database
    db.session.delete(recording)
    logger.info(f"[DELETE] Recording marked for deletion in session")
    commit_changes()
    logger.info(f"[DELETE] Changes committed to database")
    
    # Verify deletion
    recording_after = Recording.query.get(recording_id)
    logger.info(f"[DELETE] Recording after deletion query: {recording_after}")
    
    return jsonify({"status": "ok", "message": "Recording deleted successfully"}) 