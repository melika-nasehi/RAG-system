from django.urls import path

from .admin_views import DocumentDetailView, DocumentUploadView
from .views import ask, get_conversation, list_conversations

urlpatterns = [
    path("ask/", ask, name="ask"),
    path("conversations/", list_conversations, name="conversations"),
    path("conversations/<int:conversation_id>/", get_conversation, name="conversation-detail"),
    path("admin/documents/", DocumentUploadView.as_view(), name="admin-documents"),
    path(
        "admin/documents/<int:document_id>/",
        DocumentDetailView.as_view(),
        name="admin-document-detail",
    ),
]
