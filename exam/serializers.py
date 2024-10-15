from datetime import datetime
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Profile, Course, Test, Answer, Question, Choice, Result


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['username', 'password', 'user_type']

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, max_length=128)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'user_type']


class CourseSerializer(serializers.ModelSerializer):
    teacher = serializers.StringRelatedField()

    class Meta:
        model = Course
        fields = ['name', 'teacher']


class TestSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Test
        fields = ['course', 'creator', 'name', 'time_limit', 'deadline']

    def validate_deadline(self, value):
        if value <= datetime.now():
            raise serializers.ValidationError("The deadline must be in the future.")
        return value

    def create(self, validated_data):
        creator = self.context['request'].user
        validated_data['creator'] = creator
        test = Test.objects.create(**validated_data)
        return test


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'choice_text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'test', 'question_text', 'question_type', 'choices']

    def create(self, validated_data):
        # Handle choices in create if necessary
        return super().create(validated_data)


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'student', 'question', 'answer_text']

    def validate(self, data):
        question = data.get('question')
        if question.question_type == 'mcq' and not data.get('answer_text'):
            raise serializers.ValidationError('MCQ answers must have answer text.')
        if question.question_type == 'open' and data.get('answer_text') is None:
            raise serializers.ValidationError('Open-ended questions require answer text.')

        return data

    def create(self, validated_data):
        # Save the answer to the database
        return Answer.objects.create(**validated_data)


class ResultSerializer(serializers.ModelSerializer):
    test = serializers.StringRelatedField()
    student = serializers.StringRelatedField()

    class Meta:
        model = Result
        fields = ['test', 'student', 'score', 'graded_by_teacher']
