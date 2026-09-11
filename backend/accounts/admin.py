from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "degree_level", "entry_year", "field_of_study", "is_on_probation")
    list_filter = ("degree_level", "entry_year", "is_on_probation")
    search_fields = ("user__username", "field_of_study")
