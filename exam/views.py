from unittest import TestResult

from django.db.models import Avg, Max, Min
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Course, CompletedTest, AnswerSubmission, Question, Test, User, Choice, TestProgress
from .permissions import is_admin, is_teacher, is_student
from .serializers import CourseCreateSerializer, UserRegisterSerializer, UserLoginSerializer, TestSerializer, \
    CourseSerializer, QuestionSerializer
from .utils import check_for_course, check_course_retrieve, check_for_test, check_deadline, start_test, \
    create_question, calculate_test_result


class UserViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        request_body=UserRegisterSerializer,
        responses={201: 'User registered successfully', 400: 'Invalid input'},
        tags=['auth']
    )
    @is_admin
    def register(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(data={'username': user.username}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=UserLoginSerializer,
        tags=['auth'],
        responses={
            200: openapi.Response('Login successful', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                    'access': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )),
            401: 'Invalid credentials',
            400: 'Invalid input'
        }
    )
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = User.objects.filter(username=username).first()

        if not user or not user.check_password(password):
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class CourseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new course with a specified teacher",
        manual_parameters=[],
        request_body=CourseCreateSerializer,
        responses={201: CourseCreateSerializer()}
    )
    @is_admin
    def create(self, request):
        serializer = CourseCreateSerializer(data=request.data, context={'request': request})

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Retrieve details of a course by its ID",
        responses={200: CourseSerializer(), 404: 'Course not found'}
    )
    @check_course_retrieve
    def retrieve(self, request, course):
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="List all courses",
        responses={200: CourseSerializer(many=True), 404: 'No courses found'}
    )
    @check_for_course
    def list(self, request, courses):
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['title', 'course', 'time_limit', 'deadline', 'questions'],
            properties={
                'title': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The title or name of the test'
                ),
                'course': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of the course the test belongs to'
                ),
                'time_limit': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Time limit for the test in HH:MM:SS format',
                    example='01:30:00'
                ),
                'deadline': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATETIME,
                    description='Deadline for completing the test in ISO 8601 format',
                    example='2024-12-31T23:59:59'
                ),
                'questions': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        required=['question_text', 'question_type'],  # Marking required fields
                        properties={
                            'question_text': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Text of the question'
                            ),
                            'question_type': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Type of the question: multiple-choice (mcq) or open-ended (open)',
                                enum=['mcq', 'open']
                            ),
                            'choices': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    required=['choice_text'],  # Required for choice_text
                                    properties={
                                        'choice_text': openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description='Text of the choice (only for MCQ questions)'
                                        ),
                                        'is_correct': openapi.Schema(
                                            type=openapi.TYPE_BOOLEAN,
                                            description='Indicates if the choice is the correct answer (only for MCQ questions)'
                                        )
                                    }
                                ),
                                description='List of choices for MCQ questions (ignored for open-ended questions)',
                                example=[
                                    {"choice_text": "Choice 1", "is_correct": True},
                                    {"choice_text": "Choice 2", "is_correct": False}
                                ]
                            )
                        }
                    ),
                    description='List of questions to include in the test. For open-ended questions, omit the choices.'
                )
            }
        ),
        responses={
            201: openapi.Response(
                description='Test created successfully',
                schema=TestSerializer()
            ),
            400: openapi.Response(
                description='Invalid input data'
            )
        }
    )
    @is_teacher
    def create(self, request):
        data = request.data
        test_serializer = TestSerializer(data=data, context={'request': request})
        if not test_serializer.is_valid():
            return Response(test_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        test = test_serializer.save()
        questions_data = data.get('questions', [])
        for question_data in questions_data:
            create_question(test, question_data)
        response_data = TestSerializer(test).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="List all tests",
        responses={200: TestSerializer(many=True)}
    )
    @check_for_test
    def list(self, request, tests):
        serializer = TestSerializer(tests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Access a test for the student.",
        responses={200: 'Test accessed and started', 400: 'Test unavailable'}
    )
    def access_test(self, request, pk=None):
        user = request.user
        test = get_object_or_404(Test, pk=pk)
        check_deadline(test)
        test_completion = CompletedTest.objects.filter(test=test, student=user).first()
        if test_completion:
            if test_completion.end_time and timezone.now() > test_completion.end_time:
                return Response({'detail': 'Test is already over.'}, status=status.HTTP_400_BAD_REQUEST)
            if not test_completion.end_time or timezone.now() < test_completion.end_time:
                return Response({
                    'detail': 'Test already started.',
                    'end_time': test_completion.end_time
                }, status=status.HTTP_200_OK)
        start_time = timezone.now()
        end_time = start_time + test.time_limit
        test_completion = start_test(user, test, start_time, end_time)
        return Response({
            'detail': 'Test accessed and started',
            'end_time': test_completion.end_time
        }, status=status.HTTP_200_OK)


class QuestionsTestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="List all questions for a particular test with pagination",
        responses={200: QuestionSerializer(many=True)}
    )
    def list(self, request, test_id):
        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)
        paginator = self.pagination_class()
        paginated_questions = paginator.paginate_queryset(questions, request)
        serializer = QuestionSerializer(paginated_questions, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'answer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The student\'s answer (text for open questions or choice ID for MCQ)'
                )
            },
            required=['answer'],
        ),
        operation_description="Submit an answer to a particular question",
        responses={200: "Answer recorded", 400: "Bad Request"}
    )
    def answer_question(self, request, test_id, question_id):
        question = get_object_or_404(Question, id=question_id, test_id=test_id)
        test_progress, created = TestProgress.objects.get_or_create(
            test_id=test_id, student=request.user, completed=False
        )
        answer_data = request.data.get('answer')
        if question.question_type == 'mcq':
            choice = get_object_or_404(Choice, id=answer_data, question=question)
            AnswerSubmission.objects.create(
                question=question,
                student=request.user,
                selected_choice=choice
            )
        elif question.question_type == 'open':
            AnswerSubmission.objects.create(
                question=question,
                student=request.user,
                answer_text=answer_data
            )
        return Response({"message": "Answer recorded"}, status=status.HTTP_200_OK)


class TestCompletionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Finish the test and calculate the result",
        responses={200: "Test completed", 400: "Bad Request"}
    )
    def finish_test(self, request, test_id):
        test_completion = get_object_or_404(TestProgress, test_id=test_id, student=request.user, completed=False)
        test_completion.completed = True
        test_completion.end_time = timezone.now()
        test_completion.save()
        result = calculate_test_result(test_completion)
        CompletedTest.objects.create(
            test=test_completion.test,
            student=request.user,
            score=result['score'],
            start_time=test_completion.start_time,
            end_time=test_completion.end_time
        )
        return Response({"message": "Test completed", "result": result}, status=status.HTTP_200_OK)