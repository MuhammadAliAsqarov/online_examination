from datetime import timezone, datetime

from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Profile, Course, Test, Answer, Question, Choice, Result


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['username', 'password', 'user_type']

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])  # Hash the password
        return super().create(validated_data)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'user_type']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['name', 'teacher']


class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ['course', 'creator', 'name', 'time_limit', 'deadline']

    def validate(self, attrs):
        # Add any custom validation if needed
        if attrs['deadline'] <= datetime.now():
            raise serializers.ValidationError("The deadline must be in the future.")
        return attrs


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'choice_text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'test', 'question_text', 'question_type', 'choices']


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'question', 'student', 'answer_text']


class ResultSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField()

    class Meta:
        model = Result
        fields = ['test', 'student', 'score', 'graded_by_teacher']
