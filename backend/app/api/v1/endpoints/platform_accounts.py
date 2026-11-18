import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, EditorUser, PlatformAccountServiceDep
from app.schemas.platform_account import PlatformAccountCreate, PlatformAccountRead

router = APIRouter()


@router.get("", response_model=list[PlatformAccountRead])
async def list_accounts(user: CurrentUser, service: PlatformAccountServiceDep) -> list[PlatformAccountRead]:
    return [PlatformAccountRead.model_validate(a) for a in await service.list_accounts(user)]


@router.post("", response_model=PlatformAccountRead, status_code=status.HTTP_201_CREATED)
async def connect_account(
    payload: PlatformAccountCreate, user: EditorUser, service: PlatformAccountServiceDep
) -> PlatformAccountRead:
    """Store OAuth tokens (encrypted at rest) for a YouTube channel or Instagram business account."""
    return PlatformAccountRead.model_validate(await service.connect(user, payload))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: uuid.UUID, user: EditorUser, service: PlatformAccountServiceDep
) -> Response:
    await service.disconnect(user, account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
