from django.urls import path
from scheduling import views

app_name = 'scheduling'

urlpatterns = [
    path('teacher_schedule/', views.teacher_schedule, name='teacher_schedule'),
    path('student_schedule/', views.student_schedule, name='student_schedule'),
    path('week_availability/', views.week_availability, name='week_availability'),
]

# Управління розкладом та слотами
urlpatterns += [
    path('add_slot/<str:date>/', views.add_slot, name='add_slot'),
    path('update_slot/<int:pk>/', views.update_slot, name='update_slot'),
    path('confirm_payment_by_teacher/<int:pk>', views.confirm_payment_by_teacher, name='confirm_payment_by_teacher'),
    path('confirm_payment_by_student/<int:pk>', views.confirm_payment_by_student, name='confirm_payment_by_student'),
    path('teacher/cancel_slot/<int:pk>', views.cancel_slot, name='cancel_slot'),
    path('teacher/restore_slot/<int:pk>', views.restore_slot, name='restore_slot'),
]

# Управління тижневим розкладом
urlpatterns += [
    path('teacher/create_week_availability/<int:week_number>/', views.create_week_availability,
         name='create_week_availability'),
    path('teacher/update_week_availability/<int:pk>/', views.update_week_availability,
         name='update_week_availability'),
    path('teacher/delete_week_availability/<int:pk>/', views.delete_week_availability,
         name='delete_week_availability'),
    path('teacher/create_date_availability/', views.create_date_availability,
         name='create_date_availability'),
    path('teacher/update_date_availability/<int:pk>/', views.update_date_availability,
         name='update_date_availability'),
    path('teacher/delete_date_availability/<int:pk>/', views.delete_date_availability,
         name='delete_date_availability'),
]

# Управління регулярними слотами для вчителя
urlpatterns += [
    path('regular_lessons_info/', views.regular_lessons_info, name='regular_lessons_info'),
    path('regular_lessons_create/<int:week_number>/', views.regular_lessons_create, name='regular_lessons_create'),
    path('regular_lessons_update/<int:pk>/', views.regular_lessons_update, name='regular_lessons_update'),
    path('regular_lessons_delete/<int:pk>/', views.regular_lessons_delete, name='regular_lessons_delete'),
]

# Управління букінгу уроку для студента
urlpatterns += [
    path('teacher_choice/<str:date>/', views.student_choose_teahcer, name='teacher_choice'),
    path('show_availability/<str:date>/<int:teacher_id>/<int:duration_id>/', views.student_show_availability,
         name='show_availability'),
    path('student_confirm_booking/', views.student_confirm_booking,
         name='student_confirm_booking'),

]
