from sqlalchemy import Column, String, ForeignKey, Text, TIMESTAMP, PrimaryKeyConstraint, Integer, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(String, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    group_id = Column(String, ForeignKey('groups.group_id'))
    creation_time = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    created_sets = relationship("Set", back_populates="user")

    seminarist_groups = relationship(
        "Group",
        back_populates="seminarist",
        foreign_keys="[Group.seminarist_id]"
    )


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    token = Column(String(2000), primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")


class Group(Base):
    __tablename__ = 'groups'

    group_id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey('courses.course_id'), primary_key=True)
    seminarist_id = Column(String, ForeignKey('users.user_id'), nullable=False)

    seminarist = relationship(
        "User",
        back_populates="seminarist_groups",
        foreign_keys=[seminarist_id]
    )
    course = relationship("Course", back_populates="course_groups")

    __table_args__ = (
        PrimaryKeyConstraint('group_id', 'course_id'),
    )


class Course(Base):
    __tablename__ = 'courses'

    course_id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    lector_id = Column(String, ForeignKey('users.user_id'), nullable=False)

    blocks = relationship("Block", back_populates="course", cascade="all, delete")
    course_groups = relationship("Group", back_populates="course")
    sets = relationship("SetBlock", back_populates="course")


class Block(Base):
    __tablename__ = 'blocks'

    block_id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey('courses.course_id', ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)

    course = relationship("Course", back_populates="blocks")
    units = relationship("Unit", back_populates="block")


class Unit(Base):
    __tablename__ = 'units'

    unit_id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(String, ForeignKey('blocks.block_id', ondelete="CASCADE"), nullable=False)
    course_id = Column(String, ForeignKey('courses.course_id', ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)

    block = relationship("Block", back_populates="units")

    __table_args__ = (
        UniqueConstraint('block_id', 'course_id', 'name', name='_block_course_name_uc'),
    )


class Set(Base):
    __tablename__ = 'sets'

    set_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False)
    creation_time = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="created_sets")
    blocks = relationship("SetBlock", back_populates="set")


class SetBlock(Base):
    __tablename__ = 'sets_blocks'

    set_id = Column(Integer, ForeignKey('sets.set_id', ondelete="CASCADE"), primary_key=True)
    course_id = Column(String, ForeignKey('courses.course_id', ondelete="CASCADE"), primary_key=True)
    type = Column(String(50), primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)

    set = relationship("Set", back_populates="blocks")
    course = relationship("Course", back_populates="sets")
