from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chat.models import Conversation
from chat.services import ask_question


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask(request):
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"error": "question is required"}, status=400)

    conversation, message = ask_question(
        user=request.user,
        question=question,
        conversation_id=request.data.get("conversation_id"),
    )

    return Response({
        "conversation_id": conversation.id,
        "question": question,
        "answer": message.content,
        "sources": [f"{c['source']}, صفحه {c['page']}" for c in message.retrieved_chunks],
        "backend": message.backend_used,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_conversations(request):
    conversations = Conversation.objects.filter(user=request.user)[:20]
    return Response([
        {"id": c.id, "title": c.title, "updated_at": c.updated_at}
        for c in conversations
    ])


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def get_conversation(request, conversation_id):
    # Scoped to request.user for both verbs: a conversation id that exists
    # but belongs to someone else 404s exactly like one that doesn't exist —
    # it never leaks whether the id is valid, only that it isn't yours.
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)

    if request.method == "DELETE":
        conversation.delete()  # cascades to its Messages, and their Feedback
        return Response(status=204)

    messages = conversation.messages.all()
    return Response({
        "id": conversation.id,
        "title": conversation.title,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "sources": [f"{c['source']}, صفحه {c['page']}" for c in m.retrieved_chunks],
            }
            for m in messages
        ],
    })
