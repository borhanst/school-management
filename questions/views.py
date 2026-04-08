from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from academics.models import Subject
from roles.decorators import permission_required
from students.models import AcademicYear, ClassLevel

from .models import AIGenerationRequest, Question, QuestionBank, QuestionOption
from .services.ai_generator import (
    GeminiQuestionGenerator,
    create_questions_from_generation_result,
)


@login_required
@permission_required("questions", "view")
def bank_list(request):
    """List all question banks with filtering."""
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
    except AcademicYear.DoesNotExist:
        academic_year = None

    banks = QuestionBank.objects.select_related(
        "class_level", "subject", "term", "academic_year"
    ).all()

    # Filters
    class_id = request.GET.get("class")
    subject_id = request.GET.get("subject")
    search = request.GET.get("q")

    if class_id:
        banks = banks.filter(class_level_id=class_id)
    if subject_id:
        banks = banks.filter(subject_id=subject_id)
    if search:
        banks = banks.filter(name__icontains=search)

    if academic_year:
        banks = banks.filter(academic_year=academic_year)

    classes = ClassLevel.objects.all()
    subjects = Subject.objects.all()

    context = {
        "banks": banks,
        "classes": classes,
        "subjects": subjects,
        "academic_year": academic_year,
    }
    return render(request, "questions/bank_list.html", context)


@login_required
@permission_required("questions", "add")
def bank_create(request):
    """Create a new question bank or initiate AI generation."""
    if request.method == "POST":
        bank_name = request.POST.get("name")
        class_id = request.POST.get("class_level")
        subject_id = request.POST.get("subject")
        term_id = request.POST.get("term")
        topic = request.POST.get("topic")
        description = request.POST.get("description")

        if not bank_name or not class_id or not subject_id:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "questions/bank_create.html", {
                "classes": ClassLevel.objects.all(),
                "subjects": Subject.objects.all(),
            })

        try:
            academic_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            messages.error(request, "No current academic year set.")
            return redirect("questions:bank_create")

        class_level = get_object_or_404(ClassLevel, pk=class_id)
        subject = get_object_or_404(Subject, pk=subject_id)
        term = None
        if term_id:
            from examinations.models import Term
            term = get_object_or_404(Term, pk=term_id)

        # Check for duplicate
        if QuestionBank.objects.filter(
            name=bank_name,
            class_level=class_level,
            subject=subject,
            academic_year=academic_year,
        ).exists():
            messages.error(request, "A question bank with this name already exists.")
            return render(request, "questions/bank_create.html", {
                "classes": ClassLevel.objects.all(),
                "subjects": Subject.objects.all(),
            })

        bank = QuestionBank.objects.create(
            name=bank_name,
            class_level=class_level,
            subject=subject,
            term=term,
            topic=topic,
            description=description,
            academic_year=academic_year,
            created_by=request.user,
        )

        messages.success(request, f'Question bank "{bank_name}" created successfully.')
        return redirect("questions:bank_detail", pk=bank.pk)

    context = {
        "classes": ClassLevel.objects.all(),
        "subjects": Subject.objects.all(),
    }
    return render(request, "questions/bank_create.html", context)


@login_required
@permission_required("questions", "view")
def bank_detail(request, pk):
    """View question bank with all its questions."""
    bank = get_object_or_404(
        QuestionBank.objects.select_related("class_level", "subject", "term"),
        pk=pk,
    )

    questions = bank.questions.select_related("generation_request").prefetch_related(
        "options"
    ).all()

    # Group by type
    mcq_questions = questions.filter(question_type="mcq")
    creative_questions = questions.filter(question_type="creative")
    short_questions = questions.filter(question_type="short_answer")

    context = {
        "bank": bank,
        "mcq_questions": mcq_questions,
        "creative_questions": creative_questions,
        "short_questions": short_questions,
        "total_questions": questions.count(),
    }
    return render(request, "questions/bank_detail.html", context)


