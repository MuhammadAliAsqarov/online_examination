from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# Model to distinguish between teachers and students
class Profile(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'Teacher'),
        (2, 'Student'),
    )
    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=1)

    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"


# Course model, linked to a teacher and students
class Course(models.Model):
    name = models.CharField(max_length=255)
    teacher = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='courses')

    def __str__(self):
        return self.name


# Test model, linked to a course and a teacher, with additional fields for timing
class Test(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tests')
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='created_tests')
    name = models.CharField(max_length=255)
    time_limit = models.DurationField()
    deadline = models.DateTimeField()

    def __str__(self):
        return self.name

    def clean(self):
        # Ensure that the deadline is set in the future
        if self.deadline and self.deadline < timezone.now():
            raise ValueError('The deadline must be set in the future.')


# Question model linked to a test, with two question types: MCQ and Open-ended
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


# Model to store choices for MCQ questions
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.choice_text


# Model to store answers provided by students
class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)  # For open-ended or single choice text

    def clean(self):
        # Ensure that answer_text is only provided for the right question type
        if self.question.question_type == 'mcq' and not self.answer_text:
            raise ValueError('MCQ answers must have answer text.')
        if self.question.question_type == 'open' and self.answer_text is None:
            raise ValueError('Open-ended questions require answer text.')

    def __str__(self):
        return f"Answer by {self.student.username} to {self.question.question_text}"


# Model to handle test completion by students
class TestCompletion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.end_time:  # Calculate end time only if not provided
            self.end_time = self.start_time + self.test.time_limit
        super().save(*args, **kwargs)

    def clean(self):
        # Ensure that the calculated end_time does not exceed the test deadline
        if self.end_time > self.test.deadline:
            raise ValueError('End time exceeds the test deadline.')


# Model to store student results
class Result(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    graded_by_teacher = models.BooleanField(default=False)  # For manually marked tests

    def __str__(self):
        return f"Result for {self.student.username} - {self.test.name}: {self.score}%"


# Model to handle automatic and manual grading
class TestResult(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)

    def calculate_score(self):
        mcq_questions = self.test.questions.filter(question_type='mcq')
        total_mcq_questions = mcq_questions.count()
        correct_answers = 0

        for question in mcq_questions:
            student_answer = Answer.objects.filter(question=question, student=self.student).first()
            if student_answer and question.choices.filter(is_correct=True,
                                                          choice_text=student_answer.answer_text).exists():
                correct_answers += 1

        mcq_score = (correct_answers / total_mcq_questions) * 100 if total_mcq_questions > 0 else 0
        self.score = mcq_score
        self.save()

        # Update or create Result record for this test and student
        Result.objects.update_or_create(
            test=self.test,
            student=self.student,
            defaults={'score': self.score, 'graded_by_teacher': False}
        )

    def __str__(self):
        return f"TestResult for {self.student.username} - {self.test.name}: {self.score}%"


