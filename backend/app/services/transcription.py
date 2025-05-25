import os
import logging
import asyncio
from deepgram import Deepgram
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.api_key = os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
        self.client = Deepgram(self.api_key)

    def _analyze_speaker_patterns(self, utterances: List[Dict]) -> Tuple[int, float]:
        """
        Analyze speaker patterns to determine the most likely doctor.
        Returns (doctor_speaker_id, confidence)
        """
        # Count utterances per speaker
        speaker_counts = {}
        speaker_confidences = {}
        
        for utterance in utterances:
            speaker_id = utterance.get('speaker', 0)
            confidence = utterance.get('speaker_confidence', 0.5)
            
            speaker_counts[speaker_id] = speaker_counts.get(speaker_id, 0) + 1
            speaker_confidences[speaker_id] = speaker_confidences.get(speaker_id, 0) + confidence
        
        # Calculate average confidence per speaker
        for speaker_id in speaker_confidences:
            speaker_confidences[speaker_id] /= speaker_counts[speaker_id]
        
        # The speaker with the most utterances and highest confidence is likely the doctor
        doctor_id = max(speaker_counts.items(), key=lambda x: (x[1], speaker_confidences[x[0]]))[0]
        doctor_confidence = speaker_confidences[doctor_id]
        
        return doctor_id, doctor_confidence

    def _map_speaker_to_role(self, speaker_id: int, doctor_id: int) -> str:
        """Map speaker ID to role based on the identified doctor."""
        return "Doctor" if speaker_id == doctor_id else "Patient"

    def transcribe_audio(self, audio_path: str) -> dict:
        """
        Transcribe an audio file using Deepgram with speaker diarization.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            dict: Transcription result with text, diarized utterances, and metadata
        """
        try:
            logger.info(f"[TRANSCRIPTION] Starting transcription for file: {audio_path}")
            
            with open(audio_path, 'rb') as audio:
                source = {'buffer': audio, 'mimetype': 'audio/mp3'}
                options = {
                    'smart_format': True,
                    'model': 'nova-2',
                    'language': 'en-US',
                    'punctuate': True,
                    'diarize': True,
                    'utterances': True,
                    'diarize_version': '2'  # Use the latest diarization model
                }
                # Run the async transcription in a synchronous context
                response = asyncio.run(self.client.transcription.prerecorded(source, options))
                
            logger.info(f"[TRANSCRIPTION] Successfully transcribed file: {audio_path}")
            
            # Process diarized utterances
            utterances = response.get('results', {}).get('utterances', [])
            diarized_text = []
            
            if utterances:
                # Analyze speaker patterns to identify the doctor
                doctor_id, doctor_confidence = self._analyze_speaker_patterns(utterances)
                logger.info(f"[TRANSCRIPTION] Identified doctor as speaker {doctor_id} with confidence {doctor_confidence:.2f}")
                
                for utterance in utterances:
                    speaker_id = utterance.get('speaker', 0)
                    role = self._map_speaker_to_role(speaker_id, doctor_id)
                    text = utterance.get('transcript', '').strip()
                    if text:
                        diarized_text.append({
                            'speaker': role,
                            'text': text,
                            'start': utterance.get('start', 0),
                            'end': utterance.get('end', 0),
                            'confidence': utterance.get('confidence', 0),
                            'speaker_confidence': utterance.get('speaker_confidence', 0)
                        })
            
            return {
                'text': response['results']['channels'][0]['alternatives'][0]['transcript'],
                'words': response['results']['channels'][0]['alternatives'][0]['words'],
                'diarized_text': diarized_text,
                'meta': {
                    'duration': response['metadata']['duration'],
                    'channels': response['metadata']['channels'],
                    'confidence': response['results']['channels'][0]['alternatives'][0]['confidence'],
                    'speakers': len(set(utterance.get('speaker', 0) for utterance in utterances)),
                    'doctor_confidence': doctor_confidence if utterances else 0
                }
            }
            
        except Exception as e:
            logger.error(f"[TRANSCRIPTION] Error transcribing file {audio_path}: {str(e)}")
            raise 