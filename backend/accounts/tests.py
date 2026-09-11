from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from accounts.models import StudentProfile
from accounts.tokens import ACCESS_TTL, decode, for_user

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/refresh/"
ME = "/api/auth/me/"

VALID_SIGNUP = {
    "username": "sara",
    "password": "a-strong-passphrase-42",
    "email": "sara@example.com",
    "degree_level": "bachelor",
    "entry_year": 1402,
    "field_of_study": "مهندسی کامپیوتر",
}


class RegistrationTests(APITestCase):
    def test_register_creates_user_and_profile_and_returns_tokens(self):
        response = self.client.post(REGISTER, VALID_SIGNUP, format="json")
        self.assertEqual(response.status_code, 201)

        user = User.objects.get(username="sara")
        self.assertTrue(user.check_password(VALID_SIGNUP["password"]))
        self.assertFalse(user.is_staff)

        profile = StudentProfile.objects.get(user=user)
        self.assertEqual(profile.degree_level, "bachelor")
        self.assertEqual(profile.entry_year, 1402)

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertFalse(response.data["user"]["is_admin"])

    def test_duplicate_username_is_rejected(self):
        self.client.post(REGISTER, VALID_SIGNUP, format="json")
        response = self.client.post(REGISTER, {**VALID_SIGNUP, "email": "x@y.z"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(username="sara").count(), 1)

    def test_weak_password_is_rejected_and_no_user_is_created(self):
        response = self.client.post(REGISTER, {**VALID_SIGNUP, "password": "123"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="sara").exists())


class LoginAndRefreshTests(APITestCase):
    def setUp(self):
        self.client.post(REGISTER, VALID_SIGNUP, format="json")

    def test_login_with_good_credentials_returns_tokens(self):
        response = self.client.post(
            LOGIN, {"username": "sara", "password": VALID_SIGNUP["password"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        payload = decode(response.data["access"], expected_type="access")
        self.assertEqual(payload["username"], "sara")

    def test_login_with_bad_password_is_401(self):
        response = self.client.post(
            LOGIN, {"username": "sara", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_refresh_issues_a_new_access_token(self):
        login = self.client.post(
            LOGIN, {"username": "sara", "password": VALID_SIGNUP["password"]}, format="json"
        )
        response = self.client.post(REFRESH, {"refresh": login.data["refresh"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(decode(response.data["access"])["username"], "sara")

    def test_an_access_token_is_not_accepted_as_a_refresh_token(self):
        login = self.client.post(
            LOGIN, {"username": "sara", "password": VALID_SIGNUP["password"]}, format="json"
        )
        response = self.client.post(REFRESH, {"refresh": login.data["access"]}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_refresh_rotates_and_returns_a_new_refresh_token(self):
        login = self.client.post(
            LOGIN, {"username": "sara", "password": VALID_SIGNUP["password"]}, format="json"
        )
        response = self.client.post(REFRESH, {"refresh": login.data["refresh"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("refresh", response.data)
        self.assertNotEqual(response.data["refresh"], login.data["refresh"])

    def test_a_refresh_token_cannot_be_reused_after_rotation(self):
        """The core rotation guarantee: once a refresh token has been spent,
        presenting it again — the attacker's copy of a stolen token, or the
        legitimate client retrying against a stale value — is rejected."""
        login = self.client.post(
            LOGIN, {"username": "sara", "password": VALID_SIGNUP["password"]}, format="json"
        )
        old_refresh = login.data["refresh"]

        first = self.client.post(REFRESH, {"refresh": old_refresh}, format="json")
        self.assertEqual(first.status_code, 200)

        second = self.client.post(REFRESH, {"refresh": old_refresh}, format="json")
        self.assertEqual(second.status_code, 401)

    def test_the_rotated_refresh_token_itself_works(self):
        """Rotation must not be a dead end — the new refresh token has to be
        usable for the next refresh, and so on down the chain."""
        login = self.client.post(
            LOGIN, {"username": "sara", "password": VALID_SIGNUP["password"]}, format="json"
        )
        first = self.client.post(REFRESH, {"refresh": login.data["refresh"]}, format="json")
        second = self.client.post(REFRESH, {"refresh": first.data["refresh"]}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(decode(second.data["access"])["username"], "sara")


class MeEndpointTests(APITestCase):
    def setUp(self):
        self.client.post(REGISTER, VALID_SIGNUP, format="json")
        self.user = User.objects.get(username="sara")

    def _auth(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + for_user(self.user)["access"])

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_me_returns_the_current_user_with_profile(self):
        self._auth()
        response = self.client.get(ME)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "sara")
        self.assertEqual(response.data["profile"]["degree_level"], "bachelor")

    def test_me_patch_updates_the_profile(self):
        self._auth()
        response = self.client.patch(ME, {"field_of_study": "حقوق"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.student_profile.refresh_from_db()
        self.assertEqual(self.user.student_profile.field_of_study, "حقوق")

    def test_a_tampered_token_is_rejected(self):
        token = for_user(self.user)["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token[:-4] + "AAAA")
        self.assertEqual(self.client.get(ME).status_code, 401)
