from django.contrib import admin
from .models import TeacherWeekdayAvailability, TeacherDateAvailability, Slot, RegularLesson


@admin.register(TeacherWeekdayAvailability)
class TeacherWeekdayAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["teacher", "day_of_week", "start_time", "end_time"]


@admin.register(TeacherDateAvailability)
class TeacherDateAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["teacher", "date", "start_time", "end_time"]


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ["teacher", "student", "date", "status", "start_time", "end_time"]


@admin.register(RegularLesson)
class RegularLessonAdmin(admin.ModelAdmin):
    list_display = ["teacher", "student", "day_of_week"]
