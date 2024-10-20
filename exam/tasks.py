# import dramatiq
# from django.shortcuts import get_object_or_404
# from django.utils import timezone
# from .models import CompletedTest
#
#
# @dramatiq.actor
# def stop_test_completion(test_completion_id):
#     test_completion = get_object_or_404(CompletedTest, id=test_completion_id)
#     if not test_completion.completed:
#         test_completion.end_time = timezone.now()
#         test_completion.completed = True
#         test_completion.save()
#         return f'Test completion {test_completion_id} stopped.'
#     else:
#         return f'Test completion {test_completion_id} already completed.'
