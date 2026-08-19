from django.shortcuts import render, redirect, get_object_or_404
import secrets

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.core.mail import send_mail

from .forms import AddDurationForm, ChangePriceForm, BalanceActionForm, AddStudentForm
from .services import STUDENT_ACTIONS, TEACHER_ACTIONS
from .decorators import teacher_only, student_only
from .models import TeacherLessonDuration, TeacherStudent, BalanceAction
from accounts.models import TeacherProfile, StudentProfile
from django.contrib.auth.models import User


def home_page(request):
    return render(request, 'accounts/home_page.html')


@login_required
def profile_details(request, title):
    if title == 'teacher':
        teacher_profile = TeacherProfile.objects.filter(teacher=request.user).first()
        if teacher_profile is None:
            raise PermissionDenied("Ви не є вчителем")

        if request.method == 'POST':
            form = AddDurationForm(request.POST, teacher=teacher_profile)
            form.instance.teacher = teacher_profile
            if form.is_valid():
                form.save()
                return redirect('accounts:profile_details', 'teacher')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
        else:
            form = AddDurationForm(teacher=teacher_profile)

        durations = TeacherLessonDuration.objects.filter(teacher=teacher_profile)

        return render(request, 'accounts/profile/profile_teacher.html', {
            'teacher': teacher_profile,
            'durations': durations,
            'form': form
        })

    elif title == 'student':
        student_profile = StudentProfile.objects.filter(student=request.user).first()
        if student_profile is None:
            raise PermissionDenied("Ви не є учнем")
        return render(request, 'accounts/profile/profile_student.html', {
            'student': student_profile,
        })

    raise PermissionDenied("Невідома роль")


@login_required
def config_profile(request, action):
    if action in TEACHER_ACTIONS:
        role = "teacher"
        handler = TEACHER_ACTIONS.get(action)
    elif action in STUDENT_ACTIONS:
        role = "student"
        handler = STUDENT_ACTIONS.get(action)
    else:
        messages.error(request, 'Профіль не знайдено')
        return redirect('accounts:home_page')

    if request.method == 'POST':
        if handler is None:
            messages.error(request, 'Невідома дія')
            return redirect('accounts:profile_details', role)

        value = request.POST.get('value')
        try:
            success_message = handler(request.user, value)
            messages.success(request, success_message)
        except (ValueError, PermissionError) as e:
            messages.error(request, str(e))

    return redirect('accounts:profile_details', role)


@teacher_only
def config_lesson_duration(request):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    if request.method == 'POST':
        form = AddDurationForm(request.POST, teacher=teacher_profile)
        form.instance.teacher = teacher_profile
        if form.is_valid():
            form.save()
            return redirect("scheduling:week_availability")
    else:
        return redirect("scheduling:week_availability")


@teacher_only
def my_students(request):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    students = TeacherStudent.objects.filter(teacher=teacher_profile).select_related('student', 'student__student')

    return render(request, 'accounts/my_students.html', {
        'students': students
    })


@teacher_only
def student_details(request, pk):
    teacher_profile = TeacherProfile.objects.get(teacher=request.user)
    teacher_student = get_object_or_404(
        TeacherStudent.objects.select_related('student', 'student__student'),
        teacher=teacher_profile,
        student__pk=pk
    )
    price_form = ChangePriceForm(instance=teacher_student)
    balance_form = BalanceActionForm()

    if request.method == 'POST':
        if "submit_price" in request.POST:
            price_form = ChangePriceForm(request.POST, instance=teacher_student)
            if price_form.is_valid():
                price_form.save()
                messages.success(request, "Ціну за урок змінено")
                return redirect('accounts:student_details', pk)

        elif 'submit_balance' in request.POST:
            balance_form = BalanceActionForm(request.POST)
            if balance_form.is_valid():
                raw_amount = balance_form.cleaned_data['amount']
                if raw_amount is None or raw_amount == 0:
                    balance_form.add_error('amount', 'Вкажіть суму для зміни балансу')
                else:
                    with transaction.atomic():
                        locked_ts = TeacherStudent.objects.select_for_update().get(pk=teacher_student.pk)
                        if locked_ts.balance + raw_amount < 0:
                            messages.error(request, 'У учня недостатньо коштів!')
                        else:
                            balance_action = balance_form.save(commit=False)
                            balance_action.teacher_student = locked_ts
                            balance_action.action_type = 'credit' if raw_amount > 0 else 'withdrawal'
                            balance_action.amount = raw_amount
                            balance_action.save()
                            locked_ts.balance += raw_amount
                            locked_ts.save(update_fields=['balance'])
                            messages.success(request, "Баланс змінено")
                            return redirect('accounts:student_details', pk)

    transaction_history = BalanceAction.objects.filter(teacher_student=teacher_student)
    return render(request, 'accounts/student_detail.html', {
        'teacher_student': teacher_student,
        'transaction_history': transaction_history,
        'form': price_form,
        'balance_form': balance_form,
    })


