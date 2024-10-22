from datetime import datetime
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import User, Course, Test, AnswerSubmission, Question, Choice, CompletedTest


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password', 'user_type')

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)


class CourseCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    teacher = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(user_type=2))

    def create(self, validated_data):
        course = Course.objects.create(**validated_data)
        return course


class CourseSerializer(serializers.ModelSerializer):
    teacher = serializers.StringRelatedField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'teacher']


class EnrollmentSerializer(serializers.Serializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    student_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(user_type=1))
    )

    def validate(self, data):
        course = data['course']
        student_ids = data['student_ids']
        already_enrolled_students = course.students.filter(id__in=[student.id for student in student_ids])
        if already_enrolled_students.exists():
            already_enrolled = ', '.join([str(student) for student in already_enrolled_students])
            raise serializers.ValidationError(f"The following students are already enrolled: {already_enrolled}")
        return data

    def create(self, validated_data):
        course = validated_data['course']
        student_ids = validated_data['student_ids']
        course.enrolled_courses.add(*student_ids)
        return {
            'course': course,
            'students': student_ids,
        }


class ChoiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['choice_text']


class QuestionListSerializer(serializers.ModelSerializer):
    choices = ChoiceListSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['question_text', 'question_type', 'choices']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.question_type == 'open':
            representation.pop('choices', None)
        elif instance.question_type == 'mcq':

            pass

        return representation


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['choice_text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['question_text', 'question_type', 'choices']

    def validate(self, data):
        question_type = data.get('question_type')
        choices = data.get('choices', [])

        if question_type == 'mcq' and not choices:
            raise serializers.ValidationError("Multiple-choice questions must have choices.")

        if question_type == 'open' and choices:
            raise serializers.ValidationError("Open-ended questions should not have choices.")

        return data


class TestSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Test
        fields = ['course', 'creator', 'title', 'time_limit', 'deadline']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        student = self.context.get('student')

        if student:
            completion = CompletedTest.objects.filter(test=instance, student=student).first()
            if completion:
                representation['completed'] = completion.completed
            else:
                representation['completed'] = False
        else:
            representation['completed'] = None

        return representation


class TestCreateSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Test
        fields = ['course', 'creator', 'title', 'time_limit', 'deadline', 'questions']

    def validate_deadline(self, value):
        if value <= datetime.now():
            raise serializers.ValidationError("The deadline must be in the future.")
        return value

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        creator = self.context['request'].user
        validated_data['creator'] = creator
        test = Test.objects.create(**validated_data)
        for question_data in questions_data:
            choices_data = question_data.pop('choices', [])
            question = Question.objects.create(test=test, **question_data)
            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)
        return test


class AnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer_text = serializers.CharField(required=False, allow_blank=True)
    choice_id = serializers.IntegerField(required=False)

    def validate(self, data):
        question_id = data.get('question_id')
        answer_text = data.get('answer_text')
        choice_id = data.get('choice_id')

        question = Question.objects.filter(id=question_id).first()
        if not question:
            raise serializers.ValidationError(f"Question with id {question_id} does not exist.")

        if question.question_type == 'mcq':
            if choice_id is None:
                raise serializers.ValidationError(f"Choice ID must be provided for multiple-choice questions.")
            if answer_text:
                raise serializers.ValidationError(f"Answer text should not be provided for multiple-choice questions.")

        elif question.question_type == 'open':
            if not answer_text:
                raise serializers.ValidationError(f"Answer text must be provided for open-ended questions.")
            if choice_id is not None:
                raise serializers.ValidationError(f"Choice ID should not be provided for open-ended questions.")

        return data


class FinishTestSerializer(serializers.Serializer):
    answers = AnswerSerializer(many=True)

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("Answers list cannot be empty.")
        return value


class AnswerSubmissionSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_id = serializers.IntegerField(source='question.id', read_only=True)
    score = serializers.FloatField(required=False)

    class Meta:
        model = AnswerSubmission
        fields = ['question_id', 'question_text', 'score']

    def validate(self, data):
        question = self.instance.question
        if question.question_type != 'open':
            raise serializers.ValidationError("Only open questions can be scored.")
        return data
