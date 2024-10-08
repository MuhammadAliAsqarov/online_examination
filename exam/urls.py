from django.urls import path
from .views import TestViewSet

urlpatterns = [
    path('test/', TestViewSet.as_view({'post': 'create_test'}), name='test'),
    path('test/submit/', TestViewSet.as_view({'post': 'submit_test'}), name='test'),
    path('test/grade/', TestViewSet.as_view({'post': 'grade_test'}), name='test'),
]
