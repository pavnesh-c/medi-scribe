import os
import logging
import json
from typing import Dict, List, Tuple
from openai import OpenAI
from app.utils.logger import service_logger
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = service_logger

# --- Configuration Constants ---
MAX_CHUNK_UTTERANCES = 40  # Maximum number of utterances per chunk to fit within context window
OPENAI_MODEL_CHUNK_SUMMARIZATION = "gpt-4o"
OPENAI_MODEL_SOAP_GENERATION = "gpt-4o"
SUMMARIZATION_MAX_TOKENS = 500
SOAP_NOTE_MAX_TOKENS = 1000
TEMPERATURE_SUMMARIZATION = 0.3
TEMPERATURE_SOAP_NOTE = 0.3
MAX_WORKERS = 4  # Maximum number of parallel workers for chunk processing

class SOAPNoteService:
    def __init__(self):
        """
        Initializes the SOAPNoteService, ensuring the OpenAI API key is set.
        Raises ValueError if the API key is not found.
        """
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable is not set. Please set it before initializing the service.")
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=self.api_key)
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        logger.info("SOAPNoteService initialized successfully.")

    def __del__(self):
        """
        Cleanup resources when the service is destroyed.
        """
        self.executor.shutdown(wait=True)

    def _chunk_diarized_text(self, diarized_text: List[Dict], chunk_size: int = MAX_CHUNK_UTTERANCES) -> List[List[Dict]]:
        """
        Splits diarized text into manageable chunks.

        Args:
            diarized_text: A list of dictionaries, where each dictionary represents
                           an utterance with 'speaker' and 'text' keys.
            chunk_size: The maximum number of utterances per chunk.

        Returns:
            A list of lists of dictionaries, where each inner list is a chunk.
        """
        if not diarized_text:
            logger.warning("[SOAP] Attempted to chunk empty diarized text.")
            return []
        
        logger.info(f"[SOAP] Chunking diarized text of length {len(diarized_text)} into chunks of size {chunk_size}.")
        chunks = [diarized_text[i:i + chunk_size] for i in range(0, len(diarized_text), chunk_size)]
        logger.info(f"[SOAP] Created {len(chunks)} chunks.")
        return chunks

    def _summarize_chunk(self, chunk: List[Dict]) -> str:
        """
        Summarizes a chunk of the conversation using the specified OpenAI model.

        Args:
            chunk: A list of dictionaries, each representing an utterance.

        Returns:
            A concise string summary of the chunk.

        Raises:
            Exception: If the OpenAI API call fails or the JSON response is invalid.
        """
        if not chunk:
            logger.warning("[SOAP] Attempted to summarize an empty chunk. Returning empty string.")
            return ""

        logger.info(f"[SOAP] Starting chunk summarization with {len(chunk)} utterances.")
        
        # Only include speaker and text in the conversation
        conversation = "\n".join([
            f"{utterance.get('speaker', 'Unknown')}: {utterance.get('text', '')}"
            for utterance in chunk
        ])
        
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL_CHUNK_SUMMARIZATION,
                messages=[
                    {"role": "system", "content": """You are an expert medical scribe assistant. Your task is to provide a concise, factual summary of a segment of a medical conversation. 
                    Focus ONLY on extracting key medical information: patient's reported symptoms, historical context, current complaints, physical findings, doctor's observations, and any specific questions or instructions.
                    Do NOT interpret, diagnose, or generate a SOAP note. Just summarize the raw content.
                    Your output MUST be a JSON object with a single key 'summary' containing the summarized text. Ensure the JSON is well-formed."""},
                    {"role": "user", "content": f"""Summarize the following medical conversation chunk into a concise paragraph. Focus on patient statements, doctor's findings, and any relevant medical details.
                    
                    Conversation:
                    {conversation}
                    
                    Provide the response as a JSON object with a 'summary' field. Example: {{"summary": "Patient presented with a cough, sore throat, and reported feeling fatigued for three days..."}}"""}
                ],
                response_format={"type": "json_object"},
                temperature=TEMPERATURE_SUMMARIZATION,
                max_tokens=SUMMARIZATION_MAX_TOKENS
            )
            
            result = json.loads(response.choices[0].message.content)
            if not isinstance(result, dict) or "summary" not in result:
                raise ValueError("JSON response missing 'summary' field or not a dictionary.")
            
            return result["summary"]
        except Exception as e:
            logger.error(f"[SOAP] Unexpected error during chunk summarization: {e}")
            raise

    def _process_chunks_parallel(self, chunks: List[List[Dict]]) -> List[Tuple[List[Dict], str]]:
        """
        Process chunks in parallel using ThreadPoolExecutor.
        """
        chunk_summaries_data = []
        futures = []

        # Submit all chunk summarization tasks
        for chunk in chunks:
            future = self.executor.submit(self._summarize_chunk, chunk)
            futures.append((chunk, future))

        # Process completed tasks as they finish
        for chunk, future in futures:
            try:
                summary = future.result()
                chunk_summaries_data.append((chunk, summary))
            except Exception as e:
                logger.error(f"[SOAP] Failed to summarize chunk: {e}")
                chunk_summaries_data.append((chunk, f"Error summarizing chunk: {str(e)}"))

        return chunk_summaries_data

    def generate_soap_note(self, diarized_text: List[Dict]) -> Tuple[Dict, List[Tuple[List[Dict], str]]]:
        """
        Generates a SOAP note from diarized transcription using hierarchical summarization.
        Uses parallel processing for chunk summarization.
        """
        logger.info("[SOAP] Starting hierarchical SOAP note generation process.")
        
        if not diarized_text:
            logger.error("[SOAP] Input 'diarized_text' is empty. Cannot generate SOAP note.")
            raise ValueError("Input 'diarized_text' cannot be empty.")
        
        # 1. Chunk the conversation
        chunks = self._chunk_diarized_text(diarized_text)
        if not chunks:
            logger.warning("[SOAP] No chunks generated from diarized text. Returning empty SOAP note.")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }, []
        
        # 2. Process chunks in parallel
        try:
            chunk_summaries_data = self._process_chunks_parallel(chunks)
        except Exception as e:
            logger.error(f"[SOAP] Error in parallel chunk processing: {e}")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }, []
        
        # Guardrail: Check if any summaries were successfully generated
        if not chunk_summaries_data or all(s == "" for _, s in chunk_summaries_data):
            logger.warning("[SOAP] No valid chunk summaries were generated. Cannot proceed with SOAP note generation.")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }, chunk_summaries_data

        # 3. Aggregate summaries
        aggregated_summary = "\n\n".join([summary for _, summary in chunk_summaries_data if summary])
        if not aggregated_summary.strip():
            logger.warning("[SOAP] Aggregated summary is empty after filtering. Cannot generate SOAP note.")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }, chunk_summaries_data

        # 4. Generate final SOAP note
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL_SOAP_GENERATION,
                messages=[
                    {"role": "system", "content": """You are a highly skilled medical scribe AI. Your primary function is to transform a provided summary of a medical conversation into a structured and concise SOAP (Subjective, Objective, Assessment, Plan) note.
                    Adhere strictly to the definitions of each section:
                    - **Subjective (S):** Information reported by the patient (symptoms, chief complaint, relevant history, social/family history).
                    - **Objective (O):** Observable and measurable data (physical exam findings, vital signs, lab results, imaging results). Do NOT include patient-reported symptoms here.
                    - **Assessment (A):** The diagnosis or differential diagnoses, and the patient's progress or status.
                    - **Plan (P):** Future actions (medications, referrals, follow-up appointments, patient education, further diagnostics).

                    Your output MUST be a JSON object with 'subjective', 'objective', 'assessment', and 'plan' as keys. Ensure the JSON is valid and well-formed. Do NOT include any introductory or concluding remarks outside the JSON structure. If a section has no relevant information, provide an empty string for that section's value.
                    """},
                    {"role": "user", "content": f"""Create a comprehensive SOAP note from the following summarized medical conversation.
                    
                    Summarized Medical Conversation:
                    {aggregated_summary}
                    
                    Provide the response as a JSON object with the following structure:
                    {{
                        "subjective": "...",
                        "objective": "...",
                        "assessment": "...",
                        "plan": "..."
                    }}"""}
                ],
                response_format={"type": "json_object"},
                temperature=TEMPERATURE_SOAP_NOTE,
                max_tokens=SOAP_NOTE_MAX_TOKENS
            )
            
            soap_note = self._parse_soap_note(response.choices[0].message.content)
            
            # Ensure all expected keys are present
            expected_keys = {"subjective", "objective", "assessment", "plan"}
            for key in expected_keys:
                if key not in soap_note:
                    soap_note[key] = ""
            
            return soap_note, chunk_summaries_data
            
        except Exception as e:
            logger.error(f"[SOAP] Error in final SOAP note generation: {e}")
            raise

    def _parse_soap_note(self, text: str) -> Dict:
        """
        Parses the SOAP note text into a structured dictionary.
        Prioritizes JSON parsing, then falls back to heuristic text extraction.
        """
        if not text:
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }

        try:
            parsed_json = json.loads(text)
            expected_keys = {"subjective", "objective", "assessment", "plan"}
            if expected_keys.issubset(parsed_json.keys()):
                return parsed_json
            return self._heuristic_parse_soap_note_text(text)
        except json.JSONDecodeError:
            return self._heuristic_parse_soap_note_text(text)
        except Exception as e:
            logger.error(f"[SOAP] Error during SOAP note parsing: {e}")
            return self._heuristic_parse_soap_note_text(text)

    def _heuristic_parse_soap_note_text(self, text: str) -> Dict:
        """
        Heuristically parses SOAP note sections from plain text.
        """
        sections = {
            "subjective": "",
            "objective": "",
            "assessment": "",
            "plan": ""
        }
        
        current_section = None
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            lower_line = line.lower()
            if "subjective:" in lower_line or "s:" in lower_line:
                current_section = "subjective"
                sections[current_section] += line.replace("subjective:", "").replace("s:", "").strip() + "\n"
            elif "objective:" in lower_line or "o:" in lower_line:
                current_section = "objective"
                sections[current_section] += line.replace("objective:", "").replace("o:", "").strip() + "\n"
            elif "assessment:" in lower_line or "a:" in lower_line:
                current_section = "assessment"
                sections[current_section] += line.replace("assessment:", "").replace("a:", "").strip() + "\n"
            elif "plan:" in lower_line or "p:" in lower_line:
                current_section = "plan"
                sections[current_section] += line.replace("plan:", "").replace("p:", "").strip() + "\n"
            elif current_section:
                sections[current_section] += line + "\n"
        
        # Clean up sections
        for key in sections:
            sections[key] = sections[key].strip()
        
        return sections