from django.db.models import Avg, Max, Min
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework_simplejwt.tokens import RefreshToken

from exam.models import Course, Result, Answer, Question, Test, Profile, TestCompletion
from exam.serializers import CourseSerializer, TestSerializer, ResultSerializer, AnswerSerializer, QuestionSerializer, \
    UserRegistrationSerializer, UserLoginSerializer


class UserViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        request_body=UserRegistrationSerializer,
        responses={201: 'User registered successfully', 400: 'Invalid input'}
    )
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'username': user.username}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        request_body=UserLoginSerializer,
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
        courses = Course.objects.filter(teacher=request.user)
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
        request_body=TestSerializer,
        responses={201: TestSerializer(), 400: "Bad Request"}
    )
    def create(self, request):
        serializer = TestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creator=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={200: TestSerializer(many=True)}
    )
    def list(self, request):
        tests = Test.objects.filter(creator=request.user)
        serializer = TestSerializer(tests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Access a test for the student.",
        responses={200: 'Test accessed and started', 400: 'Test unavailable'}
    )
    def access_test(self, request, pk=None):
        test = get_object_or_404(Test, pk=pk)

        # Check if the test is already finished
        if timezone.now() > test.deadline:
            return Response({'detail': 'Test is already over.'}, status=status.HTTP_400_BAD_REQUEST)

        # Automatically start the test by creating TestCompletion
        test_completion, created = TestCompletion.objects.get_or_create(
            test=test, student=request.user, defaults={'start_time': timezone.now()}
        )

        if not created:
            return Response({'detail': 'Test already started'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Test accessed and started', 'end_time': test_completion.end_time},
                        status=status.HTTP_200_OK)


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
        responses={200: QuestionSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        questions = Question.objects.filter(test=test_pk)
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnswerViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=AnswerSerializer,
        responses={201: AnswerSerializer(), 400: "Bad Request"}
    )
    def create(self, request):
        serializer = AnswerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={200: AnswerSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        answers = Answer.objects.filter(student=request.user, question__test=test_pk)
        serializer = AnswerSerializer(answers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResultViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: ResultSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        if request.user.user_type == 'teacher':
            results = Result.objects.filter(test=test_pk)
        else:
            results = Result.objects.filter(test=test_pk, student=request.user)

        serializer = ResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        results = Result.objects.filter(test=test_pk)

        stats = {
            'average_score': results.aggregate(Avg('score'))['score__avg'],
            'highest_score': results.aggregate(Max('score'))['score__max'],
            'lowest_score': results.aggregate(Min('score'))['score__min'],
            'total_students': results.count(),
        }

        return Response(stats, status=status.HTTP_200_OK)
