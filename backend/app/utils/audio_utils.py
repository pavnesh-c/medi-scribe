import os
import wave
import logging
import subprocess
from typing import List

logger = logging.getLogger(__name__)

def convert_to_wav(input_path: str, output_path: str) -> None:
    """
    Convert audio file to WAV format using ffmpeg.
    
    Args:
        input_path (str): Path to input audio file
        output_path (str): Path to output WAV file
    """
    try:
        logger.info(f"Converting {input_path} to WAV format")
        cmd = [
            'ffmpeg', '-y',  # Overwrite output file if exists
            '-i', input_path,
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '48000',  # 48kHz sample rate
            '-ac', '1',  # Mono
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
            
        logger.info(f"Successfully converted to WAV: {output_path}")
        
    except Exception as e:
        logger.error(f"Error converting audio to WAV: {str(e)}")
        raise

def combine_audio_chunks(chunk_paths: List[str], output_path: str) -> None:
    """
    Combine multiple audio chunks into a single audio file.
    
    Args:
        chunk_paths (List[str]): List of paths to audio chunk files
        output_path (str): Path where the combined audio file will be saved
    """
    try:
        logger.info(f"Combining {len(chunk_paths)} audio chunks into {output_path}")
        
        # First combine the raw chunks
        temp_combined = f"{output_path}.temp.webm"
        with open(temp_combined, 'wb') as outfile:
            for chunk_path in chunk_paths:
                if not os.path.exists(chunk_path):
                    logger.warning(f"Chunk file not found: {chunk_path}")
                    continue
                    
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
        
        # Convert the combined file to WAV format
        convert_to_wav(temp_combined, output_path)
        
        # Clean up temporary file
        if os.path.exists(temp_combined):
            os.remove(temp_combined)
        
        logger.info(f"Successfully combined and converted audio chunks into {output_path}")
        
    except Exception as e:
        logger.error(f"Error combining audio chunks: {str(e)}")
        # Clean up any temporary files
        if 'temp_combined' in locals() and os.path.exists(temp_combined):
            try:
                os.remove(temp_combined)
            except:
                pass
        raise 