from datetime import datetime

from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Optional, Dict, Union, OrderedDict, Any
from .validators import (
    BaseValidationModel,
    validate_future_date,
    validate_sop_score
)
from .enums import QuestionTypeEnum, RoleEnum, Enum


class GroupSchema(BaseModel):
    group_id: str = Field(..., min_length=1)
    seminarist_id: str = Field(..., min_length=1)


class CourseCreateRequest(BaseValidationModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    lector_id: str = Field(..., min_length=1)
    groups: List[GroupSchema]


class CourseUpdateRequest(BaseValidationModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    lector_id: Optional[str] = Field(None, min_length=1)
    groups: Optional[List[GroupSchema]] = None


class BlockCreateRequest(BaseValidationModel):
    name: str = Field(..., min_length=3, max_length=100)


class UnitContentSchema(BaseValidationModel):
    test_id: Optional[str] = None
    text_content: Optional[str] = None

    @classmethod
    def parse_raw_content(cls, content: Union[str, Dict]) -> 'UnitContentSchema':
        if isinstance(content, str):
            return cls(text_content=content)
        return cls(**content)


class QuestionSchema(BaseValidationModel):
    id: int
    text: str = Field(..., min_length=5, max_length=500)
    type: QuestionTypeEnum
    answers: Optional[List[str]] = None


class AnswerSchema(BaseValidationModel):
    id: int
    answer: List[str]

    class Config:
        populate_by_name = True


class TestCreateRequest(BaseValidationModel):
    questions: List[QuestionSchema]
    answers: List[AnswerSchema]
    deadline: Optional[datetime]

    _deadline_validator = validator('deadline', allow_reuse=True)(validate_future_date)


class TestSubmitRequest(BaseValidationModel):
    answers: List[Dict]

    @validator('answers')
    def validate_answers(cls, v):
        validated_answers = []
        for answer in v:
            try:
                if 'id' in answer:
                    answer_data = {'id': answer['id'], 'answer': answer['answer']}
                else:
                    answer_data = answer

                validated = AnswerSchema(**answer_data)
                validated_answers.append(validated.dict())
            except ValidationError as e:
                raise ValueError(f"Invalid answer format: {str(e)}")
        return validated_answers


class QuestionResponse(BaseModel):
    id: int
    text: str
    type: str
    answers: List[str] = []

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class TestDetailsResponse(BaseModel):
    deadline: Optional[datetime]
    questions: List[QuestionResponse]

    @validator('deadline', pre=True)
    def parse_deadline(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None
        return v


class StudentTestResultsRequest(BaseModel):
    teacher_id: str
    teacher_role: str
    test_id: str
    student_id: str

    @validator('teacher_role')
    def validate_teacher_role(cls, v):
        if v != "teacher":
            raise ValueError("Only teachers can access this endpoint")
        return v


class TestResultsResponse(BaseModel):
    data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(default_factory=dict)
    status: int = 200


class TeacherSOPResultsRequest(BaseValidationModel):
    teacher_id: Optional[str] = None
    role: RoleEnum
    current_user_id: str

    @property
    def target_teacher_id(self) -> str:
        if self.role == "admin" and self.teacher_id:
            return self.teacher_id
        return self.current_user_id

    @property
    def target_role(self) -> str:
        if self.role == "admin" and self.teacher_id:
            return "teacher"
        return self.role


class CourseSOPResultsRequest(BaseValidationModel):
    course_id: str
    user_id: str
    user_role: RoleEnum


class QuestionType(str, Enum):
    TEXT = "text"
    RATING = "rating"


class BaseQuestionResponse(BaseModel):
    question: str
    question_type: QuestionType


class TextQuestionResponse(BaseQuestionResponse):
    question_type: QuestionType = QuestionType.TEXT
    text_answer: str


class RatingQuestionResponse(BaseQuestionResponse):
    question_type: QuestionType = QuestionType.RATING
    answer: int = Field(ge=1, le=5)


SOPQuestionResponse = Union[TextQuestionResponse, RatingQuestionResponse]


class BlockTypeEnum(str, Enum):
    COURSE = "course"
    LECTURER = "lecturer"
    SEMINARIST = "seminarist"


class SOPBlockSubmit(BaseValidationModel):
    block_type: BlockTypeEnum
    teacher_id: Optional[str]
    questions_answers: List[SOPQuestionResponse]


class SOPCourseRequest(BaseModel):
    course_id: str
    blocks: List[SOPBlockSubmit]


class SOPSubmitRequest(BaseModel):
    courses: List[SOPCourseRequest]


class CourseResponse(BaseValidationModel):
    course_id: str
    name: str
    description: Optional[str]
    lector: Dict
    blocks: List[Dict]


class AnswerItem(BaseModel):
    id: int
    is_right: bool


TestUpdateRequest = List[AnswerItem]


class BlockUpdateRequest(BaseValidationModel):
    name: str = Field(..., min_length=3, max_length=100)


class BlockResponse(BaseValidationModel):
    name: str
    units: List[int]


class UnitCreateRequest(BaseValidationModel):
    name: str = Field(..., min_length=3, max_length=100)
    type: str = Field(..., pattern="^(lecture|seminar|test)$")
    content: Union[str, Dict]

    @validator('content')
    def validate_content(cls, v, values):
        if values.get('type') == 'test':
            if not isinstance(v, dict) or 'test_id' not in v:
                raise ValueError("For test units, content must be a dictionary with 'test_id'")
        return v


class UnitUpdateRequest(BaseValidationModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    type: Optional[str] = Field(None, pattern="^(lecture|seminar|test)$")
    content: Optional[Union[str, Dict]] = None

    @validator('content')
    def validate_content(cls, v, values):
        if values.get('type') == 'test':
            if not isinstance(v, dict) or 'test_id' not in v or 'test_url' not in v:
                raise ValueError("For test units, content must be a dictionary with 'test_id' or 'test_url'")
        return v


class UnitResponse(BaseValidationModel):
    name: str
    type: str
    content: Union[Dict, str]

    class Config:
        json_encoders = {
            dict: lambda v: v,
            str: lambda v: v
        }


class CourseStudentsRequest(BaseValidationModel):
    course_id: str = Field(..., min_length=1)
    user_id: str
    user_role: RoleEnum
    limit: int = Field(ge=0, le=100)
    offset: int = Field(ge=0)
    search: str = ""

    @validator('limit')
    def validate_limit(cls, v):
        if v == 0:
            raise ValueError("Limit cannot be 0. Use positive integer.")
        return v

    @validator('course_id')
    def validate_course_id(cls, v):
        if not v:
            raise ValueError("Course ID cannot be empty")
        return v


class PaginatedResponse(BaseValidationModel):
    data: List[Dict]
    total: int
    limit: int
    offset: int
