from django.db.models import Avg, Max, Min
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from exam.models import Course, Result, Answer, Question, Test, Profile, TestCompletion, Choice
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

        # Step 1: Validate the Test data
        test_serializer = TestSerializer(data=data)
        if not test_serializer.is_valid():
            return Response(test_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Create the Test
        test = test_serializer.save(creator=request.user)

        # Step 3: Handle questions (if provided)
        questions_data = data.get('questions', [])
        for question_data in questions_data:
            question_text = question_data.get('question_text')
            question_type = question_data.get('question_type')

            # Create the question
            question = Question.objects.create(
                test=test,
                question_text=question_text,
                question_type=question_type
            )

            # Handle choices for MCQ questions
            if question_type == 'mcq':
                choices_data = question_data.get('choices', [])
                for choice_data in choices_data:
                    Choice.objects.create(
                        question=question,
                        choice_text=choice_data.get('choice_text'),
                        is_correct=choice_data.get('is_correct', False)
                    )

        # Return the created Test and associated questions
        response_data = TestSerializer(test).data
        return Response(response_data, status=status.HTTP_201_CREATED)

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

        # Check if the test has already finished based on deadline
        if timezone.now() > test.deadline:
            return Response({'detail': 'Test is already over.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve any existing TestCompletion for this test and student
        test_completion = TestCompletion.objects.filter(test=test, student=request.user).first()

        if test_completion:
            # Check if the test time has already expired
            if timezone.now() > test_completion.end_time:
                return Response({'detail': 'Test is already over.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'detail': 'Test already started.', 'end_time': test_completion.end_time},
                                status=status.HTTP_200_OK)

        # Automatically start the test by creating TestCompletion
        test_completion = TestCompletion.objects.create(
            test=test,
            student=request.user,
            start_time=timezone.now()
        )

        # Calculate end time based on time_limit
        test_completion.end_time = test_completion.start_time + test.time_limit
        test_completion.save()

        return Response({
            'detail': 'Test accessed and started',
            'end_time': test_completion.end_time
        }, status=status.HTTP_200_OK)


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
    def submit_answer(self, request, question_pk=None):
        """
        Submit an answer to a particular question in a test.
        """
        question = get_object_or_404(Question, pk=question_pk)

        # Check if student has access to the test
        test_completion = TestCompletion.objects.filter(
            test=question.test,
            student=request.user
        ).first()

        if not test_completion:
            return Response({'detail': 'Test not accessed or started.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the time limit has expired
        if timezone.now() > test_completion.end_time:
            return Response({'detail': 'Test time is over.'}, status=status.HTTP_400_BAD_REQUEST)

        # Submit the answer
        data = request.data
        data['question'] = question_pk
        data['student'] = request.user.id

        serializer = AnswerSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={200: AnswerSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        """
        List all answers submitted by the student for a particular test.
        """
        answers = Answer.objects.filter(student=request.user, question__test=test_pk)
        serializer = AnswerSerializer(answers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResultViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: ResultSerializer(many=True)}
    )
    def list(self, request, test_pk=None):
        test = get_object_or_404(Test, pk=test_pk)

        # Check if the user is a teacher or a student
        if request.user.user_type == 'teacher':
            # Teachers can view all results for their own tests
            if test.creator != request.user:
                return Response({'detail': 'You are not authorized to view results for this test.'},
                                status=status.HTTP_403_FORBIDDEN)
            results = Result.objects.filter(test=test_pk)

        elif request.user.user_type == 'student':
            # Students can only view their own results
            results = Result.objects.filter(test=test_pk, student=request.user)

        else:
            return Response({'detail': 'You are not authorized to view these results.'},
                            status=status.HTTP_403_FORBIDDEN)

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
        test = get_object_or_404(Test, pk=test_pk)

        # Ensure that only the teacher who created the test can access its statistics
        if request.user.user_type == 'teacher':
            if test.creator != request.user:
                return Response({'detail': 'You are not authorized to view statistics for this test.'},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'detail': 'Only teachers can view test statistics.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Fetch and return the statistics
        results = Result.objects.filter(test=test_pk)
        stats = {
            'average_score': results.aggregate(Avg('score'))['score__avg'],
            'highest_score': results.aggregate(Max('score'))['score__max'],
            'lowest_score': results.aggregate(Min('score'))['score__min'],
            'total_students': results.count(),
        }

        return Response(stats, status=status.HTTP_200_OK)
