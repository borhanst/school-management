"""
AI Question Generation Service using Google Gemini and Groq (Llama).

Generates MCQ, Creative, and Short Answer questions from uploaded textbook images
following the Bangladesh education system pattern.
"""

import base64
import json
import logging
import mimetypes

from django.conf import settings
from google import genai
from google.genai import types
from groq import Groq

from questions.models import AIGenerationRequest, Question, QuestionOption

logger = logging.getLogger(__name__)


# Bangladesh Education Pattern - Question Structure
# MCQ: 1 mark each, 4 options (A, B, C, D)
# Creative (CQ): 10 marks each, Bloom's taxonomy based
# Short Answer: 2-3 marks each

BLOOM_LEVELS_CQ = [
    "knowledge",  # জ্ঞানমূলক (Know/Remember)
    "comprehension",  # অনুধাবনমূলক (Understand)
    "application",  # প্রয়োগমূলক (Apply)
    "analysis",  # বিশ্লেষণমূলক (Analyze)
]

PROMPT_TEMPLATE = """You are an expert educator in the Bangladesh education system (NCTB curriculum).
Analyze the uploaded textbook page image and generate questions based on the content.

**CONTEXT:**
- Class: {class_level}
- Subject: {subject}
- Topic/Chapter: {topic}
- Language: {language}

**GENERATION REQUIREMENTS:**
1. MCQ Questions ({num_mcq} questions):
   - 1 mark each
   - 4 options: A, B, C, D
   - Clearly mark the correct answer
   - Based directly on textbook content
   - Generate in: {language}

2. Creative Questions (CQ) ({num_creative} questions):
   - 10 marks each (typically split as a=1, b=1, c=3, d=5)
   - Follow Bloom's Taxonomy: Knowledge, Comprehension, Application, Analysis
   - Each CQ should have parts (a, b, c, d)
   - Generate in: {language}

3. Short Answer Questions ({num_short} questions):
   - 2-3 marks each
   - Require brief explanations (3-5 sentences)
   - Generate in: {language}

**OUTPUT FORMAT:**
Return ONLY valid JSON in this exact structure (no markdown, no explanation):
{{
  "mcq": [
    {{
      "question_text": "Question text in the specified language",
      "options": [
        {{"label": "A", "text": "Option A in the same language", "is_correct": true}},
        {{"label": "B", "text": "Option B in the same language", "is_correct": false}},
        {{"label": "C", "text": "Option C in the same language", "is_correct": false}},
        {{"label": "D", "text": "Option D in the same language", "is_correct": false}}
      ],
      "answer_explanation": "Explanation in the same language",
      "difficulty": "easy|medium|hard"
    }}
  ],
  "creative": [
    {{
      "question_text": "Stem text in the specified language",
      "parts": [
        {{"label": "a", "text": "What is...?", "bloom": "knowledge", "marks": 1}},
        {{"label": "b", "text": "Explain...", "bloom": "comprehension", "marks": 1}},
        {{"label": "c", "text": "Apply...", "bloom": "application", "marks": 3}},
        {{"label": "d", "text": "Analyze...", "bloom": "analysis", "marks": 5}}
      ],
      "difficulty": "medium"
    }}
  ],
  "short_answer": [
    {{
      "question_text": "Short question in the specified language",
      "answer_explanation": "Brief answer in the same language",
      "difficulty": "easy|medium|hard",
      "marks": 2
    }}
  ]
}}

**IMPORTANT:**
- Questions MUST be based on the uploaded image content
- Generate ALL content in the specified language: {language}
- Do NOT create bilingual versions - use only the specified language
- Maintain class-appropriate difficulty
- Follow NCTB curriculum standards
- Return ONLY the JSON, no additional text
"""


