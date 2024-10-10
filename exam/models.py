from django.contrib.auth.models import AbstractUser
from django.db import models


# Model to distinguish between teachers and students
class Profile(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'Teacher'),
        (2, 'Student'),
    )
    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=1)
    username = models.CharField(max_length=128, unique=True)

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

    def __str__(self):
        return f"Answer by {self.student.username} to {self.question.question_text}"


class TestCompletion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField()

    def save(self, *args, **kwargs):
        # Automatically calculate end time based on time limit
        self.end_time = self.start_time + self.test.time_limit
        super().save(*args, **kwargs)


class Result(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    graded_by_teacher = models.BooleanField(default=False)  # For manually marked tests

    def __str__(self):
        return f"Result for {self.student.username} - {self.test.name}: {self.score}%"


class TestResult(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)

    def calculate_score(self):
        # Auto-grade MCQs
        mcq_questions = self.test.questions.filter(question_type='mcq')
        total_mcq_questions = mcq_questions.count()
        correct_answers = 0

        for question in mcq_questions:
            student_answer = Answer.objects.filter(question=question, student=self.student).first()
            if student_answer and question.choices.filter(is_correct=True,
                                                          choice_text=student_answer.answer_text).exists():
                correct_answers += 1

        # Calculate score for MCQs
        mcq_score = (correct_answers / total_mcq_questions) * 100 if total_mcq_questions > 0 else 0

        # Open-ended questions will be marked manually later
        # Store MCQ result
        self.score = mcq_score
        self.save()

        # Create or update the Result record for the student
        Result.objects.update_or_create(
            test=self.test,
            student=self.student,
            defaults={'score': self.score, 'graded_by_teacher': False}
        )
sdaf