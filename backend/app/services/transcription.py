import os
import asyncio
from deepgram import Deepgram
from typing import Dict, List, Tuple
import json
from app.utils.logger import service_logger

class TranscriptionService:
    def __init__(self):
        self.api_key = os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
        self.client = Deepgram(self.api_key)
        self.logger = service_logger

    def _map_speaker_to_role(self, speaker_id: int) -> str:
        """Map speaker ID to a simple Speaker 1 or Speaker 2 label."""
        return f"Speaker {speaker_id + 1}"

    def transcribe_audio(self, audio_path: str) -> dict:
        """
        Transcribe an audio file using Deepgram with speaker diarization.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            dict: Transcription result with text, diarized utterances, and metadata
        """
        try:
            self.logger.info(f"Starting transcription for file: {audio_path}")
            
            # Check if file exists and has content
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                raise ValueError(f"Audio file is empty: {audio_path}")
            
            self.logger.info(f"File size: {file_size} bytes")
            
            with open(audio_path, 'rb') as audio:
                source = {'buffer': audio, 'mimetype': 'audio/mp3'}
                options = {
                    'smart_format': True,
                    'model': 'nova-2',
                    'language': 'en-US',
                    'punctuate': True,
                    'diarize': True,
                    'utterances': True,
                    'diarize_version': '2',
                    'vad_turnoff': 500,
                    'vad_events': True,
                    'filler_words': False,
                    'profanity_filter': False
                }
                
                # Run the async transcription in a synchronous context
                response = asyncio.run(self.client.transcription.prerecorded(source, options))
                
            self.logger.info(f"Successfully transcribed file: {audio_path}")
            self.logger.info(f"Response metadata: {response.get('metadata', {})}")
            self.logger.info(f"Response results: {response.get('results', {})}")
            
            # Process diarized utterances
            utterances = response.get('results', {}).get('utterances', [])
            diarized_text = []
            
            if utterances:
                for utterance in utterances:
                    speaker_id = utterance.get('speaker', 0)
                    role = self._map_speaker_to_role(speaker_id)
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
            
            # Get the full transcript even if no diarization
            full_text = ""
            if 'results' in response and 'channels' in response['results']:
                channel = response['results']['channels'][0]
                if 'alternatives' in channel and channel['alternatives']:
                    full_text = channel['alternatives'][0].get('transcript', '').strip()
            
            # If no text was transcribed, raise an error
            if not full_text and not diarized_text:
                self.logger.warning(f"No text transcribed from file: {audio_path}")
                self.logger.info(f"Response metadata: {response.get('metadata', {})}")
                self.logger.info(f"Response results: {response.get('results', {})}")
                raise ValueError("No speech detected in audio file")
            
            return {
                'text': full_text,
                'words': response.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('words', []),
                'diarized_text': diarized_text,
                'meta': {
                    'duration': response.get('metadata', {}).get('duration', 0),
                    'channels': response.get('metadata', {}).get('channels', 1),
                    'confidence': response.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('confidence', 0),
                    'speakers': len(set(utterance.get('speaker', 0) for utterance in utterances))
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error transcribing file {audio_path}: {str(e)}")
            raise 