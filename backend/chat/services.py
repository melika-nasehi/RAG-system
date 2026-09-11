"""Business logic for conversations, kept out of views so it can be tested
and reused without going through HTTP.
"""

import time

from core.generation.rag_chain import RagChain

from .models import Conversation, Message

_chain = None


def get_chain():
    global _chain
    if _chain is None:
        _chain = RagChain()
    return _chain


def ask_question(user, question, conversation_id=None):
    """Runs one question through the RAG chain and persists both sides of
    the exchange. Returns the Message row for the assistant's reply."""
    if conversation_id:
        conversation = Conversation.objects.get(id=conversation_id, user=user)
    else:
        conversation = Conversation.objects.create(user=user, title=question[:50])

    Message.objects.create(conversation=conversation, role="user", content=question)

    start = time.monotonic()
    answer = get_chain().ask(question)
    latency_ms = int((time.monotonic() - start) * 1000)

    # The dense cosine of the best passage — comparable across questions and
    # across retrieval modes, unlike the pipeline-dependent `score`.
    top_score = (
        max(p.retrieval_score for p in answer.passages) if answer.passages else None
    )

    assistant_message = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=answer.text,
        retrieved_chunks=[
            {
                "source": p.source,
                "page": p.page,
                "score": p.score,
                "retrieval_score": p.retrieval_score,
            }
            for p in answer.passages
        ],
        top_score=top_score,
        backend_used=answer.backend,
        latency_ms=latency_ms,
    )

    return conversation, assistant_message