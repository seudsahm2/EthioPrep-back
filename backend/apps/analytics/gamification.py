from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.users.models import User

from .models import BadgeDefinition, GamificationProfile, PointTransaction, UserBadge


BADGE_SEED = [
    {"slug": "first-correct", "name": "First Correct", "description": "Answer your first question correctly.", "category": BadgeDefinition.Category.MILESTONE, "points_reward": 20, "sort_order": 10},
    {"slug": "practice-rookie", "name": "Practice Rookie", "description": "Answer 50 practice questions.", "category": BadgeDefinition.Category.PRACTICE, "points_reward": 30, "sort_order": 20},
    {"slug": "practice-grinder", "name": "Practice Grinder", "description": "Answer 250 practice questions.", "category": BadgeDefinition.Category.PRACTICE, "points_reward": 75, "sort_order": 21},
    {"slug": "practice-legend", "name": "Practice Legend", "description": "Answer 1000 practice questions.", "category": BadgeDefinition.Category.PRACTICE, "points_reward": 180, "sort_order": 22},
    {"slug": "streak-3", "name": "3-Day Streak", "description": "Study 3 days in a row.", "category": BadgeDefinition.Category.STREAK, "points_reward": 20, "sort_order": 30},
    {"slug": "streak-7", "name": "7-Day Streak", "description": "Study 7 days in a row.", "category": BadgeDefinition.Category.STREAK, "points_reward": 60, "sort_order": 31},
    {"slug": "streak-14", "name": "14-Day Streak", "description": "Study 14 days in a row.", "category": BadgeDefinition.Category.STREAK, "points_reward": 120, "sort_order": 32},
    {"slug": "streak-30", "name": "30-Day Streak", "description": "Study 30 days in a row.", "category": BadgeDefinition.Category.STREAK, "points_reward": 250, "sort_order": 33},
    {"slug": "exam-finisher", "name": "Exam Finisher", "description": "Complete your first exam simulation.", "category": BadgeDefinition.Category.EXAM, "points_reward": 40, "sort_order": 40},
    {"slug": "exam-warrior", "name": "Exam Warrior", "description": "Complete 10 exam simulations.", "category": BadgeDefinition.Category.EXAM, "points_reward": 110, "sort_order": 41},
    {"slug": "perfect-exam", "name": "Perfect Exam", "description": "Score 100% in any exam simulation.", "category": BadgeDefinition.Category.EXAM, "points_reward": 150, "sort_order": 42},
    {"slug": "perfect-master", "name": "Perfect Master", "description": "Score 100% in 5 exam simulations.", "category": BadgeDefinition.Category.EXAM, "points_reward": 300, "sort_order": 43},
    {"slug": "accuracy-70", "name": "Consistency", "description": "Keep overall accuracy at 70%+ with at least 50 answers.", "category": BadgeDefinition.Category.ACCURACY, "points_reward": 70, "sort_order": 50},
    {"slug": "accuracy-90", "name": "Elite Accuracy", "description": "Keep overall accuracy at 90%+ with at least 100 answers.", "category": BadgeDefinition.Category.ACCURACY, "points_reward": 180, "sort_order": 51},
    {"slug": "points-500", "name": "Rising Star", "description": "Reach 500 points.", "category": BadgeDefinition.Category.POINTS, "points_reward": 25, "sort_order": 60},
    {"slug": "points-2000", "name": "Champion", "description": "Reach 2000 points.", "category": BadgeDefinition.Category.POINTS, "points_reward": 80, "sort_order": 61},
    {"slug": "points-5000", "name": "Grandmaster", "description": "Reach 5000 points.", "category": BadgeDefinition.Category.POINTS, "points_reward": 200, "sort_order": 62},
    {"slug": "points-10000", "name": "Hall of Fame", "description": "Reach 10000 points.", "category": BadgeDefinition.Category.POINTS, "points_reward": 400, "sort_order": 63},
    {"slug": "top-10", "name": "Top 10", "description": "Reach Top 10 on the leaderboard.", "category": BadgeDefinition.Category.MILESTONE, "points_reward": 220, "sort_order": 70},
    {"slug": "top-3", "name": "Podium", "description": "Reach Top 3 on the leaderboard.", "category": BadgeDefinition.Category.MILESTONE, "points_reward": 320, "sort_order": 71},
    {"slug": "top-1", "name": "Champion #1", "description": "Reach rank #1 on the leaderboard.", "category": BadgeDefinition.Category.MILESTONE, "points_reward": 500, "sort_order": 72},
    {"slug": "sessions-10", "name": "Daily Builder", "description": "Start 10 practice sessions.", "category": BadgeDefinition.Category.PRACTICE, "points_reward": 45, "sort_order": 80},
    {"slug": "sessions-50", "name": "Momentum", "description": "Start 50 practice sessions.", "category": BadgeDefinition.Category.PRACTICE, "points_reward": 130, "sort_order": 81},
    {"slug": "sessions-200", "name": "Unstoppable", "description": "Start 200 practice sessions.", "category": BadgeDefinition.Category.PRACTICE, "points_reward": 280, "sort_order": 82},
    {"slug": "correct-100", "name": "Sharp Mind", "description": "Get 100 correct answers.", "category": BadgeDefinition.Category.MILESTONE, "points_reward": 50, "sort_order": 90},
    {"slug": "correct-500", "name": "Precision", "description": "Get 500 correct answers.", "category": BadgeDefinition.Category.MILESTONE, "points_reward": 160, "sort_order": 91},
    {"slug": "correct-2000", "name": "Master Solver", "description": "Get 2000 correct answers.", "category": BadgeDefinition.Category.MILESTONE, "points_reward": 360, "sort_order": 92},
    {"slug": "exam-correct-500", "name": "Exam Sniper", "description": "Get 500 correct answers in exams.", "category": BadgeDefinition.Category.EXAM, "points_reward": 220, "sort_order": 100},
    {"slug": "streak-60", "name": "60-Day Streak", "description": "Study 60 days in a row.", "category": BadgeDefinition.Category.STREAK, "points_reward": 420, "sort_order": 110},
    {"slug": "streak-100", "name": "100-Day Streak", "description": "Study 100 days in a row.", "category": BadgeDefinition.Category.STREAK, "points_reward": 700, "sort_order": 111},
]


