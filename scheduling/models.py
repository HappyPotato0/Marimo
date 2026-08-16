from django.db import models
from accounts.models import TeacherProfile, StudentProfile

from django.core.exceptions import ValidationError


class Weekday(models.IntegerChoices):
    "Вибір дня тижня"
    MON = 0, "Понеділок"
    TUE = 1, "Вівторок"
    WED = 2, "Середа"
    THU = 3, "Четвер"
    FRI = 4, "П'ятниця"
    SAT = 5, "Субота"
    SUN = 6, "Неділя"


class TeacherWeekdayAvailability(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(
                "Час закінчення більший за час початку!"
            )
        overlaps = TeacherWeekdayAvailability.objects.filter(
            teacher=self.teacher,
            day_of_week=self.day_of_week,
        ).filter(
            start_time__lt=self.end_time,
            end_time__gt=self.start_time)

        if self.pk:
            overlaps = overlaps.exclude(pk=self.pk)

        if overlaps.exists():
            raise ValidationError(
                "Цей час пересікається з існуючим!"
            )

    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = (('teacher', 'day_of_week', 'start_time'),)  #


class TeacherDateAvailability(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(
                "Час закінчення більший за час початку!"
            )
        overlaps = TeacherDateAvailability.objects.filter(
            teacher=self.teacher,
            date=self.date
        ).filter(
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        )

        if self.pk:
            overlaps = overlaps.exclude(pk=self.pk)

        if overlaps.exists():
            raise ValidationError(
                "Цей час пересікається з існуючим!"
            )

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = (('teacher', 'date', 'start_time'),)  #


class Slot(models.Model):
    class Status(models.TextChoices):
        BOOKED = 'booked', 'Заброньовано'
        CANCELLED = 'cancelled', 'Скасовано'
        BREAK = 'break', 'Перерва'

    class PaidStatus(models.TextChoices):
        PENDING = 'pending', 'Очікує оплати'
        PAID = 'paid', 'Оплачено учнем'
        CONFIRMED = 'confirmed', 'Підтверджено вчителем'

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(choices=Status.choices, default=Status.BOOKED, max_length=15)
    paid_status = models.CharField(choices=PaidStatus.choices, default=PaidStatus.PENDING, max_length=15, null=True,
                                   blank=True)
    comment = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(
                {'end_time': "Час закінчення більший за час початку!"})

        if self.status != Slot.Status.CANCELLED:
            overlaps = Slot.objects.filter(
                teacher=self.teacher,
                date=self.date
            ).exclude(status=Slot.Status.CANCELLED).filter(
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )

            if self.pk:
                overlaps = overlaps.exclude(pk=self.pk)

            if overlaps.exists():
                raise ValidationError(
                    {'start_time': "Цей час пересікається з існуючим!"})

    class Meta:
        ordering = ['date', 'start_time']


class RegularLesson(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(
                {'end_time': "Час закінчення більший за час початку!"})
        overlaps = RegularLesson.objects.filter(
            teacher=self.teacher,
            day_of_week=self.day_of_week
        ).filter(
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        )
        if self.pk:
            overlaps = overlaps.exclude(pk=self.pk)

        if overlaps.exists():
            raise ValidationError(
                {'start_time': "Цей час пересікається з існуючим!"})

    class Meta:
        ordering = ['teacher', 'student', 'day_of_week']
