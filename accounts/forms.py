from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

from accounts.models import TeacherLessonDuration, TeacherStudent, BalanceAction, StudentProfile
from django.utils.translation import gettext_lazy as _


class AddDurationForm(forms.ModelForm):
    class Meta:
        model = TeacherLessonDuration
        fields = ("duration_minutes", "coefficient")
        labels = {
            "duration_minutes": _("Тривалість уроку (хв)"),
            "coefficient": _("Коефіцієнт"),
        }
        widgets = {
            "duration_minutes": forms.NumberInput(attrs={
                'placeholder': '0',
                'min': '1',
            }),
            "coefficient": forms.NumberInput(attrs={
                'placeholder': '1,0',
                'step': '0.1',
                'min': '0.1',
            }),
        }

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        self.teacher = teacher

    def clean(self):
        cleaned_data = super().clean()
        overlaps = cleaned_data.get("duration_minutes")
        teacher = self.teacher
        if TeacherLessonDuration.objects.filter(
                teacher=teacher,
                duration_minutes=overlaps):
            self.add_error("duration_minutes", ValidationError(
                _("Такий час вже існує!")))


class ChangePriceForm(forms.ModelForm):
    class Meta:
        model = TeacherStudent
        fields = ("price",)


class BalanceActionForm(forms.ModelForm):
    amount = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(-50000), MaxValueValidator(50000)],
        widget=forms.NumberInput(attrs={
            'class': 'student-balance-input',
            'placeholder': _('Сума (наприклад -100 або 100)'),
        }),
    )

    class Meta:
        model = BalanceAction
        fields = ("amount", "comment")
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'student-balance-comment',
                'placeholder': _("Коментар (необов'язково)"),
            }),
        }


class AddStudentForm(forms.ModelForm):
    price = forms.IntegerField(
        label=_("Ціна за урок"),
        required=False,
        min_value=0,
        max_value=10000,
        widget=forms.NumberInput(attrs={
            'placeholder': _("Введіть ціну за 1 урок (не обов'язково)"),
        }),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            "email": forms.EmailInput()
        }
        labels = {
            "first_name": _("Ім'я"),
            "last_name": _("Прізвище"),
            "email": _("Email учня"),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = self.cleaned_data.get('email')
        if not email:
            self.add_error("email", ValidationError(
                _("Введіть пошту!")))
