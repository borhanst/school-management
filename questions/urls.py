from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    # Question Bank
    path("", views.bank_list, name="bank_list"),
    path("create/", views.bank_create, name="bank_create"),
    path("bank/<int:pk>/", views.bank_detail, name="bank_detail"),
    
    # AI Generation
    path("ai-generate/", views.ai_generate, name="ai_generate"),
    path("generation/<int:pk>/status/", views.generation_status, name="generation_status"),
    path("generation/<int:pk>/review/", views.generation_review, name="generation_review"),
    
    # Question CRUD
    path("question/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("question/<int:pk>/delete/", views.question_delete, name="question_delete"),
    
    # Export
    path("bank/<int:pk>/export/", views.export_question_paper, name="export_paper"),
    
    # AJAX
    path("ajax/get-subjects/", views.get_subjects_for_class, name="get_subjects"),
]
