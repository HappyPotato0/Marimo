from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def invite_student(message, email):
    mail_sent = send_mail(
        subject='New Student!',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=email
    )
    return mail_sent