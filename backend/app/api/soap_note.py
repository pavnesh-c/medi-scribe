from flask import Blueprint, jsonify, request
from app.models.models import Recording, Transcription, SOAPNote, ChunkSummary
from app.services.soap_note import SOAPNoteService
from app.utils.db import commit_changes
import logging
import json
from app import db

logger = logging.getLogger(__name__)
bp = Blueprint('soap_note', __name__)
soap_note_service = SOAPNoteService()

@bp.route('/soap-note/generate/<int:transcription_id>', methods=['POST'])
def generate_soap_note(transcription_id):
    """Generate a SOAP note from a transcription."""
    try:
        logger.info(f"[SOAP] Starting SOAP note generation for transcription_id={transcription_id}")
        
        # Get transcription
        transcription = Transcription.query.get(transcription_id)
        if not transcription:
            logger.error(f"[SOAP] Transcription not found: transcription_id={transcription_id}")
            return jsonify({"status": "error", "message": "Transcription not found"}), 404
            
        if not transcription.diarized_text:
            logger.error(f"[SOAP] No diarized text found in transcription: transcription_id={transcription_id}")
            return jsonify({"status": "error", "message": "No diarized text available"}), 400
            
        # Generate SOAP note with chunk summaries
        soap_note_data, chunk_summaries = soap_note_service.generate_soap_note(transcription.diarized_text)
        logger.info(f"[SOAP] Generated SOAP note data: {soap_note_data}")
        
        # Create SOAP note record
        soap_note = SOAPNote(
            recording_id=transcription.recording_id,
            transcription_id=transcription_id,
            subjective=soap_note_data['subjective'],
            objective=soap_note_data['objective'],
            assessment=soap_note_data['assessment'],
            plan=soap_note_data['plan'],
            status='draft'
        )
        db.session.add(soap_note)
        commit_changes()  # Commit to get the SOAP note ID
        
        # Create chunk summary records
        for idx, (chunk_text, summary) in enumerate(chunk_summaries):
            chunk_summary = ChunkSummary(
                soap_note_id=soap_note.id,
                chunk_index=idx,
                chunk_text=chunk_text,
                summary=summary
            )
            db.session.add(chunk_summary)
        
        commit_changes()
        
        return jsonify({
            "status": "ok",
            "message": "SOAP note generated successfully",
            "soap_note_id": soap_note.id
        })
        
    except Exception as e:
        logger.error(f"[SOAP] Error generating SOAP note: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/soap-note/<int:soap_note_id>', methods=['GET'])
def get_soap_note(soap_note_id):
    """Get a SOAP note by ID."""
    try:
        logger.info(f"[SOAP] Getting SOAP note: soap_note_id={soap_note_id}")
        
        soap_note = SOAPNote.query.get(soap_note_id)
        if not soap_note:
            logger.error(f"[SOAP] SOAP note not found: soap_note_id={soap_note_id}")
            return jsonify({"status": "error", "message": "SOAP note not found"}), 404
            
        # Get chunk summaries
        chunk_summaries = ChunkSummary.query.filter_by(soap_note_id=soap_note_id).order_by(ChunkSummary.chunk_index).all()
            
        return jsonify({
            "status": "ok",
            "soap_note": {
                "id": soap_note.id,
                "recording_id": soap_note.recording_id,
                "transcription_id": soap_note.transcription_id,
                "subjective": soap_note.subjective,
                "objective": soap_note.objective,
                "assessment": soap_note.assessment,
                "plan": soap_note.plan,
                "status": soap_note.status,
                "created_at": soap_note.created_at.isoformat(),
                "updated_at": soap_note.updated_at.isoformat(),
                "chunk_summaries": [{
                    "chunk_index": cs.chunk_index,
                    "chunk_text": cs.chunk_text,
                    "summary": cs.summary
                } for cs in chunk_summaries]
            }
        })
        
    except Exception as e:
        logger.error(f"[SOAP] Error getting SOAP note: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/soap-note/<int:soap_note_id>', methods=['PUT'])
def update_soap_note(soap_note_id):
    """Update a SOAP note."""
    try:
        logger.info(f"[SOAP] Updating SOAP note: soap_note_id={soap_note_id}")
        
        soap_note = SOAPNote.query.get(soap_note_id)
        if not soap_note:
            logger.error(f"[SOAP] SOAP note not found: soap_note_id={soap_note_id}")
            return jsonify({"status": "error", "message": "SOAP note not found"}), 404
            
        data = request.get_json()
        
        # Update fields if provided
        if 'subjective' in data:
            soap_note.subjective = data['subjective']
        if 'objective' in data:
            soap_note.objective = data['objective']
        if 'assessment' in data:
            soap_note.assessment = data['assessment']
        if 'plan' in data:
            soap_note.plan = data['plan']
        if 'status' in data:
            soap_note.status = data['status']
            
        commit_changes()
        
        return jsonify({
            "status": "ok",
            "message": "SOAP note updated successfully"
        })
        
    except Exception as e:
        logger.error(f"[SOAP] Error updating SOAP note: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/soap-note', methods=['GET'])
def get_all_soap_notes():
    """Get all SOAP notes."""
    try:
        logger.info("[SOAP] Getting all SOAP notes")
        
        soap_notes = SOAPNote.query.order_by(SOAPNote.created_at.desc()).all()
        
        return jsonify({
            "status": "ok",
            "soap_notes": [{
                "id": note.id,
                "recording_id": note.recording_id,
                "transcription_id": note.transcription_id,
                "subjective": note.subjective,
                "objective": note.objective,
                "assessment": note.assessment,
                "plan": note.plan,
                "status": note.status,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat()
            } for note in soap_notes]
        })
        
    except Exception as e:
        logger.error(f"[SOAP] Error getting all SOAP notes: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500 