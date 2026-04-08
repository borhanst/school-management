from django.contrib import admin
from .models import QuestionBank, Question, QuestionOption, AIGenerationRequest


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4
    fields = ["label", "option_text", "option_text_bn", "is_correct"]


@admin.register(QuestionBank)
class QuestionBankAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "class_level",
        "subject",
        "topic",
        "academic_year",
        "created_at",
        "is_active",
    ]
    list_filter = [
        "is_active",
        "class_level",
        "subject",
        "academic_year",
    ]
    search_fields = ["name", "description", "topic"]
    date_hierarchy = "created_at"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        "question_text_short",
        "question_type",
        "difficulty",
        "marks",
        "question_bank",
        "is_approved",
        "ai_generated",
    ]
    list_filter = [
        "question_type",
        "difficulty",
        "is_approved",
        "ai_generated",
    ]
    search_fields = ["question_text", "question_text_bn", "answer_explanation"]
    inlines = [QuestionOptionInline]

    def question_text_short(self, obj):
        return f"{obj.question_text[:60]}..."

    question_text_short.short_description = "Question"


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = [
        "label",
        "option_text_short",
        "question",
        "is_correct",
    ]
    list_filter = ["is_correct"]
    search_fields = ["option_text", "option_text_bn"]

    def option_text_short(self, obj):
        return f"{obj.option_text[:40]}..."

    option_text_short.short_description = "Option"


@admin.register(AIGenerationRequest)
class AIGenerationRequestAdmin(admin.ModelAdmin):
    list_display = [
        "class_level",
        "subject",
        "status",
        "total_questions_requested",
        "language",
        "created_by",
        "created_at",
    ]
    list_filter = ["status", "language", "class_level", "subject"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "prompt_used",
        "ai_response_raw",
        "error_message",
        "completed_at",
    ]
