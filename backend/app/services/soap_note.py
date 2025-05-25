import os
import logging
import openai
import json
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# --- Configuration Constants ---
MAX_CHUNK_UTTERANCES = 40  # Maximum number of utterances per chunk to fit within context window
OPENAI_MODEL_CHUNK_SUMMARIZATION = "gpt-4o"
OPENAI_MODEL_SOAP_GENERATION = "gpt-4o"
SUMMARIZATION_MAX_TOKENS = 500
SOAP_NOTE_MAX_TOKENS = 1000
TEMPERATURE_SUMMARIZATION = 0.3
TEMPERATURE_SOAP_NOTE = 0.3

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
        openai.api_key = self.api_key
        logger.info("SOAPNoteService initialized successfully.")

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
        
        conversation = "\n".join([
            f"{utterance.get('speaker', 'Unknown')}: {utterance.get('text', '')}"
            for utterance in chunk
        ])
        logger.debug(f"[SOAP] Formatted conversation chunk for summarization:\n{conversation}")
        
        try:
            response = openai.ChatCompletion.create(
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
            
            logger.info(f"[SOAP] Received response from OpenAI for chunk summarization.")
            response_content = response.choices[0].message.content
            logger.debug(f"[SOAP] Raw response content for chunk: {response_content}")
            
            result = json.loads(response_content)
            if not isinstance(result, dict) or "summary" not in result:
                raise ValueError("JSON response missing 'summary' field or not a dictionary.")
            
            logger.info(f"[SOAP] Successfully parsed JSON response for chunk summary.")
            logger.debug(f"[SOAP] Parsed chunk summary: {result['summary']}")
            return result["summary"]
        except openai.error.OpenAIError as e:
            logger.error(f"[SOAP] OpenAI API error during chunk summarization: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"[SOAP] JSON decoding error from OpenAI chunk summary response: {e}. Raw response: {response_content}")
            raise ValueError(f"Failed to decode JSON from OpenAI response: {e}")
        except Exception as e:
            logger.error(f"[SOAP] Unexpected error during chunk summarization: {e}")
            raise

    def _parse_soap_note(self, text: str) -> Dict:
        """
        Parses the SOAP note text into a structured dictionary.
        Prioritizes JSON parsing, then falls back to heuristic text extraction.

        Args:
            text: The raw string content of the SOAP note.

        Returns:
            A dictionary with 'subjective', 'objective', 'assessment', and 'plan' keys.
        """
        if not text:
            logger.warning("[SOAP] Attempted to parse empty SOAP note text. Returning empty structure.")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }

        try:
            # Attempt to parse as JSON first (preferred output format)
            parsed_json = json.loads(text)
            # Basic validation for JSON structure
            expected_keys = {"subjective", "objective", "assessment", "plan"}
            if expected_keys.issubset(parsed_json.keys()):
                logger.info("[SOAP] Successfully parsed SOAP note as JSON.")
                return parsed_json
            else:
                logger.warning(f"[SOAP] JSON parsed but missing expected keys. Falling back to text extraction. Keys found: {parsed_json.keys()}")
                # If JSON is valid but not the expected structure, still try heuristic parsing
                return self._heuristic_parse_soap_note_text(text)
        except json.JSONDecodeError:
            logger.warning("[SOAP] SOAP note text is not valid JSON. Attempting heuristic text extraction.")
            # Fallback to heuristic text extraction if not valid JSON
            return self._heuristic_parse_soap_note_text(text)
        except Exception as e:
            logger.error(f"[SOAP] Unexpected error during SOAP note parsing: {e}. Attempting heuristic text extraction.")
            return self._heuristic_parse_soap_note_text(text)

    def _heuristic_parse_soap_note_text(self, text: str) -> Dict:
        """
        Heuristically parses SOAP note sections from plain text.
        This is a fallback method if JSON parsing fails.
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
        
        # Clean up sections by stripping leading/trailing whitespace and extra newlines
        for key in sections:
            sections[key] = sections[key].strip()
        
        logger.info("[SOAP] Successfully performed heuristic parsing of SOAP note text.")
        return sections

    def generate_soap_note(self, diarized_text: List[Dict]) -> Tuple[Dict, List[Tuple[List[Dict], str]]]:
        """
        Generates a SOAP note from diarized transcription using hierarchical summarization.
        This process involves:
        1. Chunking the conversation into smaller, manageable segments.
        2. Summarizing each chunk using an LLM.
        3. Aggregating the chunk summaries.
        4. Generating the final SOAP note from the aggregated summary using an LLM.

        Args:
            diarized_text: A list of dictionaries, each representing an utterance
                           with 'speaker' and 'text' keys.

        Returns:
            A tuple containing:
            - A dictionary representing the structured SOAP note (subjective, objective, assessment, plan).
            - A list of tuples, where each tuple contains (original_chunk, chunk_summary_string).

        Raises:
            ValueError: If input diarized_text is empty or if any critical API call or parsing fails.
        """
        logger.info("[SOAP] Starting hierarchical SOAP note generation process.")
        
        if not diarized_text:
            logger.error("[SOAP] Input 'diarized_text' is empty. Cannot generate SOAP note.")
            raise ValueError("Input 'diarized_text' cannot be empty.")
        
        logger.debug(f"[SOAP] Input diarized_text length: {len(diarized_text)}")
        
        # 1. Chunk the conversation
        chunks = self._chunk_diarized_text(diarized_text)
        if not chunks:
            logger.warning("[SOAP] No chunks generated from diarized text. Returning empty SOAP note.")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }, []
        
        # 2. Summarize each chunk
        chunk_summaries_data = []
        for idx, chunk in enumerate(chunks):
            try:
                summary = self._summarize_chunk(chunk)
                chunk_summaries_data.append((chunk, summary))
            except Exception as e:
                logger.error(f"[SOAP] Failed to summarize chunk {idx+1}. Error: {e}. Skipping this chunk summary.")
                # Optionally, you could append an empty summary or a placeholder
                chunk_summaries_data.append((chunk, f"Error summarizing chunk: {e}")) 
        
        # Guardrail: Check if any summaries were successfully generated
        if not chunk_summaries_data or all(s == "" for _, s in chunk_summaries_data):
            logger.warning("[SOAP] No valid chunk summaries were generated. Cannot proceed with SOAP note generation.")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }, chunk_summaries_data

        # 3. Aggregate summaries
        aggregated_summary = "\n\n".join([summary for _, summary in chunk_summaries_data if summary]) # Only join non-empty summaries
        if not aggregated_summary.strip():
            logger.warning("[SOAP] Aggregated summary is empty after filtering. Cannot generate SOAP note.")
            return { "subjective": "", "objective": "", "assessment": "", "plan": "" }, chunk_summaries_data

        logger.info("[SOAP] Aggregated all valid chunk summaries.")
        logger.debug(f"[SOAP] Aggregated summary for final SOAP note generation:\n{aggregated_summary}")
        
        # 4. Generate final SOAP note
        logger.info("[SOAP] Generating final SOAP note from aggregated summary.")
        try:
            response = openai.ChatCompletion.create(
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
            
            logger.info("[SOAP] Received response from OpenAI for final SOAP note generation.")
            soap_note_response_content = response.choices[0].message.content
            logger.debug(f"[SOAP] Raw SOAP note response content: {soap_note_response_content}")
            
            # Use the robust parsing method
            soap_note = self._parse_soap_note(soap_note_response_content)
            
            # Guardrail: Ensure all expected keys are present after parsing
            expected_keys = {"subjective", "objective", "assessment", "plan"}
            if not expected_keys.issubset(soap_note.keys()):
                logger.error(f"[SOAP] Final SOAP note parsing resulted in missing expected keys. Keys found: {soap_note.keys()}")
                # Attempt to fill missing keys with empty strings to prevent downstream errors
                for key in expected_keys:
                    if key not in soap_note:
                        soap_note[key] = ""
            
            logger.info("[SOAP] Final SOAP note successfully generated and parsed.")
            logger.debug(f"[SOAP] Final SOAP note data: {soap_note}")
            return soap_note, chunk_summaries_data
            
        except openai.error.OpenAIError as e:
            logger.error(f"[SOAP] OpenAI API error during final SOAP note generation: {e}")
            raise
        except Exception as e:
            logger.error(f"[SOAP] Unexpected error during final SOAP note generation or parsing: {e}")
            raise