@student_only
def my_teachers(request):
    student_profile = StudentProfile.objects.get(student=request.user)
    teachers = TeacherStudent.objects.filter(student=student_profile).select_related('teacher', 'teacher__teacher')

    return render(request, 'accounts/my_teachers.html', {
        'teachers': teachers
    })


@student_only
def teacher_details(request, pk):
    student_profile = StudentProfile.objects.get(student=request.user)
    teacher_student = get_object_or_404(
        TeacherStudent.objects.select_related('student', 'student__student'),
        student=student_profile,
        teacher__pk=pk
    )

    transaction_history = BalanceAction.objects.filter(teacher_student=teacher_student)
    return render(request, 'accounts/teacher_detail.html', {
        'teacher_student': teacher_student,
        'transaction_history': transaction_history,
    })


@teacher_only
def add_student(request):
    teacher_profile = get_object_or_404(TeacherProfile, teacher=request.user)
    students = TeacherStudent.objects.filter(teacher=teacher_profile).select_related('student', 'student__student')

    if request.method == 'POST':
        form = AddStudentForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            user_created, student_created, link_created = False, False, False

            '''1. Перевірити User'''
            check_user = User.objects.filter(email=email).first()
            if not check_user:
                random_password = secrets.token_urlsafe(12)
                check_user = User.objects.create_user(
                    email=email,
                    username=email,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    password=random_password,
                )
                user_created = True

            '''2. Перевірити StudentProfile'''
            check_student = StudentProfile.objects.filter(student=check_user).first()
            if not check_student:
                check_student  = StudentProfile.objects.create(student=check_user)
                student_created = True

            '''3. Перевірити TeacherStudent'''
            link = TeacherStudent.objects.filter(teacher=teacher_profile, student=check_student).first()
            if not link:
                link = TeacherStudent.objects.create(
                    teacher=teacher_profile,
                    student=check_student,
                    price=form.cleaned_data['price'],
                )
                link_created = True

            if user_created:
                message = f'''Тебе запросив учитель: {teacher_profile.teacher.first_name} {teacher_profile.teacher.last_name}! Твій тимчасовий пароль: {random_password} на сайті https://www.iwannabepotato.com/'''
            elif student_created:
                message = f'''Тебе зробили учнем, твій новий викладач: {teacher_profile.teacher.first_name} {teacher_profile.teacher.last_name} на сайті https://www.iwannabepotato.com/'''
            elif link_created:
                message = f'''Тебе додали до учнів {teacher_profile.teacher.first_name} {teacher_profile.teacher.last_name} на сайті https://www.iwannabepotato.com/'''
            else:
                messages.warning(request, "Цей учень же існує в вашому списку!")
                return redirect('accounts:my_students')
            from .tasks import invite_student
            invite_student.delay(message=message,email=[email])


            #messages.success(request, "Учня додано, йому прийде лист з запрошенням на вказану пошту!")
            return redirect("accounts:my_students")
    else:
        form = AddStudentForm()

    return render(request, 'accounts/profile/add_student.html', {
        'students': students,
        'form': form,
    })
