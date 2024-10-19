from django.urls import path

from .views import UserViewSet, CourseViewSet, TestViewSet, QuestionsTestViewSet, TestCompletionViewSet, \
    TestStatisticsViewSet

urlpatterns = [
    # User URLs
    path('register/', UserViewSet.as_view({'post': 'register'})),
    path('login/', UserViewSet.as_view({'post': 'login'})),

    # Course URLs
    path('courses/', CourseViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('courses/<int:course_id>/', CourseViewSet.as_view({'get': 'retrieve'})),

    # Test Urls
    path('tests/', TestViewSet.as_view({'post': 'create', 'get': 'list'})),
    path('tests/<int:test_id>/access/', TestViewSet.as_view({'get': 'access_test'})),
    path('tests/<int:test_id>/questions/',
         QuestionsTestViewSet.as_view({'get': 'list'})),
    path('tests/<int:test_id>/finish/', TestCompletionViewSet.as_view({'post': 'finish_test'})),
    path('tests/<int:test_id>/student/<int:student_id>/score/',
         TestCompletionViewSet.as_view({'post': 'score_answer'})),
    path('tests/<int:test_id>/score/overall/', TestCompletionViewSet.as_view({'get': 'get_overall_score'})),
    path('tests/<int:test_id>/statistics/', TestStatisticsViewSet.as_view({'get': 'retrieve'}), name='test-statistics'),
]
