from .models import *
from accounts.models import *
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


def generate_available_periods():
    return True


def update_name(user, value):
    user.first_name = value
    user.save(update_fields=["first_name"])
    return _("Ім'я змінено")


def update_last_name(user, value):
    user.last_name = value
    user.save(update_fields=["last_name"])
    return _("Прізвище змінено")


def delete_duration(user, value):
    teacher = TeacherProfile.objects.filter(teacher=user).first()
    if teacher is None:
        raise PermissionDenied(_("Немає доступу"))
    deleted, _unused = TeacherLessonDuration.objects.filter(pk=value, teacher=teacher).delete()
    if deleted == 0:
        raise ValueError(_("Час не знайдено"))
    return _("Час видалено")


def add_duration(user, value):
    teacher = TeacherProfile.objects.get(teacher=user)
    if TeacherLessonDuration.objects.filter(teacher=teacher, duration_minutes=value).exists():
        raise ValueError(_("Такий час вже є"))
    TeacherLessonDuration.objects.create(teacher=teacher, duration_minutes=value)
    return _("Час додано")


def update_break_minutes(user, value):
    teacher = TeacherProfile.objects.get(teacher=user)
    teacher.break_minutes = value
    teacher.save(update_fields=["break_minutes"])
    return _("Час перерви між уроками змінено")


def update_teacher_bio(user, value):
    teacher = TeacherProfile.objects.get(teacher=user)
    teacher.bio = value
    teacher.save(update_fields=["bio"])
    return _("Опис змінено")


def update_student_bio(user, value):
    student = StudentProfile.objects.get(student=user)
    student.bio = value
    student.save(update_fields=["bio"])
    return _("Опис змінено")


TEACHER_ACTIONS = {
    "update_name": update_name,
    "update_last_name": update_last_name,
    "del_duration": delete_duration,
    "add_duration": add_duration,
    "update_break_minutes": update_break_minutes,
    "change_teacher_bio": update_teacher_bio,
}

STUDENT_ACTIONS = {
    "update_name": update_name,
    "update_last_name": update_last_name,
    "change_bio": update_name,
    "change_student_bio": update_student_bio,
}