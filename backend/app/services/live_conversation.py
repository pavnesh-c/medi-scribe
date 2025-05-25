import os
import logging
import json
import uuid
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from app.utils.logger import service_logger
from datetime import datetime
from app.services.transcription import TranscriptionService
from app.models.models import Recording, Transcription, UploadSession
from app.services.soap_note import SOAPNoteService
from app.utils.audio_utils import combine_audio_chunks

logger = service_logger

class LiveConversationProcessor:
    def __init__(self):
        self.logger = service_logger
        self.transcription_service = TranscriptionService()
        self.soap_note_service = SOAPNoteService()
        self.upload_dir = os.getenv('UPLOAD_DIR', 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Buffers for processing
        self.utterance_buffer = []
        self.summary_buffer = []
        self.max_buffer_size = 40  # Maximum utterances before summarization
        self.start_time = datetime.now()
        
        # State tracking
        self.is_active = True
        self.last_summary_time = None
        self.total_utterances = 0
        self.end_time = None
        self.final_soap_note = None
        
        logger.info(f"[LIVE] Initialized conversation processor")

    def process_audio_chunk(self, audio_chunk: bytes, session_id: str) -> Dict:
        """
        Process a single audio chunk from the live conversation.
        
        Args:
            audio_chunk (bytes): The audio chunk data
            session_id (str): The session ID for this conversation
            
        Returns:
            Dict: Processing result with status and any generated content
        """
        try:
            self.logger.info(f"Processing audio chunk for session {session_id}")
            self.logger.info(f"Audio chunk size: {len(audio_chunk)} bytes")
            
            if not audio_chunk:
                raise ValueError("Empty audio chunk received")
            
            # Generate a unique ID for this chunk
            chunk_id = str(uuid.uuid4())
            
            # Save the chunk to a temporary file
            chunk_path = os.path.join(self.upload_dir, f"{chunk_id}.webm")
            with open(chunk_path, 'wb') as f:
                f.write(audio_chunk)
            
            self.logger.info(f"Saved audio chunk to {chunk_path}")
            
            # Create an upload session for this chunk
            upload_session = UploadSession(
                id=chunk_id,
                file_name=f"{chunk_id}.webm",
                total_size=len(audio_chunk),
                total_chunks=1,
                status='completed'
            )
            
            # Create a recording entry
            recording = Recording(
                upload_session_id=chunk_id,
                file_path=chunk_path,
                file_name=f"{chunk_id}.webm",
                file_size=len(audio_chunk),
                status='completed'
            )
            
            # Transcribe the chunk
            transcription_result = self.transcription_service.transcribe_audio(chunk_path)
            
            if not transcription_result.get('text'):
                self.logger.warning(f"No text transcribed from chunk {chunk_id}")
                return {
                    'status': 'error',
                    'message': 'No speech detected in audio chunk'
                }
            
            # Create transcription entry
            transcription = Transcription(
                recording_id=recording.id,
                text=transcription_result['text'],
                diarized_text=json.dumps(transcription_result['diarized_text']),
                confidence=transcription_result['meta']['confidence'],
                status='completed'
            )
            
            # Generate SOAP note if we have enough content
            soap_note = None
            if transcription_result['text']:
                soap_note = self.soap_note_service.generate_soap_note(transcription_result['text'])
            
            return {
                'status': 'success',
                'recording_id': recording.id,
                'transcription_id': transcription.id,
                'text': transcription_result['text'],
                'diarized_text': transcription_result['diarized_text'],
                'confidence': transcription_result['meta']['confidence'],
                'soap_note': soap_note
            }
            
        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
        finally:
            # Clean up the temporary chunk file
            if 'chunk_path' in locals() and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    self.logger.info(f"Cleaned up temporary chunk file: {chunk_path}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up chunk file: {str(e)}")

    def process_utterance(self, utterance: Dict) -> Optional[str]:
        """
        Process a new utterance and generate summary if buffer is full.
        
        Args:
            utterance: Dictionary containing speaker and text information
            
        Returns:
            Optional[str]: Summary if generated, None otherwise
        """
        if not self.is_active:
            logger.warning(f"[LIVE] Attempted to process utterance for inactive conversation")
            return None

        try:
            self.utterance_buffer.append(utterance)
            self.total_utterances += 1
            
            # Check if we should generate a summary
            if len(self.utterance_buffer) >= self.max_buffer_size:
                summary = self._summarize_chunk()
                if summary:
                    self.summary_buffer.append(summary)
                    self.last_summary_time = datetime.now()
                    return summary
                    
        except Exception as e:
            logger.error(f"[LIVE] Error processing utterance: {e}")
            return None

    def _summarize_chunk(self) -> Optional[str]:
        """
        Summarize the current buffer of utterances.
        
        Returns:
            Optional[str]: Generated summary or None if failed
        """
        if not self.utterance_buffer:
            return None

        try:
            # Format conversation for summarization
            conversation = "\n".join([
                f"{utterance.get('speaker', 'Unknown')}: {utterance.get('text', '')}"
                for utterance in self.utterance_buffer
            ])
            
            # Generate summary using OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """You are an expert medical scribe assistant. Your task is to provide a concise, factual summary of a segment of a medical conversation. 
                    Focus ONLY on extracting key medical information: patient's reported symptoms, historical context, current complaints, physical findings, doctor's observations, and any specific questions or instructions.
                    Do NOT interpret, diagnose, or generate a SOAP note. Just summarize the raw content.
                    Your output MUST be a JSON object with a single key 'summary' containing the summarized text. Ensure the JSON is well-formed."""},
                    {"role": "user", "content": f"""Summarize the following medical conversation chunk into a concise paragraph. Focus on patient statements, doctor's findings, and any relevant medical details.
                    
                    Conversation:
                    {conversation}
                    
                    Provide the response as a JSON object with a 'summary' field."""}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            if not isinstance(result, dict) or "summary" not in result:
                raise ValueError("Invalid summary format")
                
            # Clear the buffer after successful summarization
            self.utterance_buffer = []
            return result["summary"]
            
        except Exception as e:
            logger.error(f"[LIVE] Error summarizing chunk: {e}")
            return None

    def end_conversation(self, session_id: str) -> Dict:
        """
        End a live conversation and generate final content.
        
        Args:
            session_id (str): The session ID for this conversation
            
        Returns:
            Dict: Final processing result with status and generated content
        """
        try:
            self.logger.info(f"Ending conversation for session {session_id}")
            
            # Get all recordings for this session
            recordings = Recording.query.filter_by(upload_session_id=session_id).all()
            
            if not recordings:
                raise ValueError(f"No recordings found for session {session_id}")
            
            # Combine all audio chunks
            audio_paths = [r.file_path for r in recordings]
            combined_path = os.path.join(self.upload_dir, f"{session_id}_combined.webm")
            
            combine_audio_chunks(audio_paths, combined_path)
            
            # Transcribe the combined audio
            transcription_result = self.transcription_service.transcribe_audio(combined_path)
            
            if not transcription_result.get('text'):
                raise ValueError("No speech detected in combined audio")
            
            # Generate final SOAP note
            soap_note = self.soap_note_service.generate_soap_note(transcription_result['text'])
            
            return {
                'status': 'success',
                'text': transcription_result['text'],
                'diarized_text': transcription_result['diarized_text'],
                'confidence': transcription_result['meta']['confidence'],
                'soap_note': soap_note
            }
            
        except Exception as e:
            self.logger.error(f"Error ending conversation: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
        finally:
            # Clean up the combined audio file
            if 'combined_path' in locals() and os.path.exists(combined_path):
                try:
                    os.remove(combined_path)
                    self.logger.info(f"Cleaned up combined audio file: {combined_path}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up combined file: {str(e)}")

    def get_conversation_stats(self) -> Dict:
        """
        Get statistics about the current conversation.
        
        Returns:
            Dict: Statistics including duration, utterance count, etc.
        """
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "last_summary_time": self.last_summary_time.isoformat() if self.last_summary_time else None,
            "total_utterances": self.total_utterances,
            "current_buffer_size": len(self.utterance_buffer),
            "total_summaries": len(self.summary_buffer),
            "has_soap_note": self.final_soap_note is not None
        } 