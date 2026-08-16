from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from accounts.models import TeacherLessonDuration, TeacherStudent, BalanceAction


class AddDurationForm(forms.ModelForm):
    class Meta:
        model = TeacherLessonDuration
        fields = ("duration_minutes", "coefficient")

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
                "Такий час вже існує!"))


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
            'placeholder': 'Сума (наприклад -100 або 100)',
        }),
    )

    class Meta:
        model = BalanceAction
        fields = ("amount", "comment")
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'student-balance-comment',
                'placeholder': "Коментар (необов'язково)",
            }),
        }