@login_required
@permission_required("questions", "ai_generate")
def ai_generate(request):
    """Start AI question generation from uploaded image."""
    if request.method == "POST":
        class_id = request.POST.get("class_level")
        subject_id = request.POST.get("subject")
        term_id = request.POST.get("term")
        num_mcq = int(request.POST.get("num_mcq", 10))
        num_creative = int(request.POST.get("num_creative", 5))
        num_short = int(request.POST.get("num_short_answer", 5))
        language = request.POST.get("language", "bilingual")
        gemini_model = request.POST.get("gemini_model", "")
        additional_prompt = request.POST.get("additional_prompt", "")
        image = request.FILES.get("uploaded_image")

        if not image:
            messages.error(request, "Please upload a textbook page image.")
            return redirect("questions:ai_generate")

        if not class_id or not subject_id:
            messages.error(request, "Please select class and subject.")
            return redirect("questions:ai_generate")

        class_level = get_object_or_404(ClassLevel, pk=class_id)
        subject = get_object_or_404(Subject, pk=subject_id)
        term = None
        if term_id:
            from examinations.models import Term
            term = get_object_or_404(Term, pk=term_id)

        # Create generation request
        gen_request = AIGenerationRequest.objects.create(
            class_level=class_level,
            subject=subject,
            term=term,
            uploaded_image=image,
            num_mcq=num_mcq,
            num_creative=num_creative,
            num_short_answer=num_short,
            additional_prompt=additional_prompt,
            language=language,
            created_by=request.user,
            status="pending",
        )

        # Trigger AI generation
        try:
            generator = GeminiQuestionGenerator(model_name="gemini-3.1-pro-preview" if gemini_model else None)
            result = generator.generate_questions(gen_request)

            if result["success"]:
                return redirect("questions:generation_review", pk=gen_request.pk)
            else:
                messages.error(
                    request,
                    f"AI generation failed: {result.get('error', 'Unknown error')}",
                )
                return redirect("questions:generation_status", pk=gen_request.pk)

        except ValueError as e:
            messages.error(
                request,
                f"AI service not configured: {str(e)}",
            )
            return redirect("questions:generation_status", pk=gen_request.pk)

    # GET request - show form
    context = {
        "classes": ClassLevel.objects.all(),
        "subjects": Subject.objects.all(),
        "gemini_models": [
            "gemini-3.1-pro",
            "gemini-3.1-pro-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ],
        "default_gemini_model": getattr(settings, "GEMINI_MODEL", "gemini-3.1-pro"),
    }

    # Pre-fill form if retrying a failed request
    retry_pk = request.GET.get("retry")
    if retry_pk:
        try:
            prev_request = AIGenerationRequest.objects.get(pk=retry_pk)
            context.update({
                "prev_class": prev_request.class_level.pk,
                "prev_subject": prev_request.subject.pk,
                "prev_term": prev_request.term.pk if prev_request.term else None,
                "prev_num_mcq": prev_request.num_mcq,
                "prev_num_creative": prev_request.num_creative,
                "prev_num_short_answer": prev_request.num_short_answer,
                "prev_language": prev_request.language,
                "prev_prompt": prev_request.additional_prompt,
            })
        except AIGenerationRequest.DoesNotExist:
            pass

    # Override default model with selected retry model (use settings default)
    context.setdefault("default_gemini_model", getattr(settings, "GEMINI_MODEL", "gemini-3.1-pro"))

    return render(request, "questions/ai_generate.html", context)


@login_required
@permission_required("questions", "ai_generate")
def generation_status(request, pk):
    """Check status of an AI generation request."""
    gen_request = get_object_or_404(AIGenerationRequest, pk=pk)

    context = {
        "gen_request": gen_request,
    }
    return render(request, "questions/generation_status.html", context)


@login_required
@permission_required("questions", "ai_generate")
def generation_review(request, pk):
    """Review and approve AI-generated questions."""
    gen_request = get_object_or_404(
        AIGenerationRequest.objects.prefetch_related("generated_questions"),
        pk=pk,
    )

    if gen_request.status != "completed":
        messages.error(request, "Generation is not yet complete.")
        return redirect("questions:generation_status", pk=pk)

    # Check if questions already created
    if gen_request.generated_questions.exists():
        messages.info(request, "Questions have already been created from this generation.")
        return redirect("questions:bank_detail", pk=gen_request.generated_questions.first().question_bank.pk)

    if request.method == "POST":
        # Create question bank first
        bank_name = request.POST.get("bank_name")
        topic = request.POST.get("topic")

        if not bank_name:
            messages.error(request, "Please provide a question bank name.")
            return render(request, "questions/generation_review.html", {
                "gen_request": gen_request,
                "parsed_data": gen_request.ai_response_raw,
            })

        try:
            academic_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            messages.error(request, "No current academic year set.")
            return redirect("questions:generation_status", pk=pk)

        bank = QuestionBank.objects.create(
            name=bank_name,
            class_level=gen_request.class_level,
            subject=gen_request.subject,
            term=gen_request.term,
            topic=topic,
            academic_year=academic_year,
            created_by=request.user,
        )

        # Parse AI response and create questions
        parsed_data = gen_request.ai_response_raw
        if isinstance(parsed_data, dict) and "response" in parsed_data:
            # Need to parse from the response wrapper
            import json
            response_text = parsed_data.get("response", "")
            # Re-parse
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed_data = json.loads(cleaned.strip())

        counts = create_questions_from_generation_result(
            generation_request=gen_request,
            question_bank=bank,
            parsed_data=parsed_data,
            created_by=request.user,
        )

        messages.success(
            request,
            f"Created {counts['mcq']} MCQ, {counts['creative']} Creative, "
            f"and {counts['short_answer']} Short Answer questions.",
        )
        return redirect("questions:bank_detail", pk=bank.pk)

    context = {
        "gen_request": gen_request,
        "parsed_data": gen_request.ai_response_raw,
    }
    return render(request, "questions/generation_review.html", context)


@login_required
@permission_required("questions", "edit")
def question_edit(request, pk):
    """Edit a single question."""
    question = get_object_or_404(
        Question.objects.select_related("question_bank"),
        pk=pk,
    )

    if request.method == "POST":
        question.question_text = request.POST.get("question_text", question.question_text)
        question.question_text_bn = request.POST.get("question_text_bn", "")
        question.difficulty = request.POST.get("difficulty", question.difficulty)
        question.marks = int(request.POST.get("marks", question.marks))
        question.answer_explanation = request.POST.get("answer_explanation", "")
        question.answer_explanation_bn = request.POST.get("answer_explanation_bn", "")
        question.is_approved = request.POST.get("is_approved") == "on"
        question.save()

        # Update MCQ options if applicable
        if question.question_type == "mcq":
            correct_label = request.POST.get("correct_option", "")
            for option in question.options.all():
                label = option.label
                option.option_text = request.POST.get(f"option_{label}_text", option.option_text)
                option.option_text_bn = request.POST.get(f"option_{label}_text_bn", "")
                option.is_correct = (label == correct_label)
                option.save()

        messages.success(request, "Question updated successfully.")
        return redirect("questions:bank_detail", pk=question.question_bank.pk)

    context = {
        "question": question,
    }
    return render(request, "questions/question_edit.html", context)


@login_required
@permission_required("questions", "delete")
@require_POST
def question_delete(request, pk):
    """Delete a single question."""
    question = get_object_or_404(Question, pk=pk)
    bank_pk = question.question_bank.pk
    question.delete()
    messages.success(request, "Question deleted successfully.")
    return redirect("questions:bank_detail", pk=bank_pk)


@login_required
@permission_required("questions", "view")
def export_question_paper(request, pk):
    """Generate a printable question paper."""
    bank = get_object_or_404(
        QuestionBank.objects.select_related("class_level", "subject", "term"),
        pk=pk,
    )

    # Get approved questions (or all if none approved)
    questions = bank.questions.filter(is_approved=True)
    if not questions.exists():
        questions = bank.questions.all()

    mcq_questions = questions.filter(question_type="mcq").prefetch_related("options")
    creative_questions = questions.filter(question_type="creative")
    short_questions = questions.filter(question_type="short_answer")

    context = {
        "bank": bank,
        "mcq_questions": mcq_questions,
        "creative_questions": creative_questions,
        "short_questions": short_questions,
        "total_marks": (
            mcq_questions.count() * 1 +  # 1 mark each MCQ
            creative_questions.count() * 10 +  # 10 marks each CQ
            (short_questions.aggregate(total=models.Sum("marks"))["total"] or 0)
        ),
    }
    return render(request, "questions/question_paper.html", context)


# AJAX endpoints


@login_required
@permission_required("questions", "view")
def get_subjects_for_class(request):
    """AJAX: Get subjects for a class level."""
    class_id = request.GET.get("class_id")
    if not class_id:
        return JsonResponse({"error": "class_id required"}, status=400)

    subjects = Subject.objects.filter(class_level_id=class_id, is_active=True)
    data = [{"id": s.pk, "name": str(s), "code": s.code} for s in subjects]
    return JsonResponse({"subjects": data})
