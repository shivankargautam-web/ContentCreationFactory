import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.campaign import Campaign
from app.models.content_item import ContentItem
from app.models.enums import CampaignStatus, ContentStatus, JobStatus, UserRole
from app.models.user import User
from app.repository.unit_of_work import UnitOfWork
from app.scheduler.schedule_planner import compute_schedule
from app.schemas.campaign import CalendarEvent, CampaignCreate
from app.services.dispatcher import TaskDispatcher
from app.services.instruction_parser import InstructionParser

logger = get_logger(__name__)


def scope_owner(user: User) -> uuid.UUID | None:
    """Admins see everything; everyone else is scoped to their own resources."""
    return None if user.role == UserRole.ADMIN else user.id


class CampaignService:
    def __init__(
        self,
        uow: UnitOfWork,
        parser: InstructionParser,
        dispatcher: TaskDispatcher,
        default_timezone: str,
    ) -> None:
        self._uow = uow
        self._parser = parser
        self._dispatcher = dispatcher
        self._default_tz = default_timezone

    async def create(self, user: User, payload: CampaignCreate, now: datetime | None = None) -> Campaign:
        now = now or datetime.now(UTC)
        tz_hint = payload.timezone or self._default_tz
        plan = await self._parser.parse(
            payload.instruction, now.astimezone(ZoneInfo(tz_hint)).date(), tz_hint
        )
        if payload.timezone:
            plan.timezone = payload.timezone
        start_date = payload.start_date or plan.start_date
        tone = payload.tone or plan.tone
        audience = payload.target_audience or plan.target_audience

        slots = compute_schedule(
            count=plan.total_items,
            publish_time=plan.publish_time,
            tz_name=plan.timezone,
            interval_hours=plan.interval_hours,
            now=now,
            start_date=start_date,
        )
        episodes = await self._parser.plan_series(plan.topic, plan.total_items, tone, audience)

        campaign = Campaign(
            owner_id=user.id,
            name=payload.name or f"{plan.topic[:200]} ({plan.total_items} shorts)",
            instruction=payload.instruction,
            topic=plan.topic,
            total_items=plan.total_items,
            interval_hours=plan.interval_hours,
            publish_time=plan.publish_time,
            timezone=plan.timezone,
            start_date=slots[0].astimezone(ZoneInfo(plan.timezone)).date(),
            platforms=[p.value for p in payload.platforms],
            tone=tone,
            target_audience=audience,
            status=CampaignStatus.GENERATING if payload.auto_generate else CampaignStatus.DRAFT,
            settings={"auto_generate": payload.auto_generate},
        )
        campaign.content_items = [
            ContentItem(
                sequence_number=i + 1, subtopic=episodes[i], scheduled_at=slot, status=ContentStatus.PENDING
            )
            for i, slot in enumerate(slots)
        ]
        await self._uow.campaigns.add(campaign)
        await self._uow.commit()
        logger.info("campaign.created", campaign_id=str(campaign.id), items=plan.total_items)

        if payload.auto_generate:
            for item in campaign.content_items:
                self._dispatcher.enqueue_generation(item.id)
        return await self.get(user, campaign.id)

    async def get(self, user: User, campaign_id: uuid.UUID) -> Campaign:
        campaign = await self._uow.campaigns.get_with_items(campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")
        self._authorize(user, campaign)
        return campaign

    async def list_campaigns(
        self, user: User, status: CampaignStatus | None, limit: int, offset: int
    ) -> tuple[list[Campaign], int]:
        return await self._uow.campaigns.list_for_owner(scope_owner(user), status, limit, offset)

    async def update_status(self, user: User, campaign_id: uuid.UUID, status: CampaignStatus) -> Campaign:
        campaign = await self.get(user, campaign_id)
        if status not in {CampaignStatus.PAUSED, CampaignStatus.SCHEDULED}:
            raise ValidationError("Only pausing or resuming a campaign is supported")
        if status == CampaignStatus.SCHEDULED and campaign.status != CampaignStatus.PAUSED:
            raise ValidationError("Only paused campaigns can be resumed")
        campaign.status = status
        if status == CampaignStatus.SCHEDULED:
            await self._uow.campaigns.refresh_status(campaign)
        await self._uow.commit()
        return await self.get(user, campaign_id)

    async def generate(self, user: User, campaign_id: uuid.UUID) -> Campaign:
        """(Re)queue generation for items that are pending or failed."""
        campaign = await self.get(user, campaign_id)
        queued = []
        for item in campaign.content_items:
            if item.status in {ContentStatus.PENDING, ContentStatus.FAILED}:
                item.status = ContentStatus.PENDING
                item.error = None
                queued.append(item.id)
        if campaign.status in {CampaignStatus.DRAFT, CampaignStatus.FAILED}:
            campaign.status = CampaignStatus.GENERATING
        await self._uow.commit()
        for item_id in queued:
            self._dispatcher.enqueue_generation(item_id)
        return await self.get(user, campaign_id)

    async def delete(self, user: User, campaign_id: uuid.UUID) -> None:
        campaign = await self.get(user, campaign_id)
        for item in campaign.content_items:
            for job in await self._uow.publishing_jobs.list_for_item(item.id):
                if job.status == JobStatus.SCHEDULED:
                    job.status = JobStatus.CANCELLED
        await self._uow.campaigns.delete(campaign)
        await self._uow.commit()

    async def calendar(self, user: User, start: datetime, end: datetime) -> list[CalendarEvent]:
        if end <= start:
            raise ValidationError("end must be after start")
        if (end - start).days > 92:
            raise ValidationError("Calendar window cannot exceed 92 days")
        items = await self._uow.content_items.list_in_window(scope_owner(user), start, end)
        return [
            CalendarEvent(
                content_item_id=item.id,
                campaign_id=item.campaign_id,
                campaign_name=item.campaign.name,
                title=(item.seo or {}).get("title") or item.subtopic or f"Short #{item.sequence_number}",
                scheduled_at=item.scheduled_at,
                status=item.status.value,
                platforms=item.campaign.platforms,
            )
            for item in items
        ]

    @staticmethod
    def _authorize(user: User, campaign: Campaign) -> None:
        if user.role != UserRole.ADMIN and campaign.owner_id != user.id:
            raise AuthorizationError("You do not have access to this campaign")
