from django.contrib import admin
from exam.models import User, Course, Test, Question, Choice, AnswerSubmission, CompletedTest, TestProgress


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'user_type')
    search_fields = ('username',)
    list_filter = ('user_type',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'teacher')
    search_fields = ('name', 'teacher__username')
    list_filter = ('teacher',)


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'creator', 'deadline', 'time_limit')
    search_fields = ('title', 'course__name', 'creator__username')
    list_filter = ('course', 'creator')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text', 'test', 'question_type')
    search_fields = ('question_text', 'test__name')
    list_filter = ('test', 'question_type')


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'choice_text', 'question', 'is_correct')
    search_fields = ('choice_text', 'question__question_text')
    list_filter = ('question', 'is_correct')


@admin.register(AnswerSubmission)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'student', 'answer_text')
    search_fields = ('student__username', 'question__question_text')


@admin.register(CompletedTest)
class CompletedTestAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'student', 'start_time', 'end_time')
    search_fields = ('test__name', 'student__username')


@admin.register(TestProgress)
class TestProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'test', 'completed')
    list_filter = ('student', 'test')
    search_fields = ('student__username', 'test__title')
o