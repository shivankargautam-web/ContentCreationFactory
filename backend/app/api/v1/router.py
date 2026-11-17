from fastapi import APIRouter

from app.api.v1.endpoints import analytics, auth, campaigns, content, platform_accounts, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(content.router, prefix="/content-items", tags=["content"])
api_router.include_router(platform_accounts.router, prefix="/platform-accounts", tags=["platform-accounts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
