from drf_yasg import openapi

choice_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['choice_text'],
    properties={
        'choice_text': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Text of the choice (only for MCQ questions)'
        ),
        'is_correct': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description='Indicates if the choice is the correct answer (only for MCQ questions)'
        )
    },
    description='Choices for MCQ questions'
)
question_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['question_text', 'question_type'],
    properties={
        'question_text': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Text of the question'
        ),
        'question_type': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Type of the question: multiple-choice (mcq) or open-ended (open)',
            enum=['mcq', 'open']
        ),
        'choices': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=choice_schema,
            description='List of choices for MCQ questions (ignored for open-ended questions)',
            example=[
                {"choice_text": "Choice 1", "is_correct": True},
                {"choice_text": "Choice 2", "is_correct": False}
            ]
        )
    },
    description='Schema for a question, including choices for MCQ questions'
)
test_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['title', 'course', 'time_limit', 'deadline', 'questions'],
    properties={
        'title': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='The title or name of the test'
        ),
        'course': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='ID of the course the test belongs to'
        ),
        'time_limit': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Time limit for the test in HH:MM:SS format',
            example='01:30:00'
        ),
        'deadline': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATETIME,
            description='Deadline for completing the test in ISO 8601 format',
            example='2024-12-31T23:59:59'
        ),
        'questions': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=question_schema,
            description='List of questions to include in the test. For open-ended questions, omit the choices.'
        )
    }
)

answer_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'question_id': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="ID of the question"
        ),
        'answer_text': openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Answer text for open-ended questions",
            nullable=True
        ),
        'choice_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_INTEGER),
            description="IDs of selected choices (for MCQ questions only)",
            nullable=True
        )
    },
    required=['question_id'],
    example={
        "question_id": 1,
        "choice_ids": [1]
    }
)
answers_schema = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=answer_schema,
    description='List of answers for the test',
    example=[
        {
            "question_id": 1,
            "choice_ids": [1]
        },
        {
            "question_id": 2,
            "answer_text": "This is my answer to the open-ended question"
        }
    ]
)

finish_test_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'answers': answers_schema
    },
    required=['answers']
)

# Define the response schema for test results
test_result_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'overall_score': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total score of the test'),
        'correct_answers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of correct answers'),
        'wrong_answers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of wrong answers')
    },
    description='Result of the test'
)
