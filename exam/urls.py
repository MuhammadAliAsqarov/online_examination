from django.urls import path
from .views import TestViewSet

urlpatterns = [
    path('api/test/create/', TestViewSet.as_view({'post': 'create_test'}), name='create-test'),
    path('api/test/<int:test_id>/submit/', TestViewSet.as_view({'post': 'submit_test'}), name='submit-test'),
    path('api/test/<int:submission_id>/grade/', TestViewSet.as_view({'grade': 'grade_test'}), name='grade-test'),
]
