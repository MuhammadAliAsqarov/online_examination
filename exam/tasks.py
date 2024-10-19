from celery import shared_task
from django.utils import timezone
from .models import CompletedTest


@shared_task
def stop_test_completion(test_completion_id):
    try:
        test_completion = CompletedTest.objects.get(id=test_completion_id)
        if not test_completion.completed:
            test_completion.end_time = timezone.now()
            test_completion.completed = True
            test_completion.save()
            return f'Test completion {test_completion_id} stopped.'
        else:
            return f'Test completion {test_completion_id} already completed.'
    except CompletedTest.DoesNotExist:
        return f'Test completion {test_completion_id} not found.'
