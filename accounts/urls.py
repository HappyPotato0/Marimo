from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_page, name='home_page'),
    path('profile/<str:title>/', views.profile_details, name='profile_details'),
    path('profile/', views.profile_details, name='profile_details'),
    path('config_profile/<str:action>/', views.config_profile, name='config_profile'),
    path('config_lesson_duration/', views.config_lesson_duration, name='config_lesson_duration'),

]

# Teachers
urlpatterns += [
    path('my_students/', views.my_students, name='my_students'),
    path('teacher/student/<int:pk>/', views.student_details, name='student_details'),

]

# Students
urlpatterns += [
    path('my_teachers/', views.my_teachers, name='my_teachers'),
    path('student/teacher/<int:pk>/', views.teacher_details, name='teacher_details'),
]
