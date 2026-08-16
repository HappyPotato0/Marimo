from functools import wraps
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from .models import *

def teacher_only(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Потрібно авторизуватися")
        try:
            profile = TeacherProfile.objects.get(teacher=request.user)
        except TeacherProfile.DoesNotExist:
            return HttpResponseForbidden("Профіль не знайдено")

        if not profile:
            return HttpResponseForbidden("Доступ дозволений лише викладачу")

        return view_func(request, *args, **kwargs)

    return _wrapped


def student_only(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Потрібно авторизуватися")
        try:
            profile = StudentProfile.objects.get(student=request.user)
        except TeacherProfile.DoesNotExist:
            return HttpResponseForbidden("Профіль не знайдено")

        if not profile:
            return HttpResponseForbidden("Доступ дозволений лише учню")

        return view_func(request, *args, **kwargs)

    return _wrapped
