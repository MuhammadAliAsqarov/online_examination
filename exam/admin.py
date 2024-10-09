from django.contrib import admin
from .models import Profile, Course, Test, Question, Choice, Answer, Result, TestCompletion


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type')  # Added user_type
    search_fields = ('username', 'email', 'first_name', 'last_name')  # Enable searching in UserAdmin


admin.site.register(Profile, UserAdmin)  # Register the custom User admin


class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher']
    search_fields = ['name', 'teacher__username']
    list_filter = ['teacher']


class TestAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator', 'course', 'time_limit', 'deadline']
    search_fields = ['name', 'creator__username', 'course__name']
    list_filter = ['creator', 'course', 'deadline']


class QuestionAdmin(admin.ModelAdmin):
    list_display = ['test', 'question_text', 'question_type']
    search_fields = ['question_text']
    list_filter = ['test', 'question_type']


class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['question', 'choice_text', 'is_correct']
    search_fields = ['choice_text']
    list_filter = ['question']


class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'student', 'answer_text']
    search_fields = ['student__username', 'question__question_text']
    list_filter = ['question', 'student']


class ResultAdmin(admin.ModelAdmin):
    list_display = ['test', 'student', 'score', 'graded_by_teacher']
    search_fields = ['student__username', 'test__name']
    list_filter = ['test', 'graded_by_teacher']


class TestCompletionAdmin(admin.ModelAdmin):
    list_display = ['test', 'student', 'start_time', 'end_time']
    search_fields = ['student__username', 'test__name']
    list_filter = ['test', 'student']


# Register the models with the admin site
admin.site.register(Course, CourseAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(Result, ResultAdmin)
admin.site.register(TestCompletion, TestCompletionAdmin)
