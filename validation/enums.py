from enum import Enum


class RoleEnum(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    LECTURER = "lecturer"
    SEMINARIST = "seminarist"


class QuestionTypeEnum(str, Enum):
    SINGLE_CHOICE = "one_of"
    MULTIPLE_CHOICE = "many"
    TEXT = "text"
    CUSTOM = "custom"
