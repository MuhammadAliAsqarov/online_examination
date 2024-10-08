from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from exam.models import Test, Submission, Course, Question


class TestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create a new test",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'course_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the course'),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Title of the test'),
                'time_limit': openapi.Schema(type=openapi.TYPE_STRING, description='Time limit for the test'),
                'deadline': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                           description='Deadline for the test'),
            },
        ),
        responses={201: openapi.Response('Test created', schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING),
            'test_id': openapi.Schema(type=openapi.TYPE_INTEGER)}))}
    )
    def create_test(self, request):
        course_id = request.data['course_id']
        title = request.data['title']
        time_limit = request.data['time_limit']
        deadline = request.data['deadline']

        course = Course.objects.get(id=course_id)
        test = Test.objects.create(
            course=course,
            title=title,
            creator=request.user,
            time_limit=time_limit,
            deadline=deadline
        )
        test.save()
        return Response(data={'message': 'Test created', 'test_id': test.id}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Submit answers for a test",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'answers': openapi.Schema(type=openapi.TYPE_OBJECT,
                                          additional_properties=openapi.Schema(type=openapi.TYPE_STRING),
                                          description='Answers for the test'),
            },
        ),
        responses={200: openapi.Response('Test submitted successfully')}
    )
    def submit_test(self, request, test_id):
        test = Test.objects.get(id=test_id)
        student = request.user
        answers = request.data['answers']

        submission = Submission.objects.create(
            student=student,
            test=test,
            answers=answers
        )
        submission.save()
        return Response(data={'message': 'Test submitted successfully'}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Grade a submitted test",
        responses={200: openapi.Response('Test graded', schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING), 'grade': openapi.Schema(type=openapi.TYPE_NUMBER)}))}
    )
    def grade_test(self, request, submission_id):
        submission = Submission.objects.get(id=submission_id)
        answers = submission.answers
        correct_answers = 0
        total_questions = 0

        # Automatic grading logic for MCQs
        for question_id, answer in answers.items():
            question = Question.objects.get(id=question_id)
            if question.is_mcq and question.options['correct_option'] == answer:
                correct_answers += 1
            total_questions += 1

        grade = (correct_answers / total_questions) * 100
        submission.grade = grade
        submission.is_graded = True
        submission.save()

        return Response({'message': 'Test graded', 'grade': grade}, status=status.HTTP_200_OK)
