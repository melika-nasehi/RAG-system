
from django.conf import settings
from django.db import models


class DegreeLevel(models.TextChoices):

    ASSOCIATE = "associate", "کاردانی"
    BACHELOR = "bachelor", "کارشناسی"
    MASTER = "master", "کارشناسی ارشد"
    DOCTORATE = "doctorate", "دکتری"


class StudentProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    degree_level = models.CharField(
        max_length=20,
        choices=DegreeLevel.choices,
    )

    # Persian academic years (e.g. 1402), not Gregorian — matches how the
    # source documents phrase eligibility ("ورودی ۱۴۰۲ و بعد از آن").
    entry_year = models.PositiveSmallIntegerField(
        help_text="سال ورود به دانشگاه، به شمسی (مثال: ۱۴۰۲)",
    )

    field_of_study = models.CharField(max_length=200, blank=True)


    is_on_probation = models.BooleanField(
        default=False,
        help_text="آیا در نیمسال گذشته مشروط شده‌اید؟",
    )

    last_semester_gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="معدل نیمسال گذشته (اختیاری)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.get_degree_level_display()} — {self.entry_year}"