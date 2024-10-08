from .models import User, Course, Submission, Test, Question
from django.contrib import admin

admin.site.register(User)
admin.site.register(Course)
admin.site.register(Submission)
admin.site.register(Test)
admin.site.register(Question)