def ensure_default_badges() -> None:
    existing = {item.slug: item for item in BadgeDefinition.objects.all()}
    create_batch = []

    for payload in BADGE_SEED:
        item = existing.get(payload["slug"])
        if item is None:
            create_batch.append(BadgeDefinition(**payload))
            continue

        dirty = False
        for key in ("name", "description", "category", "points_reward", "sort_order", "is_active"):
            new_value = payload.get(key, getattr(item, key))
            if getattr(item, key) != new_value:
                setattr(item, key, new_value)
                dirty = True
        if dirty:
            item.save(update_fields=["name", "description", "category", "points_reward", "sort_order", "is_active"])

    if create_batch:
        BadgeDefinition.objects.bulk_create(create_batch)


def get_or_create_profile(user: User) -> GamificationProfile:
    profile, _ = GamificationProfile.objects.get_or_create(user=user)
    return profile


def _update_streak(profile: GamificationProfile) -> bool:
    today = timezone.localdate()
    if profile.last_activity_date == today:
        return False

    if profile.last_activity_date == today - timedelta(days=1):
        profile.current_streak += 1
    else:
        profile.current_streak = 1

    profile.last_activity_date = today
    if profile.current_streak > profile.best_streak:
        profile.best_streak = profile.current_streak
    return True


def _create_transaction(user: User, action: str, points: int, source_type: str = "", source_id: int | None = None, metadata: dict | None = None) -> None:
    PointTransaction.objects.create(
        user=user,
        action=action,
        points=points,
        source_type=source_type,
        source_id=source_id,
        metadata=metadata or {},
    )


def _badge_condition(slug: str, profile: GamificationProfile, rank: int | None) -> bool:
    accuracy = (profile.total_correct / profile.total_answered) if profile.total_answered else 0
    conditions: dict[str, bool] = {
        "first-correct": profile.total_correct >= 1,
        "practice-rookie": profile.practice_answered >= 50,
        "practice-grinder": profile.practice_answered >= 250,
        "practice-legend": profile.practice_answered >= 1000,
        "streak-3": profile.current_streak >= 3,
        "streak-7": profile.current_streak >= 7,
        "streak-14": profile.current_streak >= 14,
        "streak-30": profile.current_streak >= 30,
        "exam-finisher": profile.exam_attempts >= 1,
        "exam-warrior": profile.exam_attempts >= 10,
        "perfect-exam": profile.perfect_exams >= 1,
        "perfect-master": profile.perfect_exams >= 5,
        "accuracy-70": profile.total_answered >= 50 and accuracy >= 0.70,
        "accuracy-90": profile.total_answered >= 100 and accuracy >= 0.90,
        "points-500": profile.points >= 500,
        "points-2000": profile.points >= 2000,
        "points-5000": profile.points >= 5000,
        "points-10000": profile.points >= 10000,
        "sessions-10": profile.practice_sessions >= 10,
        "sessions-50": profile.practice_sessions >= 50,
        "sessions-200": profile.practice_sessions >= 200,
        "correct-100": profile.total_correct >= 100,
        "correct-500": profile.total_correct >= 500,
        "correct-2000": profile.total_correct >= 2000,
        "exam-correct-500": profile.exam_correct >= 500,
        "streak-60": profile.current_streak >= 60,
        "streak-100": profile.current_streak >= 100,
    }

    if slug == "top-10":
        return rank is not None and rank <= 10
    if slug == "top-3":
        return rank is not None and rank <= 3
    if slug == "top-1":
        return rank is not None and rank == 1

    return conditions.get(slug, False)


def _user_rank(user: User) -> int | None:
    top_ids = list(
        GamificationProfile.objects.select_related("user")
        .filter(user__role=User.Role.STUDENT)
        .order_by("-points", "-best_streak", "user_id")
        .values_list("user_id", flat=True)
    )
    try:
        return top_ids.index(user.id) + 1
    except ValueError:
        return None


