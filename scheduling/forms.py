from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import TeacherStudent, StudentProfile, TeacherProfile, TeacherLessonDuration
from .models import Slot, TeacherWeekdayAvailability, TeacherDateAvailability, Weekday, RegularLesson


class SlotForm(forms.ModelForm):
    duration = forms.ModelChoiceField(
        queryset=TeacherLessonDuration.objects.none(),
        required=False,
        label=_("Тривалість уроку"),
    )

    class Meta:
        model = Slot
        fields = ('status', 'student', 'start_time', 'end_time', 'comment')
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'})
        }
        labels = {
            "status": _("Статус"),
            "student": _("Учень"),
            "start_time": _("Час початку"),
            "end_time": _("Час завершення"),
            "comment": _("Коментар"),
        }

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)

        student_ids = TeacherStudent.objects.filter(teacher=teacher).values_list('student_id', flat=True)
        self.fields['student'].queryset = StudentProfile.objects.filter(pk__in=student_ids)

        self.fields['status'].choices = [
            (Slot.Status.BREAK, Slot.Status.BREAK.label),
            (Slot.Status.BOOKED, Slot.Status.BOOKED.label),
        ]

        self.fields['duration'].queryset = TeacherLessonDuration.objects.filter(teacher=teacher)

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        student = cleaned_data.get('student')
        duration = cleaned_data.get('duration')

        if status == Slot.Status.BREAK and student:
            self.add_error('student', _("Ви не можете обирати учня, якщо тип Слоту 'Перерва'"))
        if student and not duration:
            self.add_error('duration', _("Оберіть тривалість уроку!"))


class SlotChangeForm(forms.ModelForm):
    duration = forms.ModelChoiceField(
        queryset=TeacherLessonDuration.objects.none(),
        required=False,
        label=_("Тривалість уроку"),
    )

    class Meta:
        model = Slot
        fields = ('student', 'start_time', 'end_time', 'comment')
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'})
        }
        labels = {
            "student": _("Учень"),
            "start_time": _("Час початку"),
            "end_time": _("Час завершення"),
            "comment": _("Коментар"),
        }

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        student_ids = TeacherStudent.objects.filter(teacher=teacher).values_list('student_id', flat=True)
        self.fields['student'].queryset = StudentProfile.objects.filter(pk__in=student_ids)
        self.fields['duration'].queryset = TeacherLessonDuration.objects.filter(teacher=teacher)

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        duration = cleaned_data.get('duration')

        if student and not duration:
            self.add_error('duration', _("Оберіть тривалість уроку"))


class TeacherWeekdayAvailabilityForm(forms.ModelForm):
    class Meta:
        model = TeacherWeekdayAvailability
        fields = ('start_time', 'end_time')
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'})
        }
        labels = {
            "start_time": _("Час початку"),
            "end_time": _("Час завершення"),
        }


class TeacherDateAvailabilityForm(forms.ModelForm):
    class Meta:
        model = TeacherDateAvailability
        fields = ('date', 'start_time', 'end_time')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'})
        }
        labels = {
            "date": _("Дата"),
            "start_time": _("Час початку"),
            "end_time": _("Час завершення"),
        }


class RegularLessonForm(forms.ModelForm):
    class Meta:
        model = RegularLesson
        fields = ('student', 'start_time', 'end_time')
        widgets = {'start_time': forms.TimeInput(attrs={'type': 'time'}),
                   'end_time': forms.TimeInput(attrs={'type': 'time'})}
        labels = {
            "student": _("Учень"),
            "start_time": _("Час початку"),
            "end_time": _("Час завершення"),
        }

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        teacher = TeacherStudent.objects.filter(teacher=teacher).values_list(
            'student_id', flat=True
        )
        students = StudentProfile.objects.filter(id__in=teacher)
        self.fields['student'].queryset = StudentProfile.objects.filter(pk__in=students)
