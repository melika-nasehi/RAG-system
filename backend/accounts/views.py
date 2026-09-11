from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, StudentProfileSerializer, UserSerializer
from .tokens import TokenError, for_user, rotate_refresh


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data, **for_user(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(
            request,
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if user is None:
            return Response(
                {"detail": "نام کاربری یا گذرواژه نادرست است."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response({"user": UserSerializer(user).data, **for_user(user)})


class RefreshView(APIView):
    """Rotates the refresh token: the one presented here stops working after
    this call, and the response carries the new one the client must switch
    to (see accounts.tokens.rotate_refresh)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            tokens = rotate_refresh(request.data.get("refresh", ""))
        except TokenError as error:
            return Response({"detail": str(error)}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(tokens)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        profile = getattr(request.user, "student_profile", None)
        if profile is None:
            return Response(
                {"detail": "این حساب پروفایل دانشجویی ندارد."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)
