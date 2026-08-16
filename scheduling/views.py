from django.shortcuts import render, redirect, reverse, get_object_or_404
from datetime import date, datetime
from django.utils import timezone as django_timezone
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from pyexpat.errors import messages
from django.http import Http404
from accounts.decorators import teacher_only, student_only
from django.contrib import messages
from django.db import transaction

from accounts.models import TeacherStudent, BalanceAction, TeacherLessonDuration
from .services import get_schedule_info, get_week_info, sorted_regular_lessons, process_balance_action, \
    generate_slots_for_intervals
from .models import TeacherProfile, Slot, StudentProfile, Weekday, TeacherWeekdayAvailability, TeacherDateAvailability, \
    RegularLesson
from .forms import SlotForm, SlotChangeForm, TeacherWeekdayAvailabilityForm, TeacherDateAvailabilityForm, \
    RegularLessonForm


@teacher_only
def teacher_schedule(request):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    selected_day_str = request.GET.get('day')

    additional_info = get_schedule_info(selected_day_str=selected_day_str, user=request.user, user_role='teacher')
    form = SlotForm(teacher=teacher_profile)

    for day in additional_info['week']:
        for slot in day['slots']:
            if slot.status == Slot.Status.CANCELLED:
                last_refund = slot.actions.filter(action_type=BalanceAction.ActionType.REFUND).order_by(
                    '-created').first()
                slot.last_refund_amount = abs(last_refund.amount) if last_refund else None
            else:
                slot.last_refund_amount = None

    return render(request, "scheduling/schedule_teacher.html", {
        **additional_info,
        'form': form
    })


@teacher_only
def add_slot(request, date):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    if request.method == 'POST':
        form = SlotForm(request.POST, teacher=teacher_profile)
        form.instance.teacher = teacher_profile
        form.instance.date = date
        if form.is_valid():
            obj = form.save(commit=False)
            if form.cleaned_data['student']:
                teacher_student = TeacherStudent.objects.filter(student=form.cleaned_data['student']).first()
                coefficient = form.cleaned_data['duration'].coefficient
                obj.price = round(teacher_student.price * coefficient, 2)
            try:
                obj.save()
            except ValidationError:
                messages.error(request, "Цей час вже зайнятий іншим заняттям")
            else:
                messages.success(request, "Додано")
                return redirect(f"{reverse('scheduling:teacher_schedule')}?day={date}")
    else:
        form = SlotForm(teacher=teacher_profile)

    additional_info = get_schedule_info(selected_day_str=date, user=request.user, user_role='teacher')
    return render(request, "scheduling/schedule_teacher.html", {
        **additional_info,
        'form': form,
        'form_mode': 'Додати заняття',
        'form_day_label': date,
        'back_day': date,
    })


