from django.db import models
from django.conf import settings

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

import zoneinfo
from django.urls import reverse

TIMEZONE_CHOICES = sorted(
    (tz, tz) for tz in zoneinfo.available_timezones()
)


class BaseProfile(models.Model):
    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default="Europe/Kyiv",
    )
    bio = models.TextField(blank=True, null=True)  #

    class Meta:
        abstract = True


class TeacherProfile(BaseProfile):
    teacher = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    break_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.teacher.first_name} {self.teacher.last_name}"

    def get_absolute_url(self):
        return reverse("accounts:teacher_details", kwargs={"pk": self.pk})


class StudentProfile(BaseProfile):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name}"

    def get_absolute_url(self):
        return reverse("accounts:student_details", kwargs={"pk": self.pk})


class TeacherStudent(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    balance = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("teacher", "student")  #

    def __str__(self):
        return f"{self.teacher.teacher} {self.student.student}"


class TeacherLessonDuration(models.Model):
    teacher = models.ForeignKey(TeacherProfile,
                                on_delete=models.CASCADE,
                                related_name="lesson_teacher")
    coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    duration_minutes = models.PositiveIntegerField()

    class Meta:
        unique_together = ("teacher", "duration_minutes")
        ordering = ["teacher", "duration_minutes"]

    def __str__(self):
        return f"{self.duration_minutes} хв · ×{self.coefficient}"


class BalanceAction(models.Model):
    class ActionType(models.TextChoices):
        CREDIT = 'credit', 'Нарахування вчителем'
        DEBIT = 'debit', 'Списання за урок'
        REFUND = 'refund', 'Скасований урок'
        RESTORE = 'restore', 'Відновлення уроку'
        WITHDRAWAL = 'withdrawal', 'Списання вчителем'

    teacher_student = models.ForeignKey(TeacherStudent, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    amount = models.IntegerField()  # завжди зі знаком: +150 / -150
    slot = models.ForeignKey('scheduling.Slot', on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='actions')
    comment = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
