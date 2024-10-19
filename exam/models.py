from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'Student'),
        (2, 'Teacher'),
        (3, 'Admin'),
    )
    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=1)
    enrolled_courses = models.ManyToManyField('Course', related_name='enrolled_courses', blank=True)

    def __str__(self):
        return f'{self.username} - {self.user_type}'


class Course(models.Model):
    name = models.CharField(max_length=128)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher', null=True)

    def __str__(self):
        return self.name


class Test(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tests')
    title = models.CharField(max_length=128)
    description = models.TextField()
    time_limit = models.DurationField()
    deadline = models.DateTimeField()

    def __str__(self):
        return f'{self.course}-{self.title} - {self.deadline}'


class Question(models.Model):
    QUESTION_TYPE_CHOICES = (
        ('mcq', 'Multiple Choice'),
        ('open', 'Open-ended'),
    )
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=4, choices=QUESTION_TYPE_CHOICES)
    question_text = models.TextField()

    def __str__(self):
        return self.question_text


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=128)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.choice_text


class AnswerSubmission(models.Model):
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='submitted_answers')
    student = models.ForeignKey('User', on_delete=models.CASCADE, related_name='submitted_answers')
    selected_choice = models.ForeignKey('Choice', null=True, blank=True, on_delete=models.CASCADE)  # for MCQs
    answer_text = models.TextField(null=True, blank=True)  # for open-ended questions
    grade_by_teacher = models.FloatField(default=0)
    submission_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer by {self.student.username} to {self.question.question_text}"


class CompletedTest(models.Model):
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name='completions')
    student = models.ForeignKey('User', on_delete=models.CASCADE, related_name='completed_tests')
    score = models.FloatField(default=0.0)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.username} completed {self.test.title}"
