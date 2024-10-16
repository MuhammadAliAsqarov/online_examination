from django.urls import path

from .views import UserViewSet, CourseViewSet, TestViewSet, QuestionsTestViewSet, TestCompletionViewSet

urlpatterns = [
    # User URLs
    path('register/', UserViewSet.as_view({'post': 'register'})),
    path('login/', UserViewSet.as_view({'post': 'login'})),

    # Course URLs
    path('courses/', CourseViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('courses/<int:course_id>/', CourseViewSet.as_view({'get': 'retrieve'})),

    # Test Urls
    path('tests/', TestViewSet.as_view({'post': 'create', 'get': 'list'})),
    path('tests/<int:pk>/access/', TestViewSet.as_view({'get': 'access_test'})),
    path('tests/<int:test_id>/questions/<int:question_id>/answer/',
         QuestionsTestViewSet.as_view({'post': 'answer_question'})),
    path('tests/<int:test_id>/finish/', TestCompletionViewSet.as_view({'post': 'finish_test'})),
]
