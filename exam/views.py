from django.db.models import Avg, Max, Min
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from exam.models import Course, Result, Answer, Question, Test, Profile
from exam.serializers import CourseSerializer, TestSerializer, ResultSerializer, AnswerSerializer, QuestionSerializer, \
    UserRegistrationSerializer, UserLoginSerializer


class UserViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        request_body=UserRegistrationSerializer,
        responses={201: openapi.Response('User registered successfully'), 400: 'Invalid input'}
    )
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()  # Save the new user
        return Response({'username': user.username}, status=status.HTTP_201_CREATED)

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
        serializer.is_valid(raise_exception=True)  # Will raise ValidationError if invalid

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Manually retrieve user based on username
        user = Profile.objects.filter(username=username).first()

        # Check if the user exists and if the password matches
        if not user and not user.check_password(password):
            return Response(data={'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


# ViewSet for Course
class CourseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all courses for the authenticated teacher.",
        responses={200: CourseSerializer(many=True)}
    )
    def list(self, request):
        courses = Course.objects.filter(teacher=request.user)
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Retrieve a specific course by ID.",
        responses={200: CourseSerializer()}
    )
    def retrieve(self, request, pk=None):
        course = Course.objects.get(pk=pk)
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ViewSet for Test
class TestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new test for the authenticated teacher.",
        request_body=TestSerializer,
        responses={201: TestSerializer(), 400: "Bad Request"}
    )
    def create(self, request):
        serializer = TestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(creator=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="List all tests created by the authenticated teacher.",
        responses={200: TestSerializer(many=True)}
    )
    def list(self, request):
        tests = Test.objects.filter(creator=request.user)
        serializer = TestSerializer(tests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ViewSet for Question
class QuestionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new question for a test.",
        request_body=QuestionSerializer,
        responses={201: QuestionSerializer(), 400: "Bad Request"}
    )
    def create(self, request):
        serializer = QuestionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="List questions of a particular test.",
        responses={200: QuestionSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        questions = Question.objects.filter(test=test_pk)
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ViewSet for Answer
class AnswerViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Submit answers to questions.",
        request_body=AnswerSerializer,
        responses={201: AnswerSerializer(), 400: "Bad Request"}
    )
    def create(self, request):
        serializer = AnswerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(student=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    operation_description="List all answers submitted for a test by the student.",
    responses={200: AnswerSerializer(many=True)}
)
def list(self, request, test_pk=None):
    answers = Answer.objects.filter(student=request.user, question__test=test_pk)
    serializer = AnswerSerializer(answers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ViewSet for Result
class ResultViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List results for a particular test.",
        responses={200: ResultSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        if request.user.profile.user_type == 'teacher':
            results = Result.objects.filter(test=test_pk)
        else:
            results = Result.objects.filter(test=test_pk, student=request.user)

        serializer = ResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Retrieve a specific result by ID.",
        responses={200: ResultSerializer()}
    )
    def retrieve(self, request, pk=None):
        result = Result.objects.get(pk=pk)
        serializer = ResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ViewSet for Test Statistics
class TestStatisticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve aggregated statistics for the test.",
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