class GeminiQuestionGenerator:
    """Generates questions from textbook images using Google Gemini."""

    def __init__(self, model_name=None):
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured in Django settings"
            )
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name or getattr(
            settings, "GEMINI_MODEL", "gemini-pro-latest"
        )

    def _build_prompt(
        self,
        class_level: str,
        subject: str,
        topic: str,
        num_mcq: int,
        num_creative: int,
        num_short_answer: int,
        language: str = "english",
        additional_prompt: str = "",
    ) -> str:
        """Build the prompt for AI generation."""
        language_display = {
            "english": "English",
            "bengali": "Bengali (বাংলা)",
        }
        lang = language_display.get(language, "English")

        prompt = PROMPT_TEMPLATE.format(
            class_level=class_level,
            subject=subject,
            topic=topic or "General",
            num_mcq=num_mcq,
            num_creative=num_creative,
            num_short=num_short_answer,
            language=lang,
        )

        if additional_prompt:
            prompt += f"\n\n**ADDITIONAL INSTRUCTIONS:**\n{additional_prompt}"

        return prompt

    def _parse_response(self, response_text: str) -> dict:
        """Parse the AI response JSON."""
        # Clean up response - remove markdown code blocks if present
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        return json.loads(cleaned)

    def generate_questions(
        self,
        generation_request: AIGenerationRequest,
    ) -> dict:
        """
        Generate questions from the uploaded textbook image.

        Returns:
            dict with 'success' (bool), 'data' (parsed JSON), 'error' (str)
        """
        try:
            # Build prompt
            prompt = self._build_prompt(
                class_level=str(generation_request.class_level),
                subject=str(generation_request.subject),
                topic=generation_request.additional_prompt or "",
                num_mcq=generation_request.num_mcq,
                num_creative=generation_request.num_creative,
                num_short_answer=generation_request.num_short_answer,
                language=generation_request.language,
                additional_prompt=generation_request.additional_prompt,
            )

            # Update request with prompt
            generation_request.prompt_used = prompt
            generation_request.status = "processing"
            generation_request.save(update_fields=["prompt_used", "status"])

            # Read uploaded image
            image_file = generation_request.uploaded_image
            image_data = image_file.read()
            
            # Determine MIME type from file extension
            import mimetypes
            filename = image_file.name.lower()
            if filename.endswith('.png'):
                mime_type = 'image/png'
            elif filename.endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif filename.endswith('.webp'):
                mime_type = 'image/webp'
            elif filename.endswith('.gif'):
                mime_type = 'image/gif'
            else:
                # Try to detect from file content or default to PNG
                mime_type = mimetypes.guess_type(image_file.name)[0] or 'image/png'

            # Prepare content for Gemini
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=image_data,
                            mime_type=mime_type,
                        ),
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]

            # Configure generation
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level="HIGH",
                ),
                response_mime_type="text/plain",
            )

            # Stream the response and collect chunks
            response_text = []
            for chunk in self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=generate_content_config,
            ):
                if text := chunk.text:
                    response_text.append(text)
                    logger.debug(f"Received chunk: {len(text)} characters")

            # Join all chunks
            full_response = "".join(response_text)

            # Store raw response
            generation_request.ai_response_raw = {"response": full_response}

            # Parse response
            parsed_data = self._parse_response(full_response)
            generation_request.status = "completed"

            from django.utils import timezone

            generation_request.completed_at = timezone.now()
            generation_request.save(
                update_fields=["ai_response_raw", "status", "completed_at"]
            )

            return {"success": True, "data": parsed_data}

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse AI response as JSON: {str(e)}"
            generation_request.status = "failed"
            generation_request.error_message = error_msg
            generation_request.save(update_fields=["status", "error_message"])
            logger.error(f"AI Generation JSON Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "raw_response": full_response
                if "full_response" in locals()
                else "",
            }

        except Exception as e:
            error_msg = f"AI Generation failed: {str(e)}"
            generation_request.status = "failed"
            generation_request.error_message = error_msg
            generation_request.save(update_fields=["status", "error_message"])
            logger.error(f"AI Generation Error: {error_msg}")
            return {"success": False, "error": error_msg}


