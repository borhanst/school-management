"""
AI Question Generation Service using Google Gemini.

Generates MCQ, Creative, and Short Answer questions from uploaded textbook images
following the Bangladesh education system pattern.
"""

import json
import logging
from typing import Optional

import google.generativeai as genai
from django.conf import settings
from django.core.files.base import ContentFile

from questions.models import AIGenerationRequest, Question, QuestionOption

logger = logging.getLogger(__name__)


# Bangladesh Education Pattern - Question Structure
# MCQ: 1 mark each, 4 options (A, B, C, D)
# Creative (CQ): 10 marks each, Bloom's taxonomy based
# Short Answer: 2-3 marks each

BLOOM_LEVELS_CQ = [
    "knowledge",      # জ্ঞানমূলক (Know/Remember)
    "comprehension",  # অনুধাবনমূলক (Understand)
    "application",    # প্রয়োগমূলক (Apply)
    "analysis",       # বিশ্লেষণমূলক (Analyze)
]

PROMPT_TEMPLATE = """You are an expert educator in the Bangladesh education system (NCTB curriculum). 
Analyze the uploaded textbook page image and generate questions based on the content.

**CONTEXT:**
- Class: {class_level}
- Subject: {subject}
- Topic/Chapter: {topic}

**GENERATION REQUIREMENTS:**
1. MCQ Questions ({num_mcq} questions):
   - 1 mark each
   - 4 options: A, B, C, D
   - Clearly mark the correct answer
   - Based directly on textbook content
   - {language_instruction}

2. Creative Questions (CQ) ({num_creative} questions):
   - 10 marks each (typically split as a=1, b=1, c=3, d=5)
   - Follow Bloom's Taxonomy: Knowledge, Comprehension, Application, Analysis
   - Each CQ should have parts (a, b, c, d)
   - {language_instruction}

3. Short Answer Questions ({num_short} questions):
   - 2-3 marks each
   - Require brief explanations (3-5 sentences)
   - {language_instruction}

**OUTPUT FORMAT:**
Return ONLY valid JSON in this exact structure (no markdown, no explanation):
{{
  "mcq": [
    {{
      "question_text": "Question in English",
      "question_text_bn": "প্রশ্ন বাংলায়",
      "options": [
        {{"label": "A", "text": "Option A", "text_bn": "বিকল্প আ", "is_correct": true}},
        {{"label": "B", "text": "Option B", "text_bn": "বিকল্প বি", "is_correct": false}},
        {{"label": "C", "text": "Option C", "text_bn": "বিকল্প সি", "is_correct": false}},
        {{"label": "D", "text": "Option D", "text_bn": "বিকল্প ডি", "is_correct": false}}
      ],
      "answer_explanation": "Explanation why A is correct",
      "answer_explanation_bn": "কেন সঠিক তার ব্যাখ্যা",
      "difficulty": "easy|medium|hard"
    }}
  ],
  "creative": [
    {{
      "question_text": "Stem/প্রদীপ in English",
      "question_text_bn": "প্রশ্নের স্টেম বাংলায়",
      "parts": [
        {{"label": "a", "text": "What is...?", "text_bn": "কী হলো...?", "bloom": "knowledge", "marks": 1}},
        {{"label": "b", "text": "Explain...", "text_bn": "ব্যাখ্যা করো...", "bloom": "comprehension", "marks": 1}},
        {{"label": "c", "text": "Apply...", "text_bn": "প্রয়োগ করো...", "bloom": "application", "marks": 3}},
        {{"label": "d", "text": "Analyze...", "text_bn": "বিশ্লেষণ করো...", "bloom": "analysis", "marks": 5}}
      ],
      "difficulty": "medium"
    }}
  ],
  "short_answer": [
    {{
      "question_text": "Short question in English",
      "question_text_bn": "সংক্ষিপ্ত প্রশ্ন বাংলায়",
      "answer_explanation": "Brief answer",
      "answer_explanation_bn": "সংক্ষিপ্ত উত্তর",
      "difficulty": "easy|medium|hard",
      "marks": 2
    }}
  ]
}}

**IMPORTANT:**
- Questions MUST be based on the uploaded image content
- Maintain class-appropriate difficulty and language
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
        genai.configure(api_key=api_key)
        self.model_name = model_name or getattr(settings, "GEMINI_MODEL", "gemini-3.1-pro")
        self.model = genai.GenerativeModel(self.model_name)

    def _build_prompt(
        self,
        class_level: str,
        subject: str,
        topic: str,
        num_mcq: int,
        num_creative: int,
        num_short_answer: int,
        language: str = "bilingual",
        additional_prompt: str = "",
    ) -> str:
        """Build the prompt for AI generation."""
        language_instructions = {
            "english": "Generate questions in English only",
            "bengali": "Generate questions in Bengali only (use question_text_bn field)",
            "bilingual": "Generate questions in BOTH English and Bengali (fill both question_text and question_text_bn fields)",
        }
        lang_instruction = language_instructions.get(language, language_instructions["bilingual"])

        prompt = PROMPT_TEMPLATE.format(
            class_level=class_level,
            subject=subject,
            topic=topic or "General",
            num_mcq=num_mcq,
            num_creative=num_creative,
            num_short=num_short_answer,
            language_instruction=lang_instruction,
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

            # Prepare image input
            from PIL import Image
            from io import BytesIO

            # Read uploaded image
            image = Image.open(generation_request.uploaded_image)
            
            # Generate using Gemini with image input
            response = self.model.generate_content(
                [prompt, image],
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 8192,
                },
            )

            # Parse response
            response_text = response.text
            generation_request.ai_response_raw = {"response": response_text}
            
            parsed_data = self._parse_response(response_text)
            generation_request.status = "completed"
            generation_request.completed_at = __import__('django.utils.timezone').utils.now()
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
            return {"success": False, "error": error_msg, "raw_response": response_text if 'response_text' in locals() else ""}

        except Exception as e:
            error_msg = f"AI Generation failed: {str(e)}"
            generation_request.status = "failed"
            generation_request.error_message = error_msg
            generation_request.save(update_fields=["status", "error_message"])
            logger.error(f"AI Generation Error: {error_msg}")
            return {"success": False, "error": error_msg}


def create_questions_from_generation_result(
    generation_request: AIGenerationRequest,
    question_bank,
    parsed_data: dict,
    created_by=None,
) -> dict:
    """
    Create Question and QuestionOption objects from parsed AI data.
    
    Args:
        generation_request: The AIGenerationRequest instance
        question_bank: The QuestionBank to add questions to
        parsed_data: Parsed JSON from AI
        created_by: User who created the questions
        
    Returns:
        dict with counts of created questions by type
    """
    created_counts = {"mcq": 0, "creative": 0, "short_answer": 0}

    # Create MCQ questions
    for mcq_data in parsed_data.get("mcq", []):
        question = Question.objects.create(
            question_bank=question_bank,
            question_text=mcq_data.get("question_text", ""),
            question_text_bn=mcq_data.get("question_text_bn", ""),
            question_type="mcq",
            difficulty=mcq_data.get("difficulty", "medium"),
            marks=1,
            answer_explanation=mcq_data.get("answer_explanation", ""),
            answer_explanation_bn=mcq_data.get("answer_explanation_bn", ""),
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
                option_text_bn=option_data.get("text_bn", ""),
                label=option_data.get("label", ""),
                is_correct=option_data.get("is_correct", False),
            )

        created_counts["mcq"] += 1

    # Create Creative questions
    for cq_data in parsed_data.get("creative", []):
        # For creative questions, combine parts into question_text
        parts = cq_data.get("parts", [])
        parts_text = "\n".join(
            [f"({p.get('label', '')}) {p.get('text', '')}" for p in parts]
        )
        parts_text_bn = "\n".join(
            [f"({p.get('label', '')}) {p.get('text_bn', '')}" for p in parts]
        )

        question = Question.objects.create(
            question_bank=question_bank,
            question_text=f"{cq_data.get('question_text', '')}\n\n{parts_text}",
            question_text_bn=f"{cq_data.get('question_text_bn', '')}\n\n{parts_text_bn}",
            question_type="creative",
            difficulty=cq_data.get("difficulty", "medium"),
            bloom_level=parts[0].get("bloom", "knowledge") if parts else "knowledge",
            marks=10,  # Standard for creative questions
            ai_generated=True,
            generation_request=generation_request,
            created_by=created_by,
            is_approved=False,
        )

        created_counts["creative"] += 1

    # Create Short Answer questions
    for sa_data in parsed_data.get("short_answer", []):
        question = Question.objects.create(
            question_bank=question_bank,
            question_text=sa_data.get("question_text", ""),
            question_text_bn=sa_data.get("question_text_bn", ""),
            question_type="short_answer",
            difficulty=sa_data.get("difficulty", "medium"),
            marks=sa_data.get("marks", 2),
            answer_explanation=sa_data.get("answer_explanation", ""),
            answer_explanation_bn=sa_data.get("answer_explanation_bn", ""),
            ai_generated=True,
            generation_request=generation_request,
            created_by=created_by,
            is_approved=False,
        )

        created_counts["short_answer"] += 1

    return created_counts
