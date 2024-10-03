from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)


class Test(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tests')
    title = models.CharField(max_length=255)
    total_time = models.DurationField()

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    is_multiple_choice = models.BooleanField(default=False)

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

class ExamSession(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

class Result(models.Model):
    exam_session = models.OneToOneField(ExamSession, on_delete=models.CASCADE)
    score = models.FloatField()
    evaluated = models.BooleanField(default=False)
