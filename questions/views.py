from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Count, Prefetch, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from academics.models import Subject
from roles.decorators import permission_required
from students.models import AcademicYear, ClassLevel

from .models import AIGenerationRequest, Question, QuestionBank, QuestionOption, QuestionPaper, QuestionPaperQuestion
from .services.ai_generator import (
    GeminiQuestionGenerator,
    GroqQuestionGenerator,
    create_questions_from_generation_result,
)


@login_required
@permission_required("questions", "view")
def bank_list(request):
    """Redirect to question papers list."""
    return redirect("questions:paper-list-all")


@login_required
@permission_required("questions", "add")
def bank_create(request):
    """Redirect to question paper creation."""
    return redirect("questions:paper-create-standalone")


@login_required
@permission_required("questions", "view")
def bank_detail(request, pk):
    """Redirect to question paper list."""
    return redirect("questions:paper-list-all")


@login_required
@permission_required("questions", "edit")
def bank_edit(request, pk):
    """Redirect to question paper list."""
    return redirect("questions:paper-list-all")


@login_required
@permission_required("questions", "delete")
@require_POST
def bank_delete(request, pk):
    """Redirect to question paper list."""
    return redirect("questions:paper-list-all")


@login_required
@permission_required("questions", "ai_generate")
def ai_generate(request, pk=None):
    """Redirect to question papers list if no paper specified."""
    if pk:
        paper = get_object_or_404(QuestionPaper, pk=pk)
    else:
        return redirect("questions:paper-list-all")

    if request.method == "POST":
        class_id = request.POST.get("class_level")
        subject_id = request.POST.get("subject")
        term_id = request.POST.get("term")
        num_mcq = int(request.POST.get("num_mcq", 10))
        num_creative = int(request.POST.get("num_creative", 5))
        num_short = int(request.POST.get("num_short_answer", 5))
        language = request.POST.get("language", "english")
        ai_provider = request.POST.get("ai_provider", "gemini")
        model_name = request.POST.get("model_name", "")
        additional_prompt = request.POST.get("additional_prompt", "")
        image = request.FILES.get("uploaded_image")

        if not image:
            messages.error(request, "Please upload a textbook page image.")
            return redirect("questions:paper-ai-generate", pk=paper.pk) if paper else redirect("questions:ai_generate")

        if not class_id or not subject_id:
            messages.error(request, "Please select class and subject.")
            return redirect("questions:paper-ai-generate", pk=paper.pk) if paper else redirect("questions:ai_generate")

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
            question_paper=paper,
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
            if ai_provider == "groq":
                generator = GroqQuestionGenerator(
                    model_name=model_name if model_name else None
                )
            else:  # default to gemini
                generator = GeminiQuestionGenerator(
                    model_name="gemini-2.5-pro" if model_name else None
                )
            result = generator.generate_questions(gen_request)
            print(result)
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
        "ai_providers": [
            {"id": "gemini", "name": "Google Gemini"},
            {"id": "groq", "name": "Groq (Llama)"},
        ],
        "gemini_models": [
            "gemini-3.1-pro",
            "gemini-3.1-pro-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ],
        "groq_models": [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-3.3-70b-versatile",
            "meta-llama/llama-3.1-8b-instant",
        ],
        "default_gemini_model": getattr(settings, "GEMINI_MODEL", "gemini-3.1-pro"),
        "default_groq_model": getattr(
            settings, "GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
        ),
        "paper": paper,
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

    # Pre-fill class/subject if from paper
    if paper:
        context.update({
            "prev_class": paper.class_level.pk if paper.class_level else None,
            "prev_subject": paper.subject.pk if paper.subject else None,
            "prev_term": paper.term.pk if paper.term else None,
        })

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
        # Redirect to paper if exists, otherwise bank
        if gen_request.question_paper:
            return redirect("questions:paper-detail", pk=gen_request.question_paper.pk)
        elif gen_request.generated_questions.first().question_bank:
            return redirect("questions:bank_detail", pk=gen_request.generated_questions.first().question_bank.pk)

    if request.method == "POST":
        action = request.POST.get("action", "create_bank")
        
        try:
            academic_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            messages.error(request, "No current academic year set.")
            return redirect("questions:generation_status", pk=pk)

        if action == "create_bank":
            # Create question bank first
            bank_name = request.POST.get("bank_name")
            topic = request.POST.get("topic")

            if not bank_name:
                messages.error(request, "Please provide a question bank name.")
                return render(request, "questions/generation_review.html", {
                    "gen_request": gen_request,
                    "parsed_data": gen_request.ai_response_raw,
                })

            # Check for duplicate question bank
            if QuestionBank.objects.filter(
                name=bank_name,
                class_level=gen_request.class_level,
                subject=gen_request.subject,
                academic_year=academic_year,
            ).exists():
                messages.error(
                    request,
                    f'A question bank with name "{bank_name}" already exists for this class, subject, and academic year. Please choose a different name.',
                )
                return render(request, "questions/generation_review.html", {
                    "gen_request": gen_request,
                    "parsed_data": gen_request.ai_response_raw,
                })

            bank = QuestionBank.objects.create(
                name=bank_name,
                class_level=gen_request.class_level,
                subject=gen_request.subject,
                term=gen_request.term,
                topic=topic,
                academic_year=academic_year,
                created_by=request.user,
            )
        else:
            # Create directly under paper
            bank = None
            if gen_request.question_paper:
                bank = gen_request.question_paper.get_or_create_bank()

            bank_name = gen_request.question_paper.name if gen_request.question_paper else "AI Generated"
            topic = request.POST.get("topic", "")

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

        # Determine where to create questions
        target_bank = bank if bank else (gen_request.question_paper.get_or_create_bank() if gen_request.question_paper else None)
        target_paper = gen_request.question_paper

        counts = create_questions_from_generation_result(
            generation_request=gen_request,
            question_bank=target_bank,
            question_paper=target_paper,
            parsed_data=parsed_data,
            created_by=request.user,
        )

        if target_paper:
            messages.success(
                request,
                f"Created {counts['mcq']} MCQ, {counts['creative']} Creative, "
                f"and {counts['short_answer']} Short Answer questions for paper.",
            )
            return redirect("questions:paper-detail", pk=target_paper.pk)
        else:
            messages.success(
                request,
                f"Created {counts['mcq']} MCQ, {counts['creative']} Creative, "
                f"and {counts['short_answer']} Short Answer questions.",
            )
            return redirect("questions:bank_detail", pk=bank.pk)

    # GET request - show review page
    try:
        academic_year = AcademicYear.objects.get(is_current=True)
        existing_banks = QuestionBank.objects.filter(
            class_level=gen_request.class_level,
            subject=gen_request.subject,
            academic_year=academic_year,
        ).select_related("class_level", "subject")
    except AcademicYear.DoesNotExist:
        existing_banks = QuestionBank.objects.none()

    context = {
        "gen_request": gen_request,
        "parsed_data": gen_request.ai_response_raw,
        "existing_banks": existing_banks,
    }
    return render(request, "questions/generation_review.html", context)


@login_required
@permission_required("questions", "edit")
def question_edit(request, pk):
    """Edit a single question."""
    question = get_object_or_404(
        Question.objects.select_related("question_bank", "question_paper").prefetch_related("options"),
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
        
        # Redirect to appropriate page
        if question.question_paper:
            return redirect("questions:paper-detail", pk=question.question_paper.pk)
        elif question.question_bank:
            return redirect("questions:bank_detail", pk=question.question_bank.pk)
        else:
            return redirect("questions:bank_list")

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
    
    # Determine where to redirect after deletion
    paper_pk = question.question_paper.pk if question.question_paper else None
    bank_pk = question.question_bank.pk if question.question_bank else None
    
    question.delete()
    messages.success(request, "Question deleted successfully.")
    
    # Redirect to appropriate page
    if paper_pk:
        return redirect("questions:paper-detail", pk=paper_pk)
    elif bank_pk:
        return redirect("questions:bank_detail", pk=bank_pk)
    else:
        return redirect("questions:bank_list")


@login_required
@permission_required("questions", "view")
def export_question_paper(request, pk):
    """Redirect to question paper detail."""
    return redirect("questions:paper-detail", pk=pk)


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


# Question Paper Management Views


@login_required
@permission_required("questions", "view")
def paper_list(request, bank_pk=None):
    """List all question papers for a question bank or all papers."""
    bank = None
    if bank_pk:
        bank = get_object_or_404(QuestionBank, pk=bank_pk)
        papers = bank.question_papers.all().select_related(
            "created_by", "class_level", "subject"
        )
    else:
        papers = QuestionPaper.objects.all().select_related(
            "created_by", "question_bank", "class_level", "subject"
        )

    papers = papers.annotate(question_count=Count("paper_questions"))
    paginator = Paginator(papers, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "bank": bank,
        "papers": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "questions/paper_list.html", context)


@login_required
@permission_required("questions", "add")
def paper_create(request, bank_pk=None):
    """Create a new question paper from a question bank or standalone."""
    bank = None
    if bank_pk:
        bank = get_object_or_404(QuestionBank, pk=bank_pk)

    if request.method == "POST":
        name = request.POST.get("name")
        paper_type = request.POST.get("paper_type", "test")
        difficulty = request.POST.get("difficulty", "medium")
        duration_minutes = int(request.POST.get("duration_minutes", 60))
        instructions = request.POST.get("instructions", "")
        class_id = request.POST.get("class_level")
        subject_id = request.POST.get("subject")
        term_id = request.POST.get("term")

        if not name:
            messages.error(request, "Please provide a question paper name.")
            context = {"bank": bank}
            if bank:
                context.update({
                    "classes": ClassLevel.objects.all(),
                    "subjects": Subject.objects.all(),
                })
            return render(request, "questions/paper_form.html", context)

        try:
            academic_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            messages.error(request, "No current academic year set.")
            return redirect("questions:paper-list", bank_pk=bank.pk if bank else 0)

        # If no bank, we need class and subject
        class_level = None
        subject = None
        term = None
        
        if not bank:
            if not class_id or not subject_id:
                messages.error(request, "Please select class and subject for standalone paper.")
                context = {"bank": bank}
                return render(request, "questions/paper_form.html", context)
            
            class_level = get_object_or_404(ClassLevel, pk=class_id)
            subject = get_object_or_404(Subject, pk=subject_id)
            if term_id:
                from examinations.models import Term
                term = get_object_or_404(Term, pk=term_id)
        else:
            class_level = bank.class_level
            subject = bank.subject
            term = bank.term

        paper = QuestionPaper.objects.create(
            name=name,
            question_bank=bank,
            class_level=class_level,
            subject=subject,
            term=term,
            paper_type=paper_type,
            difficulty=difficulty,
            duration_minutes=duration_minutes,
            instructions=instructions,
            academic_year=academic_year,
            created_by=request.user,
        )

        messages.success(request, f'Question paper "{name}" created successfully.')
        return redirect("questions:paper-detail", pk=paper.pk)

    context = {"bank": bank}
    if bank:
        context.update({
            "classes": ClassLevel.objects.all(),
            "subjects": Subject.objects.all(),
        })
    return render(request, "questions/paper_form.html", context)


@login_required
@permission_required("questions", "view")
def paper_detail(request, pk):
    """View a question paper with all its questions."""
    paper = get_object_or_404(
        QuestionPaper.objects.select_related(
            "question_bank", "created_by", "class_level", "subject"
        ).prefetch_related(
            Prefetch(
                "question_bank__questions",
                queryset=Question.objects.order_by(
                    "question_type", "-created_at"
                ),
            )
        ),
        pk=pk,
    )

    # Recalculate total marks to ensure it's up to date
    total_marks = paper.paper_questions.aggregate(total=Sum("marks"))[
        "total"
    ] or 0
    if paper.total_marks != total_marks:
        paper.total_marks = total_marks
        paper.save(update_fields=["total_marks"])

    # Get all questions via QuestionPaperQuestion linking table (ordered)
    linked_questions = (
        paper.paper_questions.select_related("question")
        .prefetch_related("question__options")
        .order_by("order")
    )
    linked_questions_by_type = {
        "mcq": [],
        "creative": [],
        "short_answer": [],
    }
    for paper_question in linked_questions:
        linked_questions_by_type[
            paper_question.question.question_type
        ].append(paper_question)

    context = {
        "paper": paper,
        "question_count": sum(
            len(questions) for questions in linked_questions_by_type.values()
        ),
        "mcq_questions": linked_questions_by_type["mcq"],
        "creative_questions": linked_questions_by_type["creative"],
        "short_questions": linked_questions_by_type["short_answer"],
    }
    return render(request, "questions/paper_detail.html", context)


@login_required
@permission_required("questions", "edit")
def paper_edit(request, pk):
    """Edit a question paper."""
    paper = get_object_or_404(QuestionPaper, pk=pk)

    if request.method == "POST":
        paper.name = request.POST.get("name", paper.name)
        paper.paper_type = request.POST.get("paper_type", paper.paper_type)
        paper.difficulty = request.POST.get("difficulty", paper.difficulty)
        paper.duration_minutes = int(request.POST.get("duration_minutes", paper.duration_minutes))
        paper.instructions = request.POST.get("instructions", paper.instructions)
        paper.is_published = request.POST.get("is_published") == "on"
        
        # Update class/subject if standalone paper
        if not paper.question_bank:
            class_id = request.POST.get("class_level")
            subject_id = request.POST.get("subject")
            term_id = request.POST.get("term")
            
            if class_id:
                paper.class_level = get_object_or_404(ClassLevel, pk=class_id)
            if subject_id:
                paper.subject = get_object_or_404(Subject, pk=subject_id)
            if term_id:
                from examinations.models import Term
                paper.term = get_object_or_404(Term, pk=term_id)
        
        paper.save()

        messages.success(request, "Question paper updated successfully.")
        return redirect("questions:paper-detail", pk=paper.pk)

    context = {"paper": paper}
    return render(request, "questions/paper_edit.html", context)


@login_required
@permission_required("questions", "delete")
@require_POST
def paper_delete(request, pk):
    """Delete a question paper."""
    paper = get_object_or_404(QuestionPaper, pk=pk)
    bank_pk = paper.question_bank.pk
    paper.delete()
    messages.success(request, "Question paper deleted successfully.")
    return redirect("questions:paper-list", bank_pk=bank_pk)


@login_required
@permission_required("questions", "edit")
@require_POST
def paper_add_question(request, pk):
    """Add a question to a question paper."""
    paper = get_object_or_404(QuestionPaper, pk=pk)
    question_id = request.POST.get("question_id")
    marks = int(request.POST.get("marks", 1))

    if not question_id:
        messages.error(request, "Question ID is required.")
        return redirect("questions:paper-detail", pk=pk)

    question = get_object_or_404(Question, pk=question_id)

    # Check if question already exists in paper
    if paper.paper_questions.filter(question=question).exists():
        messages.info(request, "This question is already in the paper.")
        return redirect("questions:paper-detail", pk=pk)

    # Get max order
    max_order = paper.paper_questions.aggregate(
        max_order=models.Max("order")
    )["max_order"] or 0

    QuestionPaperQuestion.objects.create(
        question_paper=paper,
        question=question,
        order=max_order + 1,
        marks=marks,
    )

    # Recalculate total marks
    paper.calculate_total_marks()

    messages.success(request, "Question added to paper.")
    return redirect("questions:paper-detail", pk=pk)


@login_required
@permission_required("questions", "edit")
@require_POST
def paper_remove_question(request, pk):
    """Remove a question from a question paper."""
    paper_question = get_object_or_404(QuestionPaperQuestion, pk=pk)
    paper_pk = paper_question.question_paper.pk
    paper_question.delete()
    
    # Recalculate total marks
    paper = QuestionPaper.objects.get(pk=paper_pk)
    paper.calculate_total_marks()
    
    messages.success(request, "Question removed from paper.")
    return redirect("questions:paper-detail", pk=paper_pk)


@login_required
@permission_required("questions", "edit")
@require_POST
def paper_toggle_published(request, pk):
    """Toggle the published status of a question paper."""
    paper = get_object_or_404(QuestionPaper, pk=pk)
    paper.is_published = not paper.is_published
    paper.save(update_fields=["is_published"])

    status = "published" if paper.is_published else "unpublished"
    messages.success(request, f"Question paper {status}.")
    return redirect("questions:paper-detail", pk=pk)


@login_required
@permission_required("questions", "add")
def paper_add_question_manual(request, pk):
    """Add a question manually to a question paper."""
    paper = get_object_or_404(QuestionPaper, pk=pk)

    if request.method == "POST":
        question_text = request.POST.get("question_text")
        question_text_bn = request.POST.get("question_text_bn", "")
        question_type = request.POST.get("question_type", "mcq")
        difficulty = request.POST.get("difficulty", "medium")
        marks = int(request.POST.get("marks", 1))
        bloom_level = request.POST.get("bloom_level", "knowledge")
        answer_explanation = request.POST.get("answer_explanation", "")
        answer_explanation_bn = request.POST.get("answer_explanation_bn", "")

        if not question_text:
            messages.error(request, "Question text is required.")
            return redirect("questions:paper-detail", pk=pk)

        # Get or create bank for this paper
        bank = paper.get_or_create_bank()

        # Create the question directly under the paper
        question = Question.objects.create(
            question_bank=bank,
            question_paper=paper,
            question_text=question_text,
            question_text_bn=question_text_bn,
            question_type=question_type,
            difficulty=difficulty,
            bloom_level=bloom_level,
            marks=marks,
            answer_explanation=answer_explanation,
            answer_explanation_bn=answer_explanation_bn,
            ai_generated=False,
            created_by=request.user,
            is_approved=True,
        )

        # If MCQ, create options
        if question_type == "mcq":
            labels = ["A", "B", "C", "D"]
            correct_option = request.POST.get("correct_option", "A")
            
            for label in labels:
                option_text = request.POST.get(f"option_{label}_text", "")
                option_text_bn = request.POST.get(f"option_{label}_text_bn", "")
                
                if option_text:
                    QuestionOption.objects.create(
                        question=question,
                        option_text=option_text,
                        option_text_bn=option_text_bn,
                        label=label,
                        is_correct=(label == correct_option),
                    )

        # Also add to paper questions linking table
        max_order = paper.paper_questions.aggregate(
            max_order=models.Max("order")
        )["max_order"] or 0

        QuestionPaperQuestion.objects.create(
            question_paper=paper,
            question=question,
            order=max_order + 1,
            marks=marks,
        )

        messages.success(request, f'Question "{question_text[:50]}..." added to paper.')
        return redirect("questions:paper-detail", pk=pk)


@login_required
@permission_required("questions", "edit")
def question_create_for_paper(request, pk):
    """Create a new question for a specific paper."""
    paper = get_object_or_404(QuestionPaper, pk=pk)

    if request.method == "POST":
        question_text = request.POST.get("question_text")
        question_text_bn = request.POST.get("question_text_bn", "")
        question_type = request.POST.get("question_type", "mcq")
        difficulty = request.POST.get("difficulty", "medium")
        marks = int(request.POST.get("marks", 1))
        bloom_level = request.POST.get("bloom_level", "knowledge")
        answer_explanation = request.POST.get("answer_explanation", "")

        if not question_text:
            messages.error(request, "Question text is required.")
            return redirect("questions:paper-detail", pk=paper.pk)

        # Get or create bank
        bank = paper.get_or_create_bank()

        # Create question
        question = Question.objects.create(
            question_bank=bank,
            question_paper=paper,
            question_text=question_text,
            question_text_bn=question_text_bn,
            question_type=question_type,
            difficulty=difficulty,
            bloom_level=bloom_level,
            marks=marks,
            answer_explanation=answer_explanation,
            ai_generated=False,
            created_by=request.user,
            is_approved=True,
        )

        # If MCQ, create options
        if question_type == "mcq":
            labels = ["A", "B", "C", "D"]
            correct_option = request.POST.get("correct_option", "A")

            for label in labels:
                option_text = request.POST.get(f"option_{label}_text", "")
                if option_text:
                    QuestionOption.objects.create(
                        question=question,
                        option_text=option_text,
                        label=label,
                        is_correct=(label == correct_option),
                    )

        # Add to paper
        max_order = paper.paper_questions.aggregate(
            max_order=models.Max("order")
        )["max_order"] or 0

        QuestionPaperQuestion.objects.create(
            question_paper=paper,
            question=question,
            order=max_order + 1,
            marks=marks,
        )

        # Recalculate total marks
        paper.calculate_total_marks()

        messages.success(request, "Question created successfully.")
        return redirect("questions:paper-detail", pk=paper.pk)
    
    # For GET requests, render the template
    context = {"paper": paper}
    return render(request, "questions/paper_question_create.html", context)


@login_required
@permission_required("questions", "edit")
@require_http_methods(["POST"])
def question_reorder(request, pk):
    """AJAX: Reorder questions in a paper."""
    paper = get_object_or_404(QuestionPaper, pk=pk)
    
    try:
        import json
        data = json.loads(request.body)
        question_orders = data.get("question_orders", [])
        
        # question_orders is a list of {id, order}
        with transaction.atomic():
            for item in question_orders:
                paper_question = QuestionPaperQuestion.objects.get(
                    pk=item["id"],
                    question_paper=paper
                )
                paper_question.order = item["order"]
                paper_question.save()
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
