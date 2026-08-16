from celery import shared_task

@shared_task
def add():
    a = "hello world"
    return a