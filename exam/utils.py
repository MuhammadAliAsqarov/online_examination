from django.db.models import Sum
from django.utils import timezone

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from .models import Course, Question, Test, CompletedTest, Choice, AnswerSubmission


def check_for_course(func):
    def wrapper(self, request, *args, **kwargs):
        user = request.user
        if request.user.is_authenticated and request.user.user_type == 1:
            courses = user.enrolled_courses.all()
        elif request.user.is_authenticated and request.user.user_type == 2:
            courses = Course.objects.filter(teacher=user)
        elif request.user.is_authenticated and request.user.user_type == 3:
            courses = Course.objects.all()
        else:
            return Response(data={'error': 'You dont have permissions to perform this action'},
                            status=status.HTTP_403_FORBIDDEN)

        return func(self, request, courses, *args, **kwargs)

    return wrapper


def check_course_retrieve(func):
    def wrapper(self, request, course_id, *args, **kwargs):
        user = request.user
        course = get_object_or_404(Course, pk=course_id)
        if user.user_type == 3:
            return func(self, request, course, *args, **kwargs)
        if user.user_type == 2 and course.teacher == user:
            return func(self, request, course, *args, **kwargs)
        if user.user_type == 1 and user.enrolled_courses.filter(pk=course.pk).exists():
            return func(self, request, course, *args, **kwargs)
        return Response(data={"detail": "You do not have permission to view this course."},
                        status=status.HTTP_403_FORBIDDEN)

    return wrapper


def check_for_test(func):
    def wrapper(self, request, *args, **kwargs):
        user = request.user
        if user.user_type == 1:
            courses = user.enrolled_courses.all()
            tests = Test.objects.filter(course__in=courses)
            return func(self, request, tests, *args, **kwargs)
        elif user.user_type == 2:
            tests = Test.objects.filter(creator=user)
            return func(self, request, tests, *args, **kwargs)
        elif user.user_type == 3:
            tests = Test.objects.all()
            return func(self, request, tests, *args, **kwargs)
        else:
            return Response(data={"detail": "You do not have permission to view this course."},
                            status=status.HTTP_403_FORBIDDEN)

    return wrapper


def check_permission(user, test):
    if test.course not in user.enrolled_courses.all():
        raise PermissionDenied({"detail": "Permission denied"})


def check_test(test_completion):
    if test_completion:
        if test_completion.end_time and timezone.now() > test_completion.end_time:
            raise PermissionDenied({'detail': 'Test is already over.'})
        if not test_completion.end_time or timezone.now() < test_completion.end_time:
            raise PermissionDenied({
                'detail': 'Test already started.',
                'end_time': test_completion.end_time
            })


def check_deadline(test):
    if timezone.now() > test.deadline:
        return Response({'detail': 'Deadline ended.'}, status=status.HTTP_400_BAD_REQUEST)


def start_test(user, test, start_time, end_time):
    completed_test = CompletedTest.objects.create(
        test=test,
        student=user,
        start_time=start_time,
        end_time=end_time
    )
    completed_test.end_time = completed_test.start_time + test.time_limit
    completed_test.save()
    return completed_test


def calculate_test_result(test_completion):
    answers = AnswerSubmission.objects.filter(
        question__test=test_completion.test,
        student=test_completion.student
    )
    total_count = answers.count()
    correct_answers = answers.filter(selected_choice__is_correct=True).count()
    teacher_scores = answers.aggregate(Sum('grade_by_teacher'))['grade_by_teacher__sum'] or 0
    mcq_score = (correct_answers / total_count) * 100 if total_count > 0 else 0
    overall_score = mcq_score + teacher_scores

    return {
        'total_questions': total_count,
        'mcq_score': mcq_score,
        'teacher_scores': teacher_scores,
        'overall_score': overall_score,
    }


def process_answer(question, answer_data, test_completion):
    if question.question_type == 'mcq':
        process_mcq_answer(question, answer_data, test_completion)
    elif question.question_type == 'open':
        process_open_answer(question, answer_data, test_completion)
    else:
        raise ValidationError({'detail': 'Invalid question type.'})


def process_mcq_answer(question, answer_data, test_completion):
    choice_ids = answer_data.get('choice_ids', [])
    for choice_id in choice_ids:
        choice = get_object_or_404(Choice, id=choice_id, question=question)
        AnswerSubmission.objects.create(
            student=test_completion.student,
            submission_time=test_completion,
            question=question,
            selected_choice=choice
        )


def process_open_answer(question, answer_data, test_completion):
    answer_text = answer_data.get('answer_text', '')
    AnswerSubmission.objects.create(
        student=test_completion.student,
        submission_time=test_completion,
        question=question,
        answer_text=answer_text
    )
