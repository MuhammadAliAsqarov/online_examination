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
from exam.models import Course, Result, Answer, Question, Test, Profile, TestCompletion, Choice
from exam.serializers import CourseSerializer, TestSerializer, ResultSerializer, AnswerSerializer, QuestionSerializer, \
    UserRegistrationSerializer, UserLoginSerializer


class Pagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


pagination_params = openapi.Parameter(
    'page',
    openapi.IN_QUERY,
    description="Page number to retrieve.",
    type=openapi.TYPE_INTEGER,
    required=False,
)

page_size_param = openapi.Parameter(
    'page_size',
    openapi.IN_QUERY,
    description="Number of questions per page.",
    type=openapi.TYPE_INTEGER,
    required=False,
)

question_response = openapi.Response(
    'Success',
    QuestionSerializer(many=True),
)


class UserViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        request_body=UserRegistrationSerializer,
        responses={201: 'User registered successfully', 400: 'Invalid input'},
        tags=['auth']
    )
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'username': user.username}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        if serializer.is_valid(raise_exception=True):
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = Profile.objects.filter(username=username).first()

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
        responses={200: CourseSerializer(many=True)}
    )
    def list(self, request):
        user = request.user

        if user.user_type == 1:  # Teacher
            courses = Course.objects.filter(teacher=user)
        elif user.user_type == 2:  # Student
            courses = user.courses.all()
        else:
            return Response({"detail": "Invalid user type."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        responses={200: CourseSerializer()}
    )
    def retrieve(self, request, pk=None):
        course = get_object_or_404(Course, pk=pk)
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Test name'),
                'course': openapi.Schema(type=openapi.TYPE_INTEGER, description='Course ID'),
                'time_limit': openapi.Schema(type=openapi.TYPE_STRING, description='Time limit for the test'),
                'deadline': openapi.Schema(type=openapi.TYPE_STRING, description='Test deadline'),
                'questions': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'question_text': openapi.Schema(type=openapi.TYPE_STRING, description='Question text'),
                            'question_type': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Type of question (mcq/open)',
                                enum=['mcq', 'open']
                            ),
                            'choices': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'choice_text': openapi.Schema(type=openapi.TYPE_STRING),
                                        'is_correct': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                    }
                                ),
                                description='Choices for MCQ type questions (optional for open-ended questions)'
                            )
                        }
                    ),
                    description='List of questions to be added to the test'
                )
            }
        ),
        responses={201: TestSerializer(), 400: "Bad Request"}
    )
    def create(self, request):
        data = request.data
        test_serializer = TestSerializer(data=data, context={'request': request})
        if not test_serializer.is_valid():
            return Response(test_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        test = test_serializer.save()
        questions_data = data.get('questions', [])
        for question_data in questions_data:
            question_text = question_data.get('question_text')
            question_type = question_data.get('question_type')
            question = Question.objects.create(
                test=test,
                question_text=question_text,
                question_type=question_type
            )
            if question_type == 'mcq':
                choices_data = question_data.get('choices', [])
                for choice_data in choices_data:
                    Choice.objects.create(
                        question=question,
                        choice_text=choice_data.get('choice_text'),
                        is_correct=choice_data.get('is_correct', False)
                    )
        response_data = TestSerializer(test).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: TestSerializer(many=True)}
    )
    def list(self, request):
        user = request.user
        if user.user_type == 1:  # Teacher
            tests = Test.objects.filter(creator=user)
        elif user.user_type == 2:  # Student
            courses = user.courses.all()  # Get courses the student is enrolled in
            tests = Test.objects.filter(course__in=courses)  # Get tests from those courses
        else:
            return Response({"detail": "Invalid user type."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TestSerializer(tests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Access a test for the student.",
        responses={200: 'Test accessed and started', 400: 'Test unavailable'}
    )
    def access_test(self, request, pk=None):
        test = get_object_or_404(Test, pk=pk)
        if timezone.now() > test.deadline:
            return Response({'detail': 'Test is already over.'}, status=status.HTTP_400_BAD_REQUEST)
        test_completion = TestCompletion.objects.filter(test=test, student=request.user).first()
        if test_completion:
            if timezone.now() > test_completion.end_time:
                return Response({'detail': 'Test is already over.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'detail': 'Test already started.', 'end_time': test_completion.end_time},
                                status=status.HTTP_200_OK)
        test_completion = TestCompletion.objects.create(
            test=test,
            student=request.user,
            start_time=timezone.now()
        )
        test_completion.end_time = test_completion.start_time + test.time_limit
        test_completion.save()

        return Response({
            'detail': 'Test accessed and started',
            'end_time': test_completion.end_time
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        responses={200: 'Test finished successfully', 400: 'Invalid request'},
    )
    def finish_test(self, request, pk=None):
        test_completion = get_object_or_404(TestCompletion, test_id=pk, student=request.user)
        if test_completion.end_time is not None:
            return Response({"detail": "Test already finished."}, status=status.HTTP_400_BAD_REQUEST)
        test_completion.end_time = timezone.now()
        test_completion.save()
        result, created = Result.objects.get_or_create(test=test_completion.test, student=request.user)
        result.calculate_mcq_score()
        return Response({"detail": "Test finished successfully.", "score": result.score}, status=status.HTTP_200_OK)


class QuestionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=QuestionSerializer,
        responses={201: QuestionSerializer(), 400: "Bad Request"}
    )
    def create(self, request):
        serializer = QuestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="List Questions",
        operation_description="Retrieve a list of questions for a specific test, with optional pagination.",
        manual_parameters=[pagination_params, page_size_param],
        responses={
            status.HTTP_200_OK: question_response,
            status.HTTP_404_NOT_FOUND: "Test not found."
        },
    )
    def list(self, request, test_pk=None):
        questions = Question.objects.filter(test=test_pk)
        paginator = Pagination()
        paginated_questions = paginator.paginate_queryset(questions, request)

        serializer = QuestionSerializer(paginated_questions, many=True)
        return paginator.get_paginated_response(serializer.data)


class ResultViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: ResultSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        test = get_object_or_404(Test, pk=test_pk)
        if request.user.user_type == 1:
            if test.creator != request.user:
                return Response({'detail': 'You are not authorized to view results for this test.'},
                                status=status.HTTP_403_FORBIDDEN)
            results = Result.objects.filter(test=test)
        elif request.user.user_type == 2:
            results = Result.objects.filter(test=test, student=request.user)

        else:
            return Response({'detail': 'You are not authorized to view these results.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = ResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnswerViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Submit an answer to a question",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'question': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the question being answered'),
                'answer_text': openapi.Schema(type=openapi.TYPE_STRING,
                                              description='Text of the answer (required for MCQ and open-ended questions)')
            },
            required=['question', 'answer_text']
        ),
    )
    def create(self, request):
        student = request.user
        data = request.data.copy()
        data['student'] = student.id
        question = get_object_or_404(Question, id=data['question'])
        test = question.test
        test_completion = TestCompletion.objects.filter(test=test, student=student).first()
        if not test_completion or timezone.now() > test_completion.end_time:
            return Response({"detail": "You cannot submit answers after the test has finished."},
                            status=status.HTTP_400_BAD_REQUEST)
        if Answer.objects.filter(student=student, question=question).exists():
            return Response({"detail": "You have already answered this question."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AnswerSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            answer = serializer.save()
            return Response(AnswerSerializer(answer).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TestStatisticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'average_score': openapi.Schema(type=openapi.TYPE_NUMBER),
                'highest_score': openapi.Schema(type=openapi.TYPE_NUMBER),
                'lowest_score': openapi.Schema(type=openapi.TYPE_NUMBER),
                'total_students': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        )}
    )
    def retrieve(self, request, test_pk=None):
        test = get_object_or_404(Test, pk=test_pk)
        if request.user.user_type == 1:
            if test.creator != request.user:
                return Response({'detail': 'You are not authorized to view statistics for this test.'},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'detail': 'Only teachers can view test statistics.'},
                            status=status.HTTP_403_FORBIDDEN)
        results = Result.objects.filter(test=test)
        stats = {
            'average_score': results.aggregate(Avg('score'))['score__avg'] or 0,
            'highest_score': results.aggregate(Max('score'))['score__max'] or 0,
            'lowest_score': results.aggregate(Min('score'))['score__min'] or 0,
            'total_students': results.count(),
        }

        return Response(stats, status=status.HTTP_200_OK)