class GroqQuestionGenerator:
    """Generates questions from textbook images using Groq (Llama)."""

    # Supported vision-capable models on Groq
    DEFAULT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

    def __init__(self, model_name=None):
        api_key = getattr(settings, "GROQ_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured in Django settings"
            )
        self.client = Groq(api_key=api_key)
        self.model_name = model_name or getattr(
            settings, "GROQ_MODEL", self.DEFAULT_MODEL
        )

    def _build_prompt(
        self,
        class_level: str,
        subject: str,
        topic: str,
        num_mcq: int,
        num_creative: int,
        num_short_answer: int,
        language: str = "english",
        additional_prompt: str = "",
    ) -> str:
        """Build the prompt for AI generation."""
        language_display = {
            "english": "English",
            "bengali": "Bengali (বাংলা)",
        }
        lang = language_display.get(language, "English")

        prompt = PROMPT_TEMPLATE.format(
            class_level=class_level,
            subject=subject,
            topic=topic or "General",
            num_mcq=num_mcq,
            num_creative=num_creative,
            num_short=num_short_answer,
            language=lang,
        )

        if additional_prompt:
            prompt += f"\n\n**ADDITIONAL INSTRUCTIONS:**\n{additional_prompt}"

        return prompt

    def _parse_response(self, response_text: str) -> dict:
        """Parse the AI response JSON."""
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        return json.loads(cleaned)

    def _encode_image(self, image_file) -> tuple[str, str]:
        """
        Encode uploaded image to base64 and return (base64_string, mime_type).
        """
        image_data = image_file.read()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Determine MIME type from file extension
        filename = image_file.name.lower()
        if filename.endswith(".png"):
            mime_type = "image/png"
        elif filename.endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"
        elif filename.endswith(".webp"):
            mime_type = "image/webp"
        elif filename.endswith(".gif"):
            mime_type = "image/gif"
        else:
            mime_type = mimetypes.guess_type(image_file.name)[0] or "image/png"

        return base64_image, mime_type

    def generate_questions(
        self,
        generation_request: AIGenerationRequest,
    ) -> dict:
        """
        Generate questions from the uploaded textbook image using Groq/Llama.

        Returns:
            dict with 'success' (bool), 'data' (parsed JSON), 'error' (str)
        """
        try:
            # Build prompt
            prompt = self._build_prompt(
                class_level=str(generation_request.class_level),
                subject=str(generation_request.subject),
                topic=generation_request.additional_prompt or "",
                num_mcq=generation_request.num_mcq,
                num_creative=generation_request.num_creative,
                num_short_answer=generation_request.num_short_answer,
                language=generation_request.language,
                additional_prompt=generation_request.additional_prompt,
            )

            # Update request with prompt
            generation_request.prompt_used = prompt
            generation_request.status = "processing"
            generation_request.save(update_fields=["prompt_used", "status"])

            # Encode image
            base64_image, mime_type = self._encode_image(
                generation_request.uploaded_image
            )

            # Prepare messages for Groq
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ]

            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
            )

            # Extract response
            full_response = chat_completion.choices[0].message.content

            # Store raw response
            generation_request.ai_response_raw = {"response": full_response}

            # Parse response
            parsed_data = self._parse_response(full_response)
            generation_request.status = "completed"

            from django.utils import timezone

            generation_request.completed_at = timezone.now()
            generation_request.save(
                update_fields=["ai_response_raw", "status", "completed_at"]
            )

            return {"success": True, "data": parsed_data}

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse AI response as JSON: {str(e)}"
            generation_request.status = "failed"
            generation_request.error_message = error_msg
            generation_request.save(update_fields=["status", "error_message"])
            logger.error(f"AI Generation JSON Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "raw_response": full_response
                if "full_response" in locals()
                else "",
            }

        except Exception as e:
            error_msg = f"AI Generation failed: {str(e)}"
            generation_request.status = "failed"
            generation_request.error_message = error_msg
            generation_request.save(update_fields=["status", "error_message"])
            logger.error(f"AI Generation Error: {error_msg}")
            return {"success": False, "error": error_msg}