@teacher_only
def update_slot(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    slot = get_object_or_404(Slot, id=pk, teacher=teacher_profile)

    if request.method == 'POST':
        form = SlotChangeForm(request.POST, instance=slot, teacher=teacher_profile)
        if form.is_valid():
            obj = form.save(commit=False)
            if form.cleaned_data['student']:
                teacher_student = TeacherStudent.objects.filter(student=form.cleaned_data['student']).first()
                coefficient = form.cleaned_data['duration'].coefficient
                obj.price = round(teacher_student.price * coefficient, 2)
            try:
                obj.save()
            except ValidationError:
                messages.error(request, "Цей час вже зайнятий іншим заняттям")
            else:
                messages.success(request, "Оновлено")
                return redirect(f"{reverse('scheduling:teacher_schedule')}?day={slot.date}")
    else:
        form = SlotChangeForm(instance=slot, teacher=teacher_profile)

    additional_info = get_schedule_info(selected_day_str=slot.date.isoformat(), user=request.user, user_role='teacher')
    return render(request, "scheduling/schedule_teacher.html", {
        **additional_info,
        'form': form,
        'form_mode': 'Редагувати заняття',
        'form_day_label': slot.date.isoformat(),
        'back_day': slot.date.isoformat(),
    })


@teacher_only
def week_availability(request):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    slots = TeacherWeekdayAvailability.objects.filter(teacher=teacher_profile)
    date_overrides = TeacherDateAvailability.objects.filter(teacher=teacher_profile, date__gte=date.today())

    week = []
    for day_value, day_label in Weekday.choices:
        week.append({
            "day_value": day_value,
            "day_label": day_label,
            "slots": [slot for slot in slots if slot.day_of_week == day_value]
        })

    return render(request, 'scheduling/week_availability/teacher_week_availability.html', {
        'week': week,
        'date_overrides': date_overrides
    })


@student_only
def student_schedule(request):
    selected_day_str = request.GET.get('day')

    additional_info = get_schedule_info(selected_day_str=selected_day_str, user=request.user, user_role='student')
    return render(request, "scheduling/schedule_student.html", {
        **additional_info,
    })


@teacher_only
def confirm_payment_by_teacher(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    slot = get_object_or_404(Slot, id=pk, teacher=teacher_profile)
    Slot.objects.filter(id=slot.id).update(paid_status=Slot.PaidStatus.CONFIRMED)
    return redirect(f"{reverse('scheduling:teacher_schedule')}?day={slot.date}")


@student_only
def confirm_payment_by_student(request, pk):
    teacher_profile = get_object_or_404(StudentProfile, student=request.user)
    slot = get_object_or_404(Slot, id=pk, student=teacher_profile)
    Slot.objects.filter(id=slot.id).update(paid_status=Slot.PaidStatus.PAID)
    return redirect(f"{reverse('scheduling:student_schedule')}?day={slot.date}")


@teacher_only
def cancel_slot(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    slot = get_object_or_404(Slot, id=pk, teacher=teacher_profile)

    if slot.paid_status == Slot.PaidStatus.CONFIRMED and slot.student:
        with transaction.atomic():
            process_balance_action(teacher=teacher_profile,
                                   student=slot.student,
                                   slot=slot,
                                   action=BalanceAction.ActionType.REFUND,
                                   amount=slot.price)
            slot.status = Slot.Status.CANCELLED
            slot.save()
        messages.success(request, "Урок скасовано, кошти повернуто учню!")
    else:
        slot.status = Slot.Status.CANCELLED
        slot.save()
    return redirect(f"{reverse('scheduling:teacher_schedule')}?day={slot.date}")


@teacher_only
def restore_slot(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    slot = get_object_or_404(Slot, id=pk, teacher=teacher_profile)

    if slot.paid_status == Slot.PaidStatus.CONFIRMED and slot.student:
        try:
            with transaction.atomic():
                process_balance_action(teacher=teacher_profile,
                                       student=slot.student,
                                       slot=slot,
                                       action=BalanceAction.ActionType.RESTORE,
                                       amount=-(slot.price))
                slot.status = Slot.Status.BOOKED
                slot.save()
        except ValidationError as e:
            if 'start_time' in getattr(e, 'message_dict', {}):
                messages.error(request, "Не можна відновити — цей час вже зайнятий іншим уроком")
            else:
                messages.error(request, "У учня недостатньо коштів для відновлення уроку")
        else:
            messages.success(request, "Урок відновлено, кошти учня списані!")
    else:
        try:
            slot.status = Slot.Status.BOOKED
            slot.save()
        except ValidationError:
            messages.error(request, "Не можна відновити — цей час вже зайнятий іншим уроком")
        else:
            messages.success(request, "Урок відновлено!")
    return redirect(f"{reverse('scheduling:teacher_schedule')}?day={slot.date}")


@teacher_only
def create_week_availability(request, week_number):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    if week_number not in Weekday.values:
        raise Http404
    if request.method == 'POST':
        form = TeacherWeekdayAvailabilityForm(request.POST)
        form.instance.teacher = teacher_profile
        form.instance.day_of_week = week_number
        if form.is_valid():
            messages.success(request, "Додано")
            form.save()
            return redirect("scheduling:week_availability")
    else:
        form = TeacherWeekdayAvailabilityForm()
    additional_info = get_week_info(teacher_profile)

    return render(request, 'scheduling/week_availability/week_add_form.html', {
        **additional_info,
        'form': form,
        'day_label': Weekday.choices[week_number][1]
    })


@teacher_only
def update_week_availability(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    to_update = get_object_or_404(TeacherWeekdayAvailability, id=pk, teacher=teacher_profile)
    if request.method == 'POST':
        form = TeacherWeekdayAvailabilityForm(request.POST, instance=to_update)
        if form.is_valid():
            form.save()
            messages.success(request, "Оновлено")
            return redirect("scheduling:week_availability")
    else:
        form = TeacherWeekdayAvailabilityForm(instance=to_update)
    additional_info = get_week_info(teacher_profile)

    return render(request, 'scheduling/week_availability/week_update_form.html', {
        **additional_info,
        'form': form,
        'day_label': Weekday.choices[to_update.day_of_week][1],
    })


@teacher_only
def delete_week_availability(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    to_delete = TeacherWeekdayAvailability.objects.filter(id=pk, teacher=teacher_profile).delete()
    messages.success(request, "Видалено")
    return redirect("scheduling:week_availability")


@teacher_only
def create_date_availability(request):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    if request.method == 'POST':
        form = TeacherDateAvailabilityForm(request.POST)
        form.instance.teacher = teacher_profile
        if form.is_valid():
            form.save()
            messages.success(request, "Додано")
            return redirect("scheduling:week_availability")
    else:
        form = TeacherDateAvailabilityForm()
    additional_info = get_week_info(teacher_profile)
    return render(request, 'scheduling/week_availability/date_add_form.html', {
        **additional_info,
        'form': form,
    })


@teacher_only
def update_date_availability(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    to_update = get_object_or_404(TeacherDateAvailability, id=pk, teacher=teacher_profile)
    if request.method == 'POST':
        form = TeacherDateAvailabilityForm(request.POST, instance=to_update)
        if form.is_valid():
            form.save()
            messages.success(request, "Оновлено")
            return redirect("scheduling:week_availability")
    else:
        form = TeacherDateAvailabilityForm(instance=to_update)
    additional_info = get_week_info(teacher_profile)
    return render(request, 'scheduling/week_availability/date_update_form.html', {
        **additional_info,
        'form': form,
        'date': to_update.date,
    })


@teacher_only
def delete_date_availability(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    to_delete = TeacherDateAvailability.objects.filter(id=pk, teacher=teacher_profile).delete()
    messages.success(request, "Видалено")
    return redirect("scheduling:week_availability")


@teacher_only
def regular_lessons_info(request):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    lessons = sorted_regular_lessons(teacher=teacher_profile)

    return render(request, "scheduling/regular_lessons/info.html", {
        **lessons,
    })


@teacher_only
def regular_lessons_create(request, week_number):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    if week_number not in Weekday.values:
        raise Http404
    if request.method == 'POST':
        form = RegularLessonForm(request.POST, teacher=teacher_profile)
        form.instance.teacher = teacher_profile
        form.instance.day_of_week = week_number
        if form.is_valid():
            form.save()
            messages.success(request, "Додано")
            return redirect("scheduling:regular_lessons_info")
    else:
        form = RegularLessonForm(teacher=teacher_profile)

    lessons = sorted_regular_lessons(teacher=teacher_profile)
    return render(request, "scheduling/regular_lessons/create.html", {
        **lessons,
        "form": form,
        'day_label': Weekday.choices[week_number][1]
    })


@teacher_only
def regular_lessons_update(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    to_update = get_object_or_404(RegularLesson, id=pk, teacher=teacher_profile)
    if request.method == 'POST':
        form = RegularLessonForm(request.POST,
                                 instance=to_update,
                                 teacher=teacher_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Оновлено")
            return redirect("scheduling:regular_lessons_info")
    else:
        form = RegularLessonForm(instance=to_update, teacher=teacher_profile)

    lessons = sorted_regular_lessons(teacher=teacher_profile)
    return render(request, "scheduling/regular_lessons/update.html", {
        **lessons,
        "form": form,
        'day_label': Weekday.choices[to_update.day_of_week][1],
    })


@teacher_only
def regular_lessons_delete(request, pk):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    to_delete = RegularLesson.objects.filter(id=pk, teacher=teacher_profile).delete()
    messages.success(request, "Видалено")
    return redirect("scheduling:regular_lessons_info")


@student_only
def student_choose_teahcer(request, date):
    parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
    student_profile = get_object_or_404(StudentProfile, student=request.user)
    teachers = (TeacherStudent.objects.filter(student=student_profile)
                .select_related('teacher')
                .prefetch_related('teacher__lesson_teacher'))
    additional_info = get_schedule_info(selected_day_str=date, user=request.user, user_role='student')

    return render(request, "scheduling/student_booking/choose_teacher.html", {
        **additional_info,
        "teachers": teachers,
        "date": parsed_date,
    })


@student_only
def student_show_availability(request, date, teacher_id, duration_id):
    parsed_date = datetime.strptime(date, '%Y-%m-%d').date()

    if parsed_date < django_timezone.now().date():
        messages.error(request, "Не можна обрати дату в минулому")
        return redirect("scheduling:student_schedule")

    duration = get_object_or_404(TeacherLessonDuration, id=duration_id, teacher_id=teacher_id)
    teacher_profile = duration.teacher
    break_minutes = teacher_profile.break_minutes
    slot_minutes = duration.duration_minutes

    busy_intervals = list(
        Slot.objects.filter(teacher=teacher_profile, date=parsed_date)
        .exclude(status=Slot.Status.CANCELLED)
        .values("date", "start_time", "end_time")
    )

    date_availability = TeacherDateAvailability.objects.filter(teacher=teacher_profile, date=parsed_date)

    if date_availability.exists():
        free_intervals = list(date_availability.values("date", "start_time", "end_time"))
    else:
        weekday_availability = TeacherWeekdayAvailability.objects.filter(
            teacher=teacher_profile,
            day_of_week=parsed_date.weekday(),
        )
        free_intervals = [
            {"date": parsed_date, "start_time": wa.start_time, "end_time": wa.end_time}
            for wa in weekday_availability
        ]

    try:
        result = generate_slots_for_intervals(
            teacher=teacher_profile,
            free_intervals=free_intervals,
            busy_intervals=busy_intervals,
            slot_minutes=slot_minutes,
            break_minutes=break_minutes,
        )
    except ValidationError:
        messages.error(request, "Жаль, але для цієї дати немає слотів")
        return redirect("scheduling:student_schedule")

    additional_info = get_schedule_info(selected_day_str=date, user=request.user, user_role='student')

    return render(request, "scheduling/student_booking/show_availability.html", {
        **additional_info,
        "date": parsed_date,
        "teacher": teacher_profile,
        "duration": duration,
        "duration_minutes": slot_minutes,
        "available_slots": result["slots"],
    })


@student_only
def student_confirm_booking(request):
    if request.method != 'POST':
        return redirect('scheduling:student_schedule')

    teacher_id = request.POST.get('teacher_id')
    duration_id = request.POST.get('duration_id')
    date_str = request.POST.get('date')
    start_time_str = request.POST.get('start_time')
    end_time_str = request.POST.get('end_time')

    teacher_profile = get_object_or_404(TeacherProfile, pk=teacher_id)
    student_profile = get_object_or_404(StudentProfile, student=request.user)
    duration_obj = get_object_or_404(TeacherLessonDuration, pk=duration_id, teacher=teacher_profile)

    teacher_student = get_object_or_404(
        TeacherStudent,
        teacher=teacher_profile,
        student=student_profile,
    )
    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    start_time = datetime.strptime(start_time_str, '%H:%M').time()
    end_time = datetime.strptime(end_time_str, '%H:%M').time()

    price = round(teacher_student.price * duration_obj.coefficient, 2)
    try:
        with transaction.atomic():
            locked_slots = list(
                Slot.objects.select_for_update().filter(
                    teacher=teacher_profile,
                    date=parsed_date,
                ).exclude(status=Slot.Status.CANCELLED)
            )
            has_overlap = any(
                s.start_time < end_time and s.end_time > start_time
                for s in locked_slots
            )
            if has_overlap:
                messages.error(request, "На жаль, цей час вже зайнято. Спробуйте інший.")
                return redirect(f"{reverse('scheduling:student_schedule')}?day={parsed_date}")
            slot = Slot(
                teacher=teacher_profile,
                student=student_profile,
                date=parsed_date,
                start_time=start_time,
                end_time=end_time,
                status=Slot.Status.BOOKED,
                price=price,
            )
            slot.save()
    except ValidationError:
        messages.error(request, "На жаль, цей час вже зайнято. Спробуйте інший.")
        return redirect(f"{reverse('scheduling:student_schedule')}?day={parsed_date}")
    messages.success(request, "Урок успішно заброньовано!")
    return redirect(f"{reverse('scheduling:student_schedule')}?day={parsed_date}")
