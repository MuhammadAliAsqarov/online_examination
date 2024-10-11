from django.contrib import admin
from exam.models import Profile, Course, Test, Question, Choice, Answer, Result, TestCompletion


# Admin for Profile model
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'user_type')
    search_fields = ('username',)
    list_filter = ('user_type',)


# Admin for Course model
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'teacher')
    search_fields = ('name', 'teacher__username')
    list_filter = ('teacher',)


# Admin for Test model
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'course', 'creator', 'deadline', 'time_limit')
    search_fields = ('name', 'course__name', 'creator__username')
    list_filter = ('course', 'creator')


# Admin for Question model
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text', 'test', 'question_type')
    search_fields = ('question_text', 'test__name')
    list_filter = ('test', 'question_type')


# Admin for Choice model
@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'choice_text', 'question', 'is_correct')
    search_fields = ('choice_text', 'question__question_text')
    list_filter = ('question', 'is_correct')


# Admin for Answer model
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'student', 'answer_text')
    search_fields = ('student__username', 'question__question_text')


# Admin for Result model
@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'student', 'score', 'graded_by_teacher')
    search_fields = ('test__name', 'student__username')
    list_filter = ('test', 'graded_by_teacher')


# Admin for TestCompletion model
@admin.register(TestCompletion)
class TestCompletionAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'student', 'start_time', 'end_time')
    search_fields = ('test__name', 'student__username')
