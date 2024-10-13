from django.urls import path

from .views import (
    TestViewSet,
    QuestionViewSet,
    AnswerViewSet,
    ResultViewSet,
    TestStatisticsViewSet,
    UserViewSet,
    CourseViewSet
)

urlpatterns = [
    # User URLs
    path('register/', UserViewSet.as_view({'post': 'register'}), name='user_register'),
    path('login/', UserViewSet.as_view({'post': 'login'}), name='user_login'),

    # Course URLs
    path('courses/', CourseViewSet.as_view({'get': 'list'}), name='course-list'),
    path('courses/<int:pk>/', CourseViewSet.as_view({'get': 'retrieve'}), name='course-detail'),

    # Test URLs
    path('tests/', TestViewSet.as_view({'get': 'list', 'post': 'create'}), name='test-list-create'),
    path('tests/<int:pk>/', TestViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
         name='test-detail'),
    path('tests/<int:pk>/access/', TestViewSet.as_view({'get': 'access_test'}), name='access-test'),

    # Question URLs
    path('tests/<int:test_pk>/questions/', QuestionViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='question-list-create'),
    path('questions/<int:pk>/', QuestionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
         name='question-detail'),

    # Answer URLs
    path('tests/<int:test_pk>/answers/', AnswerViewSet.as_view({'get': 'list', 'post': 'submit_answer'}),
         name='answer-list-create'),
    path('answers/<int:pk>/', AnswerViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
         name='answer-detail'),

    # Result URLs
    path('tests/<int:test_pk>/results/', ResultViewSet.as_view({'get': 'list'}), name='result-list'),
    path('results/<int:pk>/', ResultViewSet.as_view({'get': 'retrieve'}), name='result-detail'),

    # Test Statistics
    path('tests/<int:test_pk>/statistics/', TestStatisticsViewSet.as_view({'get': 'retrieve'}), name='test-statistics'),
]
