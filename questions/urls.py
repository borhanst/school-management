from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    # Question Bank CRUD
    path("", views.bank_list, name="bank_list"),
    path("create/", views.bank_create, name="bank_create"),
    path("bank/<int:pk>/", views.bank_detail, name="bank_detail"),
    path("bank/<int:pk>/edit/", views.bank_edit, name="bank_edit"),
    path("bank/<int:pk>/delete/", views.bank_delete, name="bank_delete"),

    # AI Generation (standalone)
    path("ai-generate/", views.ai_generate, name="ai_generate"),
    path("generation/<int:pk>/status/", views.generation_status, name="generation_status"),
    path("generation/<int:pk>/review/", views.generation_review, name="generation_review"),

    # Question Paper Management (standalone)
    path("papers/", views.paper_list, name="paper-list-all"),
    path("papers/create/", views.paper_create, name="paper-create-standalone"),
    path("paper/<int:pk>/", views.paper_detail, name="paper-detail"),
    path("paper/<int:pk>/edit/", views.paper_edit, name="paper-edit"),
    path("paper/<int:pk>/delete/", views.paper_delete, name="paper-delete"),
    path("paper/<int:pk>/toggle-publish/", views.paper_toggle_published, name="paper-toggle-publish"),
    path("paper/<int:pk>/add-question/", views.paper_add_question, name="paper-add-question"),
    path("paper/<int:pk>/add-question-manual/", views.paper_add_question_manual, name="paper-add-question-manual"),
    path("paper/<int:pk>/ai-generate/", views.ai_generate, name="paper-ai-generate"),
    path("paper/<int:pk>/questions/create/", views.question_create_for_paper, name="paper-question-create"),
    path("paper/<int:pk>/questions/reorder/", views.question_reorder, name="paper-question-reorder"),
    path("paper-question/<int:pk>/remove/", views.paper_remove_question, name="paper-remove-question"),
    
    # Question Paper Management (from bank)
    path("bank/<int:bank_pk>/papers/", views.paper_list, name="paper-list"),
    path("bank/<int:bank_pk>/papers/create/", views.paper_create, name="paper-create"),

    # Question CRUD
    path("question/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("question/<int:pk>/delete/", views.question_delete, name="question_delete"),

    # Export
    path("bank/<int:pk>/export/", views.export_question_paper, name="export_paper"),

    # AJAX
    path("ajax/get-subjects/", views.get_subjects_for_class, name="get_subjects"),
]
