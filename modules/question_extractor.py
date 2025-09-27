import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate

from config.settings import AppConfig
from utils.helpers import clean_text, chunk_text, remove_duplicates

logger = logging.getLogger(__name__)

class QuestionExtractor:
    def __init__(self):
        self.config = AppConfig()
        self.llm = self._setup_llm()
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0
        }

    def _setup_llm(self) -> ChatGroq:
        try:
            return ChatGroq(
                model=self.config.LLM_MODEL,
                groq_api_key=self.config.GROQ_API_KEY,
                temperature=0.3,
                max_tokens=2000
            )
        except Exception as e:
            logger.error(f"Failed to setup LLM: {str(e)}")
            raise

    
    def _create_extraction_prompt(self) -> PromptTemplate:
        template = """
    You are an expert AI assistant specialized in extracting Golden Questions and Expected Responses from web content for chatbot testing purposes.

    Your task is to analyze the provided web content and identify:
    1. Golden Questions: High-value questions that users commonly ask or should ask about the content
    2. Expected Responses: Accurate, helpful answers based on the content provided

    Extract only questions that can be answered directly from the provided content.
    Focus on FAQ-style, how-to, and informational queries.
    Ensure questions are natural and realistic, and responses are concise and accurate.

    Content to analyze:
    {content}

    IMPORTANT: Return ONLY a valid JSON object in this EXACT format (no markdown, no code blocks, no extra text):

    {{"questions": [
        {{
            "question": "Clear, natural question as a user would ask",
            "expected_response": "Comprehensive answer based on the content",
            "confidence": 0.9,
            "category": "general",
            "keywords": ["keyword1", "keyword2", "keyword3"]
        }}
    ]}}

    Extract 5-20 high-quality questions. Return only the JSON object, nothing else.
    """
    
        return PromptTemplate(template=template, input_variables=["content"])

    def _create_refinement_prompt(self) -> PromptTemplate:
        template = """
Review and refine the following extracted questions for chatbot testing. 

Original questions:
{questions}

Improve these questions by:
1. Making them more natural and conversational
2. Ensuring responses are accurate and complete
3. Removing duplicates
4. Improving clarity and specificity
5. Adding relevant categories and keywords

Return the refined questions in the same JSON format, keeping only the best 10-15 questions.
"""
        return PromptTemplate(template=template, input_variables=["questions"])

   
    
    def _extract_from_chunk(self, content_chunk: str, url: str) -> List[Dict[str, Any]]:
        try:
            cleaned_chunk = content_chunk.strip()
            if len(cleaned_chunk) < 50:
                return []

            # Additional validation for chunk content
            problematic_patterns = [
                '"questions"', 
                'json', 
                chr(96) + chr(96) + chr(96),  # Three backtick characters
                '<script'
            ]
            
            if any(pattern in cleaned_chunk.lower() for pattern in problematic_patterns):
                logger.debug(f"Skipping chunk with problematic content from {url}")
                return []

            prompt = self._create_extraction_prompt()
            formatted_prompt = prompt.format(content=cleaned_chunk)
            
            response = self.llm.invoke([
                SystemMessage(content="You are an expert question extractor for chatbot training."),
                HumanMessage(content=formatted_prompt)
            ])

            response_text = response.content.strip()
            logger.debug(f"Raw LLM response: {response_text[:200]}...")

            # Enhanced JSON parsing with better error handling
            try:
                # First try standard JSON parsing
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError:
                try:
                    # Clean up common JSON formatting issues
                    json_text = response_text
                    
                    # Remove markdown code blocks
                    backticks = chr(96) + chr(96) + chr(96)
                    json_pattern = backticks + r'(?:json)?\s*(\{.*?\})\s*' + backticks
                    json_match = re.search(json_pattern, json_text, re.DOTALL | re.IGNORECASE)
                    if json_match:
                        json_text = json_match.group(1)
                    
                    # Fix common JSON formatting issues
                    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)  # Remove trailing commas
                    json_text = re.sub(r'(\w)"(\w)', r'\1"\2', json_text)  # Fix quote issues
                    json_text = re.sub(r'\n\s*"questions"', '"questions"', json_text)  # Fix malformed questions key
                    
                    # Try parsing again
                    parsed_data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing failed for chunk from {url}: {e}")
                    logger.error(f"Problematic JSON content: {response_text[:500]}")
                    return []

            # Handle different possible response structures
            questions = []
            
            # Check for standard "questions" key
            if "questions" in parsed_data:
                questions = parsed_data["questions"]
            # Check for malformed keys (with newlines/spaces)
            else:
                # Look for any key that contains "questions"
                for key in parsed_data.keys():
                    if "questions" in key.lower().strip():
                        questions = parsed_data[key]
                        break
                
                # If still no questions found, check if the entire response is a list
                if not questions and isinstance(parsed_data, list):
                    questions = parsed_data

            # Ensure questions is a list
            if not isinstance(questions, list):
                logger.warning(f"Expected list of questions, got {type(questions)}")
                return []

            # Add metadata to each question
            valid_questions = []
            for q in questions:
                if isinstance(q, dict) and q.get("question") and q.get("expected_response"):
                    q.update({
                        "source_url": url,
                        "extracted_at": datetime.now().isoformat(),
                        "extraction_method": "llm_chunk"
                    })
                    q.setdefault("confidence", 0.8)
                    q.setdefault("category", "general") 
                    q.setdefault("keywords", [])
                    valid_questions.append(q)

            logger.info(f"Extracted {len(valid_questions)} valid questions from content chunk at {url}")
            return valid_questions

        except Exception as e:
            logger.error(f"Error extracting questions from chunk at {url}: {repr(e)}")
            logger.error(f"Chunk content preview: {content_chunk[:200]}...")
            return []


    
    def _refine_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not questions:
            return []
        try:
            # Build and send refinement prompt
            questions_json = json.dumps({"questions": questions}, indent=2)
            formatted = self._create_refinement_prompt().format(questions=questions_json)
            response = self.llm.invoke([
                SystemMessage(content="You are an expert at refining chatbot training questions."),
                HumanMessage(content=formatted)
            ])
            text = response.content.strip()
            if not text:
                logger.warning("Empty refinement response; using original questions")
                return questions

            # Extract potential code block JSON
            backticks = chr(96)*3
            m = re.search(rf"{backticks}(?:json)?\s*(\{{.*?\}})\s*{backticks}", text, re.DOTALL|re.IGNORECASE)
            json_text = m.group(1) if m else text
            json_text = re.sub(r',\s*([}\]])', r'\1', json_text)

            parsed = json.loads(json_text)
            return parsed.get("questions", questions)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed in refinement: {e}; using original")
            return questions
        except Exception as e:
            logger.error(f"Unexpected error in refinement: {e}; using original")
            return questions
   
    def _refine_all_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Refine questions in batches of 10 to avoid token limits.
        """
        refined = []
        for i in range(0, len(questions), 10):
            batch = questions[i : i + 10]
            refined.extend(self._refine_questions(batch))
        return refined
    



    def _post_process_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed = []
        for q in questions:
            if not q.get("question") or not q.get("expected_response"):
                continue
            question_text = clean_text(q["question"].strip())
            response_text = clean_text(q["expected_response"].strip())
            if len(question_text) < self.config.MIN_QUESTION_LENGTH:
                continue
            if not question_text.endswith("?"):
                question_text += "?"
            confidence = float(q.get("confidence", 0.5))
            if confidence < self.config.QUESTION_CONFIDENCE_THRESHOLD:
                continue
            processed.append({
                "question": question_text,
                "expected_response": response_text,
                "confidence": confidence,
                "category": q.get("category", "general"),
                "keywords": q.get("keywords", []),
                "source_url": q.get("source_url", ""),
                "extracted_at": q.get("extracted_at", datetime.now().isoformat()),
                "char_count": len(question_text),
                "word_count": len(question_text.split()),
                "response_length": len(response_text)
            })

        unique_questions = remove_duplicates(
            processed,
            key_func=lambda x: x["question"].lower(),
            similarity_threshold=0.85
        )
        unique_questions.sort(key=lambda x: x["confidence"], reverse=True)
        return unique_questions[:self.config.MAX_QUESTIONS_PER_PAGE]

    
   
    
    def extract_questions_and_responses(self, content: str, url: str) -> List[Dict[str, Any]]:
        self.extraction_stats["total_extractions"] += 1
        try:
            logger.info(f"Starting question extraction for URL: {url}")
            if not content or len(content.strip()) < 100:
                logger.warning("Content too short for extraction")
                return []

            cleaned_content = clean_text(content)

            max_length = 100_000
            if len(cleaned_content) > max_length:
                logger.warning(f"Content too large ({len(cleaned_content)} chars), truncating for extraction")
                cleaned_content = cleaned_content[:max_length]

            if len(cleaned_content) > self.config.CHUNK_SIZE * 2:
                chunks = chunk_text(cleaned_content, self.config.CHUNK_SIZE, self.config.CHUNK_OVERLAP)
            else:
                chunks = [cleaned_content]

            # Enhanced chunk filtering to remove problematic content
            def is_valid_extraction_chunk(chunk_text):
                chunk_lower = chunk_text.lower().strip()
                
                # Filter out chunks that are too short
                if len(chunk_text.strip()) < 100:
                    return False
                
                # Filter out chunks containing JSON artifacts
                problematic_patterns = [
                    '"questions"',
                    '{"questions"',
                    '}\n{',
                    'json',
                    '```',
                    '```',
                    '</script>',
                    '<script',
                    'window.',
                    'document.',
                    'function(',
                    'var ',
                    'const ',
                    'let '
                ]
                
                for pattern in problematic_patterns:
                    if pattern in chunk_lower:
                        return False
                        
                return True

            # Apply strict filtering
            valid_chunks = [chunk for chunk in chunks if is_valid_extraction_chunk(chunk)]
            
            MAX_CHUNKS = 20  # Further reduced for memory safety
            if len(valid_chunks) > MAX_CHUNKS:
                valid_chunks = valid_chunks[:MAX_CHUNKS]

            logger.info(f"Processing {len(valid_chunks)} valid chunks out of {len(chunks)} total chunks")

            all_questions = []
            for i, chunk in enumerate(valid_chunks):
                try:
                    chunk_questions = self._extract_from_chunk(chunk, url)
                    all_questions.extend(chunk_questions)
                    logger.debug(f"Extracted {len(chunk_questions)} questions from chunk {i+1}")
                except Exception as e:
                    logger.error(f"Error extracting questions from chunk {i+1} at {url}: {repr(e)}")
                    continue

            if all_questions:
                refined = self._refine_questions(all_questions)
                final_questions = self._post_process_questions(refined)
            else:
                final_questions = []

            if final_questions:
                self.extraction_stats["successful_extractions"] += 1
            else:
                self.extraction_stats["failed_extractions"] += 1

            logger.info(f"Extraction completed: {len(final_questions)} questions from {url}")
            return final_questions

        except Exception as e:
            logger.error(f"Error in extraction for {url}: {repr(e)}", exc_info=True)
            return []
