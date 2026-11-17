from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Platform(StrEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    GENERATING = "generating"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class ContentStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class VideoStatus(StrEnum):
    PENDING = "pending"
    RENDERING = "rendering"
    READY = "ready"
    FAILED = "failed"


class JobStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"
