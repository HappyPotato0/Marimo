from django.urls import path, include
from . import views
from django.utils.translation import gettext_lazy as _

app_name = 'accounts'

urlpatterns = [
    path('', views.home_page, name='home_page'),
    path(_('profile/<str:title>/'), views.profile_details, name='profile_details'),
    path(_('profile/'), views.profile_details, name='profile_details'),
    path(_('config_profile/<str:action>/'), views.config_profile, name='config_profile'),
    path(_('config_lesson_duration/'), views.config_lesson_duration, name='config_lesson_duration'),

]

# Teachers
urlpatterns += [
    path(_('my_students/'), views.my_students, name='my_students'),
    path(_('teacher/student/<int:pk>/'), views.student_details, name='student_details'),
    path(_('add_student/'), views.add_student, name='add_student'),

]

# Students
urlpatterns += [
    path(_('my_teachers/'), views.my_teachers, name='my_teachers'),
    path(_('student/teacher/<int:pk>/'), views.teacher_details, name='teacher_details'),
]