def create_questions_from_generation_result(
    generation_request: AIGenerationRequest,
    question_bank=None,
    question_paper=None,
    parsed_data: dict = None,
    created_by=None,
) -> dict:
    """
    Create Question and QuestionOption objects from parsed AI data.

    Args:
        generation_request: The AIGenerationRequest instance
        question_bank: The QuestionBank to add questions to (optional if question_paper provided)
        question_paper: The QuestionPaper to add questions to (optional)
        parsed_data: Parsed JSON from AI
        created_by: User who created the questions

    Returns:
        dict with counts of created questions by type
    """
    if parsed_data is None:
        parsed_data = {}
        
    created_counts = {"mcq": 0, "creative": 0, "short_answer": 0}

    # If paper specified but no bank, get or create bank from paper
    if question_paper and not question_bank:
        question_bank = question_paper.get_or_create_bank()

    # Create MCQ questions
    for mcq_data in parsed_data.get("mcq", []):
        question = Question.objects.create(
            question_bank=question_bank,
            question_paper=question_paper,
            question_text=mcq_data.get("question_text", ""),
            question_type="mcq",
            difficulty=mcq_data.get("difficulty", "medium"),
            marks=1,
            answer_explanation=mcq_data.get("answer_explanation", ""),
            ai_generated=True,
            generation_request=generation_request,
            created_by=created_by,
            is_approved=False,
        )

        # Create options
        for option_data in mcq_data.get("options", []):
            QuestionOption.objects.create(
                question=question,
                option_text=option_data.get("text", ""),
                label=option_data.get("label", ""),
                is_correct=option_data.get("is_correct", False),
            )

        # If paper specified, also add to paper questions
        if question_paper:
            from django.db import models
            max_order = question_paper.paper_questions.aggregate(
                max_order=models.Max("order")
            )["max_order"] or 0
            
            from questions.models import QuestionPaperQuestion
            QuestionPaperQuestion.objects.create(
                question_paper=question_paper,
                question=question,
                order=max_order + 1,
                marks=1,
            )

        created_counts["mcq"] += 1

    # Create Creative questions
    for cq_data in parsed_data.get("creative", []):
        # For creative questions, combine parts into question_text
        parts = cq_data.get("parts", [])
        parts_text = "\n".join(
            [f"({p.get('label', '')}) {p.get('text', '')}" for p in parts]
        )

        question = Question.objects.create(
            question_bank=question_bank,
            question_paper=question_paper,
            question_text=f"{cq_data.get('question_text', '')}\n\n{parts_text}",
            question_type="creative",
            difficulty=cq_data.get("difficulty", "medium"),
            bloom_level=parts[0].get("bloom", "knowledge")
            if parts
            else "knowledge",
            marks=10,  # Standard for creative questions
            ai_generated=True,
            generation_request=generation_request,
            created_by=created_by,
            is_approved=False,
        )

        # If paper specified, also add to paper questions
        if question_paper:
            from django.db import models
            max_order = question_paper.paper_questions.aggregate(
                max_order=models.Max("order")
            )["max_order"] or 0
            
            from questions.models import QuestionPaperQuestion
            QuestionPaperQuestion.objects.create(
                question_paper=question_paper,
                question=question,
                order=max_order + 1,
                marks=10,
            )

        created_counts["creative"] += 1

    # Create Short Answer questions
    for sa_data in parsed_data.get("short_answer", []):
        question = Question.objects.create(
            question_bank=question_bank,
            question_paper=question_paper,
            question_text=sa_data.get("question_text", ""),
            question_type="short_answer",
            difficulty=sa_data.get("difficulty", "medium"),
            marks=sa_data.get("marks", 2),
            answer_explanation=sa_data.get("answer_explanation", ""),
            ai_generated=True,
            generation_request=generation_request,
            created_by=created_by,
            is_approved=False,
        )

        # If paper specified, also add to paper questions
        if question_paper:
            from django.db import models
            max_order = question_paper.paper_questions.aggregate(
                max_order=models.Max("order")
            )["max_order"] or 0
            
            from questions.models import QuestionPaperQuestion
            QuestionPaperQuestion.objects.create(
                question_paper=question_paper,
                question=question,
                order=max_order + 1,
                marks=sa_data.get("marks", 2),
            )

        created_counts["short_answer"] += 1

    # Recalculate total marks for the paper
    if question_paper:
        question_paper.calculate_total_marks()

    return created_counts
