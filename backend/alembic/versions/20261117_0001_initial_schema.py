"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("admin", "editor", "viewer", name="user_role", create_type=False)
platform = postgresql.ENUM("youtube", "instagram", name="platform", create_type=False)
campaign_status = postgresql.ENUM(
    "draft",
    "generating",
    "scheduled",
    "completed",
    "paused",
    "failed",
    name="campaign_status",
    create_type=False,
)
content_status = postgresql.ENUM(
    "pending",
    "generating",
    "ready",
    "publishing",
    "published",
    "failed",
    name="content_status",
    create_type=False,
)
video_status = postgresql.ENUM(
    "pending", "rendering", "ready", "failed", name="video_status", create_type=False
)
job_status = postgresql.ENUM(
    "scheduled", "in_progress", "published", "failed", "cancelled", name="job_status", create_type=False
)
ENUMS = (user_role, platform, campaign_status, content_status, video_status, job_status)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("interval_hours", sa.Integer(), nullable=False),
        sa.Column("publish_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("platforms", postgresql.JSONB(), nullable=False),
        sa.Column("tone", sa.String(100)),
        sa.Column("target_audience", sa.String(255)),
        sa.Column("status", campaign_status, nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_campaigns_owner_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_campaigns"),
    )
    op.create_index("ix_campaigns_owner_id", "campaigns", ["owner_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])

    op.create_table(
        "content_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("subtopic", sa.String(500)),
        sa.Column("status", content_status, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("research", postgresql.JSONB()),
        sa.Column("script", postgresql.JSONB()),
        sa.Column("seo", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name="fk_content_items_campaign_id_campaigns",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_content_items"),
        sa.UniqueConstraint("campaign_id", "sequence_number", name="uq_content_items_campaign_seq"),
    )
    op.create_index("ix_content_items_campaign_id", "content_items", ["campaign_id"])
    op.create_index("ix_content_items_status", "content_items", ["status"])
    op.create_index("ix_content_items_scheduled_at", "content_items", ["scheduled_at"])

    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=False),
        sa.Column("status", video_status, nullable=False),
        sa.Column("storyboard", postgresql.JSONB(), nullable=False),
        sa.Column("captions_srt", sa.Text()),
        sa.Column("audio_key", sa.String(1024)),
        sa.Column("video_key", sa.String(1024)),
        sa.Column("thumbnail_key", sa.String(1024)),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("error", sa.Text()),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name="fk_videos_content_item_id_content_items",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_videos"),
    )
    op.create_index("ix_videos_content_item_id", "videos", ["content_item_id"], unique=True)

    op.create_table(
        "platform_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("scopes", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_platform_accounts_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_platform_accounts"),
        sa.UniqueConstraint(
            "user_id", "platform", "external_account_id", name="uq_platform_accounts_identity"
        ),
    )
    op.create_index("ix_platform_accounts_user_id", "platform_accounts", ["user_id"])

    op.create_table(
        "publishing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=False),
        sa.Column("platform_account_id", sa.Uuid()),
        sa.Column("platform", platform, nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("external_id", sa.String(255)),
        sa.Column("external_url", sa.String(1024)),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text()),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name="fk_publishing_jobs_content_item_id_content_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["platform_account_id"],
            ["platform_accounts.id"],
            name="fk_publishing_jobs_platform_account_id_platform_accounts",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_publishing_jobs"),
        sa.UniqueConstraint("content_item_id", "platform", name="uq_publishing_jobs_item_platform"),
    )
    op.create_index("ix_publishing_jobs_content_item_id", "publishing_jobs", ["content_item_id"])
    op.create_index("ix_publishing_jobs_platform_account_id", "publishing_jobs", ["platform_account_id"])
    op.create_index("ix_publishing_jobs_status", "publishing_jobs", ["status"])
    op.create_index("ix_publishing_jobs_scheduled_at", "publishing_jobs", ["scheduled_at"])
    op.create_index("ix_publishing_jobs_external_id", "publishing_jobs", ["external_id"])

    op.create_table(
        "analytics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("publishing_job_id", sa.Uuid(), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False),
        sa.Column("likes", sa.BigInteger(), nullable=False),
        sa.Column("comments", sa.BigInteger(), nullable=False),
        sa.Column("shares", sa.BigInteger(), nullable=False),
        sa.Column("watch_time_seconds", sa.BigInteger(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["publishing_job_id"],
            ["publishing_jobs.id"],
            name="fk_analytics_publishing_job_id_publishing_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analytics"),
    )
    op.create_index("ix_analytics_publishing_job_id", "analytics", ["publishing_job_id"])
    op.create_index("ix_analytics_job_collected", "analytics", ["publishing_job_id", "collected_at"])


def downgrade() -> None:
    for table in (
        "analytics",
        "publishing_jobs",
        "platform_accounts",
        "videos",
        "content_items",
        "campaigns",
        "users",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum in reversed(ENUMS):
        enum.drop(bind, checkfirst=True)