def evaluate_and_award_badges(user: User, profile: GamificationProfile) -> list[BadgeDefinition]:
    ensure_default_badges()
    owned = set(UserBadge.objects.filter(user=user).values_list("badge__slug", flat=True))
    rank = _user_rank(user)
    newly_awarded: list[BadgeDefinition] = []

    for badge in BadgeDefinition.objects.filter(is_active=True).order_by("sort_order", "id"):
        if badge.slug in owned:
            continue
        if not _badge_condition(badge.slug, profile, rank):
            continue

        UserBadge.objects.create(user=user, badge=badge)
        profile.points += badge.points_reward
        profile.badges_count += 1
        _create_transaction(
            user,
            action=f"Badge unlocked - {badge.name}",
            points=badge.points_reward,
            source_type="badge",
            source_id=badge.id,
        )
        newly_awarded.append(badge)

    return newly_awarded


def _gamification_event_payload(profile: GamificationProfile, earned_points: int, badges: list[BadgeDefinition]) -> dict:
    return {
        "earned_points": int(earned_points),
        "total_points": int(profile.points),
        "current_streak": int(profile.current_streak),
        "best_streak": int(profile.best_streak),
        "badges_unlocked": [
            {
                "slug": badge.slug,
                "name": badge.name,
                "points_reward": int(badge.points_reward),
            }
            for badge in badges
        ],
    }


def leaderboard_rows(limit: int = 100) -> list[dict]:
    rows: list[dict] = []
    profiles = (
        GamificationProfile.objects.select_related("user")
        .filter(user__role=User.Role.STUDENT)
        .order_by("-points", "-best_streak", "user_id")
    )

    for idx, profile in enumerate(profiles[:limit], start=1):
        rows.append(
            {
                "user_id": profile.user_id,
                "name": profile.user.username,
                "points": profile.points,
                "streak": profile.current_streak,
                "rank": idx,
            }
        )
    return rows


def user_badges_payload(user: User) -> list[dict]:
    ensure_default_badges()
    owned = set(UserBadge.objects.filter(user=user).values_list("badge__slug", flat=True))
    payload = []
    for badge in BadgeDefinition.objects.filter(is_active=True).order_by("sort_order", "id"):
        payload.append(
            {
                "name": badge.name,
                "description": badge.description,
                "earned": badge.slug in owned,
            }
        )
    return payload


def points_history_payload(user: User, limit: int = 50) -> list[dict]:
    rows = PointTransaction.objects.filter(user=user).order_by("-created_at")[:limit]
    return [{"action": row.action, "points": row.points, "time": row.created_at} for row in rows]


@transaction.atomic
def record_practice_answer_event(user: User, is_correct: bool, session_id: int | None = None, subject: str | None = None) -> dict:
    profile = get_or_create_profile(user)

    profile.practice_answered += 1
    profile.total_answered += 1

    if is_correct:
        profile.practice_correct += 1
        profile.total_correct += 1
        earned_points = 10
        action = "Practice correct answer"
    else:
        earned_points = 2
        action = "Practice attempt"

    profile.points += earned_points
    _update_streak(profile)

    _create_transaction(
        user,
        action=action,
        points=earned_points,
        source_type="practice_answer",
        source_id=session_id,
        metadata={"subject": subject or "Mixed", "is_correct": is_correct},
    )

    new_badges = evaluate_and_award_badges(user, profile)
    profile.save()
    return _gamification_event_payload(profile, earned_points, new_badges)


@transaction.atomic
def record_practice_session_start(user: User) -> dict:
    profile = get_or_create_profile(user)
    profile.practice_sessions += 1
    _update_streak(profile)
    new_badges = evaluate_and_award_badges(user, profile)
    profile.save()
    return _gamification_event_payload(profile, 0, new_badges)


@transaction.atomic
def record_exam_result_event(user: User, exam_result) -> dict:
    profile = get_or_create_profile(user)

    profile.exam_attempts += 1
    profile.exam_answered += int(exam_result.total_questions or 0)
    profile.exam_correct += int(exam_result.correct_answers or 0)
    profile.total_answered += int(exam_result.total_questions or 0)
    profile.total_correct += int(exam_result.correct_answers or 0)

    earned_points = 40 + int(exam_result.correct_answers or 0) * 15
    if int(exam_result.total_questions or 0) > 0 and int(exam_result.correct_answers or 0) == int(exam_result.total_questions or 0):
        profile.perfect_exams += 1
        earned_points += 150

    profile.points += earned_points
    _update_streak(profile)

    _create_transaction(
        user,
        action=f"Exam simulation - {exam_result.subject}",
        points=earned_points,
        source_type="exam_result",
        source_id=exam_result.id,
        metadata={
            "subject": exam_result.subject,
            "correct_answers": int(exam_result.correct_answers or 0),
            "total_questions": int(exam_result.total_questions or 0),
        },
    )

    new_badges = evaluate_and_award_badges(user, profile)
    profile.save()
    return _gamification_event_payload(profile, earned_points, new_badges)
