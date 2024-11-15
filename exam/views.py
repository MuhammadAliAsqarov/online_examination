from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from exceptions.error_codes import ErrorCodes
from exceptions.exception import CustomApiException
# from .tasks import stop_test_completion
from .custom_pagination import CustomPagination, CustomPaginationCourse
from .models import CompletedTest, AnswerSubmission, Question, Test, User
from .permissions import is_admin, is_teacher, is_student
from .serializers import CourseCreateSerializer, UserRegisterSerializer, UserLoginSerializer, TestSerializer, \
    CourseSerializer, QuestionSerializer, TestCreateSerializer, FinishTestSerializer, QuestionListSerializer, \
    AnswerSubmissionSerializer, EnrollmentSerializer
from .utils import check_for_course, check_course_retrieve, check_for_test, check_deadline, start_test, \
    calculate_test_result, check_permission, check_test, answers_func, all_score_func
from .utils_cache import get_cache_key_stats, get_overall_score_cache_key
from django.core.cache import cache


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
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST.value)
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class CourseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new course with a specified teacher",
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
        if not request.user.user_type == 3:
            serializer = CourseSerializer(courses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        paginator = CustomPaginationCourse()
        paginated_questions = paginator.paginate_queryset(courses, request)
        serializer = CourseSerializer(paginated_questions, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        operation_description="Enroll multiple students to a course",
        request_body=EnrollmentSerializer,
        responses={200: 'Students successfully enrolled', 400: 'Invalid data', 404: 'Course not found'}
    )
    @is_admin
    def enroll_students(self, request, course_id):
        data = {
            'course': course_id,
            'student_ids': request.data.get('student_ids', [])
        }
        serializer = EnrollmentSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        result = serializer.save()
        return Response(
            {'detail': 'Students successfully enrolled', 'enrollments': EnrollmentSerializer(result).data},
            status=status.HTTP_201_CREATED)


class TestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=TestCreateSerializer,
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
        test_serializer = TestCreateSerializer(data=data, context={'request': request})
        if not test_serializer.is_valid():
            return Response(test_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        test = test_serializer.save()
        response_data = TestSerializer(test).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="List all tests",
        responses={200: TestSerializer(many=True)}
    )
    @check_for_test
    def list(self, request, tests):
        serializer = TestSerializer(tests, many=True, context={'student': request.user})
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
        # stop_test_completion.send_with_options(
        #     args=(test_completion.id,),
        #     delay=test.time_limit.total_seconds() * 1000
        # )
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
        user = request.user
        get_object_or_404(
            CompletedTest,
            student=user,
            test_id=test_id,
            completed=False
        )
        questions = Question.objects.filter(test_id=test_id)
        paginator = CustomPagination()
        paginated_questions = paginator.paginate_queryset(questions, request)
        serializer = QuestionListSerializer(paginated_questions, many=True)
        return paginator.get_paginated_response(serializer.data)


class TestCompletionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Finish a test and calculate the result",
        request_body=FinishTestSerializer,
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
        serializer = FinishTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        answers = serializer.validated_data['answers']
        result = answers_func(answers, test_completion)
        return Response({
            "message": "Test completed",
            "result": result
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Get paginated answers for a specific test and score them",
        responses={200: AnswerSubmissionSerializer(many=True)},
    )
    @is_teacher
    def list(self, request, test_id, student_id):
        answer_submissions = AnswerSubmission.objects.filter(
            question__test__id=test_id,
            student__id=student_id
        )
        paginator = CustomPagination()
        paginated_answer_submissions = paginator.paginate_queryset(answer_submissions, request)
        serializer = AnswerSubmissionSerializer(paginated_answer_submissions, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
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
            student__id=student_id
        )
        if answer_submission.question.question_type != 'open':
            raise CustomApiException(error_code=ErrorCodes.FORBIDDEN.value,
                                     message={'detail': 'Only open questions can be scored'})
        answer_submission.grade_by_teacher = score
        answer_submission.save()
        cache.delete(get_cache_key_stats('test', test_id))
        cache.delete(get_overall_score_cache_key(test_id, student_id))
        return Response({"message": "Score recorded"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Get the overall score for a student's test",
        responses={200: "Score retrieved", 404: "Test not found"}
    )
    @is_student
    @swagger_auto_schema(
        operation_description="Get the overall score for a student's test",
        responses={200: "Score retrieved", 404: "Test not found"}
    )
    @is_student
    def get_overall_score(self, request, test_id):
        result = get_object_or_404(CompletedTest, test_id=test_id, student=request.user)
        result_data = calculate_test_result(result)
        return Response({
            "message": "Score retrieved",
            **result_data
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
        )},
    )
    @is_teacher
    def retrieve(self, request, test_id):
        test = get_object_or_404(Test, pk=test_id)
        if test.creator != request.user:
            raise CustomApiException(
                error_code=ErrorCodes.FORBIDDEN.value,
                message={'detail': 'You are not authorized to view this test'}
            )
        cache_key = get_cache_key_stats('test', test_id)
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        results = CompletedTest.objects.filter(test=test)
        all_scores = all_score_func(results)
        stats = {
            'average_score': sum(all_scores) / len(all_scores) if all_scores else 0,
            'highest_score': max(all_scores) if all_scores else 0,
            'lowest_score': min(all_scores) if all_scores else 0,
            'total_students': len(all_scores),
        }
        cache.set(cache_key, stats, timeout=60 * 15)
        return Response(stats, status=status.HTTP_200_OK)
