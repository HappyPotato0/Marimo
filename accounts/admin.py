from django.contrib import admin
from .models import TeacherProfile, StudentProfile, TeacherStudent, TeacherLessonDuration, BalanceAction


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ["teacher", "break_minutes", "timezone", "bio"]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ["student", "timezone", "bio"]


@admin.register(TeacherStudent)
class TeacherStudentAdmin(admin.ModelAdmin):
    list_display = ["teacher", "student", "balance"]


@admin.register(TeacherLessonDuration)
class TeacherLessonDurationAdmin(admin.ModelAdmin):
    list_display = ["teacher", "duration_minutes", "coefficient"]


@admin.register(BalanceAction)
class BalanceActionAdmin(admin.ModelAdmin):
    list_display = ["teacher_student", "action_type", "amount", "slot", "created", "comment"]
    list_filter = ["created", "action_type"]
