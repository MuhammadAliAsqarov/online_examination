from datetime import datetime
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Profile, Course, Test, Answer, Question, Choice, Result


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['username', 'password', 'user_type']

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])  # Hash the password before saving
        return super().create(validated_data)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, max_length=128)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'user_type']


class CourseSerializer(serializers.ModelSerializer):
    teacher = serializers.StringRelatedField()  # Use string representation for the teacher field

    class Meta:
        model = Course
        fields = ['name', 'teacher']


class TestSerializer(serializers.ModelSerializer):
    course = serializers.StringRelatedField()  # Display course name
    creator = serializers.StringRelatedField()  # Display creator's username

    class Meta:
        model = Test
        fields = ['course', 'creator', 'name', 'time_limit', 'deadline']

    def validate_deadline(self, value):
        """ Ensure the deadline is in the future """
        if value <= datetime.now():
            raise serializers.ValidationError("The deadline must be in the future.")
        return value


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'choice_text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)  # Nested serializer for related choices

    class Meta:
        model = Question
        fields = ['id', 'test', 'question_text', 'question_type', 'choices']

    def create(self, validated_data):
        # Handle choices in create if necessary
        return super().create(validated_data)


class AnswerSerializer(serializers.ModelSerializer):
    question = serializers.StringRelatedField()  # Display question text
    student = serializers.StringRelatedField()  # Display student's username

    class Meta:
        model = Answer
        fields = ['id', 'question', 'student', 'answer_text']


class ResultSerializer(serializers.ModelSerializer):
    test = serializers.StringRelatedField()  # Display test name
    student = serializers.StringRelatedField()  # Display student name

    class Meta:
        model = Result
        fields = ['test', 'student', 'score', 'graded_by_teacher']
