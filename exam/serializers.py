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
    teacher_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(user_type=2))

    def create(self, validated_data):
        course = Course.objects.create(**validated_data)
        return course


class CourseSerializer(serializers.ModelSerializer):
    teacher = serializers.StringRelatedField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'teacher']


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['choice_text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['question_text', 'question_type', 'choices']


class TestSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Test
        fields = ['course', 'creator', 'title', 'time_limit', 'deadline']

    def validate_deadline(self, value):
        if value <= datetime.now():
            raise serializers.ValidationError("The deadline must be in the future.")
        return value

    def create(self, validated_data):
        creator = self.context['request'].user
        validated_data['creator'] = creator
        test = Test.objects.create(**validated_data)
        return test
