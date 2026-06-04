from __future__ import annotations

from django.db.models import Q, QuerySet

from .models import Question, Subject


def is_student_user(user) -> bool:
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "role", None) == "student")


def scope_subject_queryset_for_user(queryset: QuerySet[Subject], user) -> QuerySet[Subject]:
    if not is_student_user(user):
        return queryset

    if user.exam_type == user.ExamType.GRADE12:
        scoped = queryset.filter(exam_type=Subject.ExamType.GRADE12)
        if user.grade12_stream in {Subject.Grade12Stream.NATURAL, Subject.Grade12Stream.SOCIAL}:
            scoped = scoped.filter(Q(grade12_stream=user.grade12_stream) | Q(grade12_stream__isnull=True))
        return scoped

    if user.exam_type == user.ExamType.EXIT:
        scoped = queryset.filter(exam_type=Subject.ExamType.EXIT)
        if user.department_id:
            scoped = scoped.filter(department_id=user.department_id)
        return scoped

    return queryset


def scope_question_queryset_for_user(queryset: QuerySet[Question], user) -> QuerySet[Question]:
    if not is_student_user(user):
        return queryset

    if user.exam_type == user.ExamType.GRADE12:
        scoped = queryset.filter(subject__exam_type=Subject.ExamType.GRADE12)
        if user.grade12_stream in {Subject.Grade12Stream.NATURAL, Subject.Grade12Stream.SOCIAL}:
            scoped = scoped.filter(Q(subject__grade12_stream=user.grade12_stream) | Q(subject__grade12_stream__isnull=True))
        return scoped

    if user.exam_type == user.ExamType.EXIT:
        scoped = queryset.filter(subject__exam_type=Subject.ExamType.EXIT)
        if user.department_id:
            scoped = scoped.filter(subject__department_id=user.department_id)
        return scoped

    return queryset


def question_belongs_to_user_track(question: Question, user) -> bool:
    if not is_student_user(user):
        return True

    if user.exam_type == user.ExamType.GRADE12:
        if question.subject.exam_type != Subject.ExamType.GRADE12:
            return False
        if user.grade12_stream in {Subject.Grade12Stream.NATURAL, Subject.Grade12Stream.SOCIAL}:
            return question.subject.grade12_stream in {user.grade12_stream, None}
        return True

    if user.exam_type == user.ExamType.EXIT:
        if question.subject.exam_type != Subject.ExamType.EXIT:
            return False
        if user.department_id:
            return getattr(question.subject, "department_id", None) == user.department_id
        return True

    return True
