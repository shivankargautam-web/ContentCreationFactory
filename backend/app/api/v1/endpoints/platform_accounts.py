import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import ContainerDep, CurrentUser, EditorUser, OAuthServiceDep, PlatformAccountServiceDep
from app.core.exceptions import DomainError
from app.core.logging import get_logger
from app.models.enums import Platform
from app.schemas.platform_account import (
    OAuthAuthorization,
    OAuthProviders,
    PlatformAccountCreate,
    PlatformAccountRead,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=list[PlatformAccountRead])
async def list_accounts(user: CurrentUser, service: PlatformAccountServiceDep) -> list[PlatformAccountRead]:
    return [PlatformAccountRead.model_validate(a) for a in await service.list_accounts(user)]


@router.post("", response_model=PlatformAccountRead, status_code=status.HTTP_201_CREATED)
async def connect_account(
    payload: PlatformAccountCreate, user: EditorUser, service: PlatformAccountServiceDep
) -> PlatformAccountRead:
    """Store OAuth tokens directly (automation / advanced use). The UI uses the sign-in flow below."""
    return PlatformAccountRead.model_validate(await service.connect(user, payload))


@router.get("/oauth/providers", response_model=OAuthProviders)
async def oauth_providers(_: CurrentUser, oauth: OAuthServiceDep) -> OAuthProviders:
    """Which platforms have sign-in configured on this deployment."""
    return OAuthProviders.model_validate(oauth.providers())


@router.get("/oauth/{platform}/authorize", response_model=OAuthAuthorization)
async def oauth_authorize(platform: Platform, user: EditorUser, oauth: OAuthServiceDep) -> OAuthAuthorization:
    """Return the Google / Facebook consent URL the browser should navigate to."""
    return OAuthAuthorization(authorization_url=oauth.authorization_url(user, platform))


@router.get("/oauth/{platform}/callback", include_in_schema=False)
async def oauth_callback(
    platform: Platform,
    oauth: OAuthServiceDep,
    container: ContainerDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    """Provider redirect target: exchange the code, store the account, bounce back to Settings."""
    settings_url = f"{container.settings.public_app_url.rstrip('/')}/settings"
    if error or not code or not state:
        message = error_description or error or "Sign-in was cancelled"
        return RedirectResponse(f"{settings_url}?{urlencode({'oauth_error': message})}", status_code=302)
    try:
        result = await oauth.complete(platform, code, state)
    except DomainError as exc:
        logger.warning("oauth.callback_failed", platform=platform.value, error=str(exc))
        return RedirectResponse(f"{settings_url}?{urlencode({'oauth_error': str(exc)})}", status_code=302)
    query = urlencode({"connected": platform.value, "accounts": len(result.accounts)})
    return RedirectResponse(f"{settings_url}?{query}", status_code=302)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: uuid.UUID, user: EditorUser, service: PlatformAccountServiceDep
) -> Response:
    await service.disconnect(user, account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
