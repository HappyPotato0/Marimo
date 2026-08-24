from functools import wraps
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from .models import *
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

def teacher_only(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _("Потрібно авторизуватися"))
            return redirect('login')
        try:
            profile = TeacherProfile.objects.get(teacher=request.user)
        except TeacherProfile.DoesNotExist:
            messages.error(request, _("Профіль не знайдено"))
            return redirect('home_page')

        if not profile:
            messages.error(request, _("Доступ дозволений лише викладачу"))
            return redirect('home_page')

        return view_func(request, *args, **kwargs)

    return _wrapped


def student_only(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _("Потрібно авторизуватися"))
            return redirect('login')
        try:
            profile = StudentProfile.objects.get(student=request.user)
        except TeacherProfile.DoesNotExist:
            messages.error(request, _("Профіль не знайдено"))
            return redirect('home_page')

        if not profile:
            messages.error(request, _("Доступ дозволений лише учню"))
            return redirect('home_page')

        return view_func(request, *args, **kwargs)

    return _wrapped