from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from exam.models import Test, Submission, Course, Question


class TestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create_test(self, request):
        # Assuming the user is a teacher
        course_id = request.data['course_id']
        title = request.data['title']
        time_limit = request.data['time_limit']
        deadline = request.data['deadline']

        course = Course.objects.get(id=course_id)
        test = Test.objects.create(
            course=course,
            title=title,
            creator=request.user,
            time_limit=time_limit,
            deadline=deadline
        )
        test.save()
        return Response(data={'message': 'Test created', 'test_id': test.id})

    def submit_test(self, request, test_id):
        test = Test.objects.get(id=test_id)
        student = request.user
        answers = request.data['answers']

        submission = Submission.objects.create(
            student=student,
            test=test,
            answers=answers
        )
        submission.save()
        return Response(data={'message': 'Test submitted successfully'})

    def grade_test(self, request, submission_id):
        submission = Submission.objects.get(id=submission_id)
        answers = submission.answers
        correct_answers = 0
        total_questions = 0

        # Automatic grading logic for MCQs
        for question_id, answer in answers.items():
            question = Question.objects.get(id=question_id)
            if question.is_mcq and question.options['correct_option'] == answer:
                correct_answers += 1
            total_questions += 1

        grade = (correct_answers / total_questions) * 100
        submission.grade = grade
        submission.is_graded = True
        submission.save()

        return Response({'message': 'Test graded', 'grade': grade})
