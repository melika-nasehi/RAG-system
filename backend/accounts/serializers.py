from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import DegreeLevel, StudentProfile

User = get_user_model()


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            "degree_level",
            "entry_year",
            "field_of_study",
            "is_on_probation",
            "last_semester_gpa",
        ]


class UserSerializer(serializers.ModelSerializer):
    # Admin vs. student is Django's is_staff flag — admins manage the corpus,
    # students only ask questions. Exposed read-only so the frontend can gate
    # the upload UI.
    is_admin = serializers.BooleanField(source="is_staff", read_only=True)
    profile = StudentProfileSerializer(source="student_profile", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "is_admin", "profile"]


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    email = serializers.EmailField(required=False, allow_blank=True)

    degree_level = serializers.ChoiceField(choices=DegreeLevel.choices)
    entry_year = serializers.IntegerField(min_value=1300, max_value=1500)
    field_of_study = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("این نام کاربری قبلاً ثبت شده است.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data.get("email", ""),
        )
        StudentProfile.objects.create(
            user=user,
            degree_level=validated_data["degree_level"],
            entry_year=validated_data["entry_year"],
            field_of_study=validated_data.get("field_of_study", ""),
        )
        return user
