from django.contrib.auth.models import AbstractUser
from django.db import models


class Profile(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'Teacher'),
        (2, 'Student'),
    )
    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=1)
    courses = models.ManyToManyField('Course', related_name='students', blank=True)

    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"


class Course(models.Model):
    name = models.CharField(max_length=255)
    teacher = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='taught_courses')

    def __str__(self):
        return self.name


class Test(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tests')
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='created_tests')
    name = models.CharField(max_length=255)
    time_limit = models.DurationField()
    deadline = models.DateTimeField()

    def __str__(self):
        return self.name


class Question(models.Model):
    QUESTION_TYPE_CHOICES = (
        ('mcq', 'Multiple Choice'),
        ('open', 'Open-ended'),
    )

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=4, choices=QUESTION_TYPE_CHOICES)

    def __str__(self):
        return self.question_text


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.choice_text


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)


class TestCompletion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)


class Result(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    graded_by_teacher = models.BooleanField(default=False)  # For manually marked tests

    def calculate_mcq_score(self):
        # Get all the questions for the test
        questions = self.test.questions.filter(question_type='mcq')
        total_questions = questions.count()
        correct_answers = 0

        for question in questions:

            student_answer = Answer.objects.filter(question=question, student=self.student).first()
            if not student_answer:
                continue

            correct_choices = question.choices.filter(is_correct=True)

            if correct_choices.filter(choice_text=student_answer.answer_text).exists():
                correct_answers += 1

        if total_questions > 0:
            self.score = (correct_answers / total_questions) * 100
        else:
            self.score = 0

        self.save()

    def __str__(self):
        return f"Result for {self.student.username} - {self.test.name}: {self.score}%"


class TestResult(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)

    def __str__(self):
        return f"TestResult for {self.student.username} - {self.test.name}: {self.score}%"
