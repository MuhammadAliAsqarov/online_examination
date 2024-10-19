from django.db.models import Avg, Max, Min, Sum
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CompletedTest, AnswerSubmission, Question, Test, User
from .permissions import is_admin, is_teacher, is_student
from .serializers import CourseCreateSerializer, UserRegisterSerializer, UserLoginSerializer, TestSerializer, \
    CourseSerializer, QuestionSerializer
from .swagger_utils import test_schema, finish_test_schema
from .utils import check_for_course, check_course_retrieve, check_for_test, check_deadline, start_test, \
    create_question, calculate_test_result, process_answer, check_permission, check_test


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
        request_body=test_schema,
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
    @is_student
    def access_test(self, request, test_id=None):
        user = request.user
        test = get_object_or_404(Test, pk=test_id)
        check_permission(user, test)
        check_deadline(test)
        test_completion = CompletedTest.objects.filter(test=test, student=user).first()
        check_test(test_completion)
        start_time = timezone.now()
        end_time = start_time + test.time_limit
        test_completion = start_test(user, test, start_time, end_time)
        return Response({
            'detail': 'Test accessed and started',
            'end_time': test_completion.end_time
        }, status=status.HTTP_200_OK)


class QuestionsTestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all questions for a particular test with pagination",
        responses={200: QuestionSerializer(many=True)}
    )
    def list(self, request, test_id):
        test = get_object_or_404(Test, id=test_id)
        questions = Question.objects.filter(test=test)
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TestCompletionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Finish a test and calculate the result",
        request_body=finish_test_schema,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Test finished and results calculated",
                examples={
                    'application/json': {
                        "message": "Test completed",
                        "result": {
                            "overall_score": 85,
                            "correct_answers": 8,
                            "wrong_answers": 2
                        }
                    }
                }
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Test not found"
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Invalid data provided"
            )
        }
    )
    def finish_test(self, request, test_id):
        test_completion = get_object_or_404(
            CompletedTest, test_id=test_id, student=request.user, completed=False
        )
        test_completion.end_time = timezone.now()
        answers = request.data.get('answers', [])
        for answer_data in answers:
            question = get_object_or_404(Question, id=answer_data['question_id'])
            process_answer(question, answer_data, test_completion)
        test_completion.completed = True
        test_completion.save()
        result = calculate_test_result(test_completion)
        test_completion.score = result['overall_score']
        test_completion.save()
        return Response({
            "message": "Test completed",
            "result": result
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Score the answers of a student for a specific test",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'question_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of the question being scored'
                ),
                'score': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Score given by the teacher for the question'
                ),
            },
            required=['question_id', 'score'],
        ),
        responses={200: "Score recorded", 400: "Bad Request"}
    )
    @is_teacher
    def score_answer(self, request, test_id, student_id):
        data = request.data
        question_id = data.get('question_id')
        score = data.get('score')
        answer_submission = get_object_or_404(
            AnswerSubmission,
            question__test__id=test_id,
            question_id=question_id,
            student__id=student_id,
            student__user_type=2
        )

        answer_submission.score = score
        answer_submission.save()
        return Response({"message": "Score recorded"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Get the overall score for a student's test",
        responses={200: "Score retrieved", 404: "Test not found"}
    )
    @is_student
    def get_overall_score(self, request, test_id):
        completed_test = get_object_or_404(CompletedTest, test_id=test_id, student=request.user)
        result = calculate_test_result(completed_test)

        return Response({
            "message": "Score retrieved",
            "overall_score": result['overall_score'],
            "mcq_score": result['mcq_score'],
            "teacher_scores": result['teacher_scores'],
            "total_questions": result['total_questions'],
            "correct_answers": result['correct_answers'],
        }, status=status.HTTP_200_OK)


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
    @is_teacher
    def retrieve(self, request, test_id=None):
        test = get_object_or_404(Test, pk=test_id)
        if test.creator != request.user:
            return Response({'detail': 'You are not authorized to view statistics for this test.'},
                            status=status.HTTP_403_FORBIDDEN)
        results = CompletedTest.objects.filter(test=test)
        stats = {
            'average_score': results.aggregate(Avg('score'))['score__avg'] or 0,
            'highest_score': results.aggregate(Max('score'))['score__max'] or 0,
            'lowest_score': results.aggregate(Min('score'))['score__min'] or 0,
            'total_students': results.count(),
        }

        return Response(stats, status=status.HTTP_200_OK)
