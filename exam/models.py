from django.db import models
from rest_framework.authtoken.admin import User

Question_choices = (
    (1, 'MCQ'),
    (2, 'Open')
)


class Course(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Test(models.Model):
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=128)
    questions = models.TextField(max_length=128)
    deadline = models.DateField()
    time_limit = models.IntegerField(default=30)

    def __str__(self):
        return self.title
