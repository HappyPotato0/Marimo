from datetime import date, datetime, timedelta
from django.shortcuts import get_object_or_404
from django.http import Http404

from django.db.models import F
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

from accounts.models import TeacherProfile, StudentProfile, TeacherStudent, BalanceAction
from .models import TeacherWeekdayAvailability, TeacherDateAvailability, RegularLesson, Slot, Weekday


def get_schedule_info(selected_day_str, user, user_role):
    try:
        selected_day = date.fromisoformat(selected_day_str) if selected_day_str else date.today()
    except ValueError:
        selected_day = date.today()
    week_start = selected_day - timedelta(days=selected_day.weekday())
    week_end = week_start + timedelta(days=6)

    if user_role == 'teacher':
        user = get_object_or_404(TeacherProfile, teacher=user)
        slots = Slot.objects.filter(teacher=user, date__range=[week_start, week_end])
    elif user_role == 'student':
        user = get_object_or_404(StudentProfile, student=user)
        slots = Slot.objects.filter(student=user, date__range=[week_start, week_end])
    else:
        raise Http404

    week = []
    for i in range(7):
        current_day = week_start + timedelta(days=i)
        week.append({
            "date": current_day,
            "weekday_name": Weekday(current_day.weekday()).label,
            "slots": [slot for slot in slots if slot.date == current_day],
        })

    return {
        'selected_day': selected_day,
        'week_start': week_start,
        'week_end': week_end,
        'week': week,
        'previous_week': week_start - timedelta(days=7),
        'next_week': week_start + timedelta(days=7),
    }


def get_week_info(teacher):
    slots = TeacherWeekdayAvailability.objects.filter(teacher=teacher)
    date_overrides = TeacherDateAvailability.objects.filter(teacher=teacher, date__gte=date.today())

    week = []
    for day_value, day_label in Weekday.choices:
        week.append({
            "day_value": day_value,
            "day_label": day_label,
            "slots": [slot for slot in slots if slot.day_of_week == day_value]
        })
    return {
        'week': week,
        'date_overrides': date_overrides,
    }


def sorted_regular_lessons(teacher):
    lessons = RegularLesson.objects.filter(teacher=teacher)

    week = []

    for day_value, day_label in Weekday.choices:
        week.append({
            "day_value": day_value,
            "day_label": day_label,
            "slots": [lesson for lesson in lessons if lesson.day_of_week == day_value]
        })

    return {
        'week': week,
    }


def register_action(teacher, student, ):
    return True


def process_balance_action(
        teacher: TeacherProfile,
        student: StudentProfile,
        action: BalanceAction.ActionType,
        amount: Decimal,
        slot=None) -> None:
    """
    Просто застосовує зміну балансу
    Викликати лише з transaction.atomic()!!!
    """
    teacher_student = TeacherStudent.objects.select_for_update().get(
        teacher=teacher, student=student)

    if teacher_student.balance + amount < 0:
        raise ValidationError(_("Недостатньо коштів для цієї операції!"))

    teacher_student.balance = F('balance') + amount
    teacher_student.save(update_fields=['balance'])

    BalanceAction.objects.create(
        teacher_student=teacher_student,
        action_type=action,
        amount=amount,
        slot=slot,
    )


def generate_slots_for_intervals(
        teacher,
        free_intervals,
        busy_intervals,
        slot_minutes,
        break_minutes,
):
    """
        Генерує доступні слоти на основі вільних та зайнятих інтервалів.

        Вхід:
        - teacher: об'єкт з teacher.id
        - free_intervals: список інтервалів (date або weekday)
        - busy_intervals: список зайнятих інтервалів (date обов'язковий)
        - slot_minutes: тривалість слоту
        - break_minutes: перерва між слотами

        Вихід:
        {
            "slots": [...],
            "remaining_intervals": [...],
        }

        Приклад:
        free: 09:00–13:00
        busy: 10:00–10:30 (+break)

        → генеруються слоти поза зайнятими вікнами
        """
    free_intervals = list(free_intervals)
    busy_intervals = list(busy_intervals)

    if not free_intervals:
        raise ValidationError(_("Не надано вільних інтервалів."))

    slot_delta = timedelta(minutes=slot_minutes)
    break_delta = timedelta(minutes=break_minutes)
    step_delta = slot_delta + break_delta

    slots = []
    remaining_intervals = []
    busy_ranges_by_date = {}

    for interval in busy_intervals:
        interval_date = interval["date"]
        start_time = interval["start_time"]
        end_time = interval["end_time"]

        if start_time >= end_time:
            raise ValidationError(
                _("Час завершення зайнятого інтервалу має бути пізніше за час початку: %(start)s - %(end)s.") % {
                    'start': start_time,
                    'end': end_time,
                }
            )

        busy_start = datetime.combine(interval_date, start_time)
        busy_end = datetime.combine(interval_date, end_time) + break_delta

        busy_ranges_by_date.setdefault(interval_date, []).append((busy_start, busy_end))

    for interval_date, ranges in busy_ranges_by_date.items():
        ranges.sort(key=lambda x: x[0])

        merged = []
        for start_dt, end_dt in ranges:
            if not merged:
                merged.append([start_dt, end_dt])
            else:
                last_start, last_end = merged[-1]
                if start_dt <= last_end:
                    merged[-1][1] = max(last_end, end_dt)
                else:
                    merged.append([start_dt, end_dt])

        busy_ranges_by_date[interval_date] = [(start, end) for start, end in merged]

    base_date = None
    if busy_intervals:
        base_date = busy_intervals[0]["date"]
    else:
        base_date = datetime.today().date()

    for interval in free_intervals:
        if "date" in interval and interval["date"] is not None:
            interval_date = interval["date"]
        elif "weekday" in interval:
            interval_date = base_date
        else:
            raise ValidationError(_("Вільний інтервал повинен містити 'date' або 'weekday'."))

        start_time = interval["start_time"]
        end_time = interval["end_time"]

        if start_time >= end_time:
            raise ValidationError(
                _("Час завершення вільного інтервалу має бути пізніше за час початку: %(start)s - %(end)s.") % {
                    'start': start_time,
                    'end': end_time,
                }
            )
        free_start = datetime.combine(interval_date, start_time)
        free_end = datetime.combine(interval_date, end_time)

        day_busy = busy_ranges_by_date.get(interval_date, [])
        remaining_segments = [(free_start, free_end)]

        for busy_start, busy_end in day_busy:
            new_segments = []

            for seg_start, seg_end in remaining_segments:
                if busy_end <= seg_start or busy_start >= seg_end:
                    new_segments.append((seg_start, seg_end))
                    continue

                if busy_start > seg_start:
                    new_segments.append((seg_start, busy_start))

                if busy_end < seg_end:
                    new_segments.append((busy_end, seg_end))

            remaining_segments = new_segments

        for seg_start, seg_end in remaining_segments:
            if seg_start < seg_end:
                remaining_intervals.append({
                    "teacher": teacher.id,
                    "date": interval_date,
                    "start_time": seg_start.time(),
                    "end_time": seg_end.time(),
                })

        for seg_start, seg_end in remaining_segments:
            current_dt = seg_start

            while current_dt + slot_delta <= seg_end:
                slot_start_dt = current_dt
                slot_end_dt = current_dt + slot_delta

                slots.append({
                    "teacher": teacher.id,
                    "date": interval_date,
                    "start_time": slot_start_dt.time(),
                    "end_time": slot_end_dt.time(),
                })

                current_dt += step_delta

    return {
        "slots": slots,
        "remaining_intervals": remaining_intervals,
    }
