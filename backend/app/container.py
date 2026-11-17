"""Composition root: wires concrete implementations to abstractions (dependency injection)."""

from functools import cached_property

from app.agents import PublisherAgent, PublishingGateway, ResearchAgent, ScriptAgent, SEOAgent, VideoAgent
from app.core.config import Settings, get_settings
from app.core.security import JWTService, PasswordHasher, TokenCipher
from app.db.session import Database
from app.models.enums import Platform
from app.repository.unit_of_work import UnitOfWork
from app.services.analytics_service import AnalyticsCollector
from app.services.dispatcher import CeleryTaskDispatcher, TaskDispatcher
from app.services.generation_service import ContentGenerationService
from app.services.instruction_parser import InstructionParser
from app.services.integrations.instagram import InstagramClient
from app.services.integrations.llm import LLMClient, OpenAILLMClient
from app.services.integrations.offline_llm import OfflineLLMClient
from app.services.integrations.publishers import (
    DryRunPublisher,
    InstagramPublisher,
    PublisherRegistry,
    YouTubePublisher,
)
from app.services.integrations.storage import ObjectStorage, build_storage
from app.services.integrations.tts import ElevenLabsTextToSpeech, NullTextToSpeech, TextToSpeech
from app.services.integrations.youtube import YouTubeClient
from app.services.media.renderer import FFmpegVideoRenderer, VideoRenderer
from app.services.platform_account_service import PlatformAccountService
from app.services.publishing_service import PublishingService
from app.workflows.content_pipeline import ContentPipeline, PipelineAgents


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @cached_property
    def database(self) -> Database:
        return Database(self.settings)

    @cached_property
    def password_hasher(self) -> PasswordHasher:
        return PasswordHasher()

    @cached_property
    def jwt_service(self) -> JWTService:
        return JWTService(self.settings)

    @cached_property
    def token_cipher(self) -> TokenCipher:
        return TokenCipher(self.settings)

    @cached_property
    def llm(self) -> LLMClient:
        if self.settings.openai_api_key:
            return OpenAILLMClient(self.settings)  # type: ignore[return-value]  # tenacity wrapper
        return OfflineLLMClient()

    @cached_property
    def tts(self) -> TextToSpeech:
        if self.settings.elevenlabs_api_key:
            return ElevenLabsTextToSpeech(self.settings)
        return NullTextToSpeech()

    @cached_property
    def storage(self) -> ObjectStorage:
        return build_storage(self.settings)

    @cached_property
    def renderer(self) -> VideoRenderer:
        return FFmpegVideoRenderer(self.settings)

    @cached_property
    def youtube_client(self) -> YouTubeClient:
        return YouTubeClient(self.settings)

    @cached_property
    def instagram_client(self) -> InstagramClient:
        return InstagramClient(self.settings)

    @cached_property
    def publisher_registry(self) -> PublisherRegistry:
        if self.settings.publishing_dry_run:
            return PublisherRegistry([DryRunPublisher(Platform.YOUTUBE), DryRunPublisher(Platform.INSTAGRAM)])
        return PublisherRegistry(
            [
                YouTubePublisher(self.youtube_client, self.storage),
                InstagramPublisher(self.instagram_client, self.storage),
            ]
        )

    @cached_property
    def dispatcher(self) -> TaskDispatcher:
        return CeleryTaskDispatcher()

    def instruction_parser(self) -> InstructionParser:
        return InstructionParser(self.llm)

    def build_pipeline(self, gateway: PublishingGateway) -> ContentPipeline:
        return ContentPipeline(
            PipelineAgents(
                research=ResearchAgent(self.llm),
                script=ScriptAgent(self.llm),
                seo=SEOAgent(self.llm),
                video=VideoAgent(self.llm, self.tts, self.renderer, self.storage),
                publisher=PublisherAgent(gateway),
            )
        )

    # Factories for per-transaction services (used by API dependencies and Celery tasks)
    def platform_account_service(self, uow: UnitOfWork) -> PlatformAccountService:
        return PlatformAccountService(uow, self.token_cipher, self.youtube_client)

    def publishing_service(self, uow: UnitOfWork) -> PublishingService:
        return PublishingService(
            uow, self.publisher_registry, self.platform_account_service(uow), self.settings.publishing_dry_run
        )

    def generation_service(self, uow: UnitOfWork) -> ContentGenerationService:
        return ContentGenerationService(uow, self.build_pipeline, self.publishing_service(uow))

    def analytics_collector(self, uow: UnitOfWork) -> AnalyticsCollector:
        return AnalyticsCollector(
            uow, self.platform_account_service(uow), self.youtube_client, self.instagram_client
        )


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def set_container(container: Container | None) -> None:
    global _container
    _container = container
