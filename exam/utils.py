from django.db.models import Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404
from exceptions.error_codes import ErrorCodes
from exceptions.exception import CustomApiException
from .models import Course, Question, Test, CompletedTest, Choice, AnswerSubmission
from .utils_cache import get_overall_score_cache_key
from django.core.cache import cache


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
            raise CustomApiException(error_code=ErrorCodes.FORBIDDEN.value)

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
        raise CustomApiException(error_code=ErrorCodes.FORBIDDEN.value)

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
            raise CustomApiException(error_code=ErrorCodes.FORBIDDEN.value)

    return wrapper


def check_permission(user, test):
    if test.course not in user.enrolled_courses.all():
        raise CustomApiException(error_code=ErrorCodes.FORBIDDEN.value)


def check_test(test_completion):
    if test_completion:
        if test_completion.end_time and timezone.now() > test_completion.end_time:
            test_completion.completed = True
            test_completion.save()
            raise CustomApiException(error_code=ErrorCodes.FORBIDDEN.value, message={'detail': 'Test already over'})
        if not test_completion.end_time or timezone.now() < test_completion.end_time:
            raise CustomApiException(error_code=ErrorCodes.FORBIDDEN.value,
                                     message={'detail': 'Test already started.',
                                              'end_time': test_completion.end_time})


def check_deadline(test):
    if timezone.now() > test.deadline:
        raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT.value, message={'detail': 'Deadline ended.'})


def answers_func(answers, test_completion):
    for answer_data in answers:
        question = get_object_or_404(Question, id=answer_data['question_id'])
        process_answer(question, answer_data, test_completion)
    test_completion.completed = True
    test_completion.save()
    result = calculate_test_result(test_completion)
    test_completion.score = result['overall_score']
    test_completion.save()
    return result


def start_test(user, test, start_time, end_time):
    completed_test = CompletedTest.objects.create(
        test=test,
        student=user,
        start_time=start_time,
        end_time=end_time,
        completed=False
    )
    completed_test.end_time = completed_test.start_time + test.time_limit
    completed_test.save()
    return completed_test


def calculate_test_result(test_completion):
    cache_key = get_overall_score_cache_key(test_completion.test.id, test_completion.student.id)
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    answers = AnswerSubmission.objects.filter(
        question__test=test_completion.test,
        student=test_completion.student
    )
    total_count = answers.count()
    correct_answers = answers.filter(selected_choice__is_correct=True).count()
    teacher_scores = answers.aggregate(Sum('grade_by_teacher'))['grade_by_teacher__sum'] or 0
    mcq_score = (correct_answers / total_count) * 100 if total_count > 0 else 0
    overall_score = mcq_score + teacher_scores

    result_data = {
        'total_questions': total_count,
        'mcq_score': mcq_score,
        'teacher_scores': teacher_scores,
        'overall_score': overall_score,
    }
    cache.set(cache_key, result_data, timeout=60 * 15)
    return result_data


def process_answer(question, answer_data, test_completion):
    if question.question_type == 'mcq':
        process_mcq_answer(question, answer_data, test_completion)
    elif question.question_type == 'open':
        process_open_answer(question, answer_data, test_completion)
    else:
        raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT.value,
                                 message={'detail': 'Invalid question type.'})


def process_mcq_answer(question, answer_data, test_completion):
    choice_id = answer_data.get('choice_id')
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


def all_score_func(results):
    all_scores = []
    for result in results:
        test_result = calculate_test_result(result)
        overall_score = test_result['overall_score']
        all_scores.append(overall_score)
        result.score = overall_score
        result.save()
    return all_scores
