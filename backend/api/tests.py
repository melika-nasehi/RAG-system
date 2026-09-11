import io
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from accounts.tokens import for_user
from api.models import Document
from chat.models import Conversation, Feedback, Message

ASK = "/api/ask/"
CONVERSATIONS = "/api/conversations/"
ADMIN_DOCS = "/api/admin/documents/"


def conversation_detail(conversation_id):
    return f"/api/conversations/{conversation_id}/"


def document_detail(document_id):
    return f"/api/admin/documents/{document_id}/"


def bearer(user):
    return {"HTTP_AUTHORIZATION": "Bearer " + for_user(user)["access"]}


class AuthenticationRequiredTests(APITestCase):
    def test_ask_requires_authentication(self):
        self.assertEqual(self.client.post(ASK, {"question": "x"}, format="json").status_code, 401)

    def test_conversations_require_authentication(self):
        self.assertEqual(self.client.get(CONVERSATIONS).status_code, 401)


class AskEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("student1", password="pw-abcdef-123456")

    @mock.patch("api.views.ask_question")
    def test_ask_uses_the_request_user_not_a_shared_test_user(self, ask_question):
        conversation = Conversation.objects.create(user=self.user, title="t")
        message = Message.objects.create(
            conversation=conversation, role="assistant", content="پاسخ", retrieved_chunks=[]
        )
        ask_question.return_value = (conversation, message)

        response = self.client.post(
            ASK, {"question": "سوال؟"}, format="json", **bearer(self.user)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ask_question.call_args.kwargs["user"], self.user)

    def test_a_user_only_sees_their_own_conversations(self):
        other = User.objects.create_user("student2", password="pw-abcdef-123456")
        Conversation.objects.create(user=self.user, title="mine")
        Conversation.objects.create(user=other, title="theirs")

        response = self.client.get(CONVERSATIONS, **bearer(self.user))
        titles = [c["title"] for c in response.data]
        self.assertEqual(titles, ["mine"])


class DeleteConversationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("student1", password="pw-abcdef-123456")
        self.other = User.objects.create_user("student2", password="pw-abcdef-123456")

    def test_deleting_removes_the_conversation_and_its_messages(self):
        conversation = Conversation.objects.create(user=self.user, title="to delete")
        message = Message.objects.create(
            conversation=conversation, role="assistant", content="پاسخ", retrieved_chunks=[]
        )
        Feedback.objects.create(message=message, rating="up")

        response = self.client.delete(conversation_detail(conversation.id), **bearer(self.user))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Conversation.objects.filter(id=conversation.id).exists())
        self.assertFalse(Message.objects.filter(id=message.id).exists())
        self.assertFalse(Feedback.objects.filter(message_id=message.id).exists())

    def test_a_user_cannot_delete_another_users_conversation(self):
        theirs = Conversation.objects.create(user=self.other, title="not yours")

        response = self.client.delete(conversation_detail(theirs.id), **bearer(self.user))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Conversation.objects.filter(id=theirs.id).exists())

    def test_deleting_requires_authentication(self):
        conversation = Conversation.objects.create(user=self.user, title="x")
        response = self.client.delete(conversation_detail(conversation.id))
        self.assertEqual(response.status_code, 401)
        self.assertTrue(Conversation.objects.filter(id=conversation.id).exists())

    def test_deleting_an_unknown_id_is_404(self):
        response = self.client.delete(conversation_detail(999999), **bearer(self.user))
        self.assertEqual(response.status_code, 404)

    def test_the_list_no_longer_includes_a_deleted_conversation(self):
        conversation = Conversation.objects.create(user=self.user, title="gone soon")
        self.client.delete(conversation_detail(conversation.id), **bearer(self.user))

        response = self.client.get(CONVERSATIONS, **bearer(self.user))
        self.assertEqual([c["id"] for c in response.data], [])


class AdminDocumentEndpointTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user("stud", password="pw-abcdef-123456")
        self.admin = User.objects.create_user(
            "boss", password="pw-abcdef-123456", is_staff=True
        )

    def test_student_cannot_reach_the_admin_endpoint(self):
        response = self.client.get(ADMIN_DOCS, **bearer(self.student))
        self.assertEqual(response.status_code, 403)

        upload = io.BytesIO(b"%PDF-1.4 fake")
        upload.name = "x.pdf"
        response = self.client.post(
            ADMIN_DOCS, {"file": upload}, format="multipart", **bearer(self.student)
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_request_is_401_not_403(self):
        self.assertEqual(self.client.get(ADMIN_DOCS).status_code, 401)

    @mock.patch("api.admin_views.ingest_pdf")
    def test_a_corrupted_pdf_is_rejected_with_a_reason_and_never_indexed(self, ingest_pdf):
        bad = io.BytesIO(b"this is not a pdf at all")
        bad.name = "broken.pdf"

        response = self.client.post(
            ADMIN_DOCS, {"file": bad}, format="multipart", **bearer(self.admin)
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["accepted"])
        self.assertTrue(response.data["reason"])
        ingest_pdf.assert_not_called()

    def test_a_non_pdf_extension_is_rejected_before_validation(self):
        f = io.BytesIO(b"whatever")
        f.name = "notes.txt"
        response = self.client.post(
            ADMIN_DOCS, {"file": f}, format="multipart", **bearer(self.admin)
        )
        self.assertEqual(response.status_code, 400)

    @mock.patch("api.admin_views.ingest_pdf")
    @mock.patch("api.admin_views.validate_pdf")
    def test_an_accepted_pdf_is_ingested(self, validate_pdf, ingest_pdf):
        from core.ingestion.pipeline import IngestResult
        from core.ingestion.validation import ValidationResult

        validate_pdf.return_value = ValidationResult(True, "ACCEPT", "ok", {})
        ingest_pdf.return_value = IngestResult(
            accepted=True, source="good.pdf", reason="ok", chunks_added=12, chunks_total=12
        )

        good = io.BytesIO(b"%PDF-1.4 ...")
        good.name = "good.pdf"
        with mock.patch("api.admin_views.RAW_DIR", Path(tempfile.mkdtemp())):
            response = self.client.post(
                ADMIN_DOCS, {"file": good}, format="multipart", **bearer(self.admin)
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["accepted"])
        self.assertEqual(response.data["chunks_added"], 12)
        ingest_pdf.assert_called_once()
        self.assertTrue(Document.objects.filter(source="good.pdf").exists())


class DocumentDetailTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user("stud2", password="pw-abcdef-123456")
        self.admin = User.objects.create_user(
            "boss2", password="pw-abcdef-123456", is_staff=True
        )
        self.raw_dir = Path(tempfile.mkdtemp())
        self.pdf_bytes = b"%PDF-1.4 fake content for the download test"
        (self.raw_dir / "sample.pdf").write_bytes(self.pdf_bytes)
        self.document = Document.objects.create(
            source="sample.pdf",
            uploaded_by=self.admin,
            verdict="ACCEPT",
            chunk_count=5,
            page_count=3,
        )

    def test_list_includes_rich_metadata(self):
        response = self.client.get(ADMIN_DOCS, **bearer(self.admin))
        self.assertEqual(response.status_code, 200)
        row = response.data[0]
        self.assertEqual(row["source"], "sample.pdf")
        self.assertEqual(row["uploaded_by"], "boss2")
        self.assertEqual(row["chunk_count"], 5)
        self.assertEqual(row["page_count"], 3)
        self.assertEqual(row["verdict"], "ACCEPT")

    def test_student_cannot_download_or_delete(self):
        with mock.patch("api.admin_views.RAW_DIR", self.raw_dir):
            get_resp = self.client.get(document_detail(self.document.id), **bearer(self.student))
            delete_resp = self.client.delete(
                document_detail(self.document.id), **bearer(self.student)
            )

        self.assertEqual(get_resp.status_code, 403)
        self.assertEqual(delete_resp.status_code, 403)
        self.assertTrue(Document.objects.filter(id=self.document.id).exists())

    def test_unauthenticated_is_401_for_both_actions(self):
        self.assertEqual(self.client.get(document_detail(self.document.id)).status_code, 401)
        self.assertEqual(self.client.delete(document_detail(self.document.id)).status_code, 401)

    def test_download_returns_the_exact_file_bytes(self):
        with mock.patch("api.admin_views.RAW_DIR", self.raw_dir):
            response = self.client.get(document_detail(self.document.id), **bearer(self.admin))

        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content)
        self.assertEqual(content, self.pdf_bytes)

    def test_downloading_an_unknown_id_is_404(self):
        response = self.client.get(document_detail(999999), **bearer(self.admin))
        self.assertEqual(response.status_code, 404)

    @mock.patch("api.admin_views.remove_document")
    def test_delete_removes_the_record_the_file_and_calls_remove_document(self, remove_document):
        with mock.patch("api.admin_views.RAW_DIR", self.raw_dir):
            response = self.client.delete(document_detail(self.document.id), **bearer(self.admin))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Document.objects.filter(id=self.document.id).exists())
        self.assertFalse((self.raw_dir / "sample.pdf").exists())
        remove_document.assert_called_once_with("sample.pdf")

    def test_deleting_an_unknown_id_is_404(self):
        response = self.client.delete(document_detail(999999), **bearer(self.admin))
        self.assertEqual(response.status_code, 404)

    @mock.patch("api.admin_views.remove_document")
    def test_deleting_does_not_break_when_the_file_is_already_gone(self, remove_document):
        """The raw PDF and the Document row can drift (manual cleanup, a
        prior partial failure) — delete must still succeed and clean up the
        indexes rather than 500 on a missing file."""
        empty_dir = Path(tempfile.mkdtemp())
        with mock.patch("api.admin_views.RAW_DIR", empty_dir):
            response = self.client.delete(document_detail(self.document.id), **bearer(self.admin))

        self.assertEqual(response.status_code, 204)
        remove_document.assert_called_once_with("sample.pdf")
