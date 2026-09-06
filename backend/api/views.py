"""HTTP layer only. All RAG logic lives in src/ and is untouched by this file."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "5_generation"))

from rest_framework.decorators import api_view
from rest_framework.response import Response

from rag_chain import RagChain

_chain = None


def get_chain():
    global _chain
    if _chain is None:
        _chain = RagChain()
    return _chain


@api_view(["POST"])
def ask_question(request):
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"error": "question is required"}, status=400)

    answer = get_chain().ask(question)

    return Response({
        "question": answer.question,
        "answer": answer.text,
        "sources": answer.sources(),
        "backend": answer.backend,
    })