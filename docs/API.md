# API Contract

Base URL: `/api/v1`. Auth: `Authorization: Bearer <access_token>`.
Errors use `{"error": {"code": str, "message": str}}`; 422 responses add `details`.
Machine-readable contract: [`openapi.json`](openapi.json) (served at `/api/v1/openapi.json`, UI at `/docs`).

| Method | Path | Summary | Request | Response |
|---|---|---|---|---|
| GET | `/health/live` | Live | — | `object` |
| GET | `/health/ready` | Ready | — | 204/202 |
| POST | `/api/v1/auth/register` | Register | `RegisterRequest` | `UserRead` |
| POST | `/api/v1/auth/login` | Login | `LoginRequest` | `TokenPair` |
| POST | `/api/v1/auth/refresh` | Refresh | `RefreshRequest` | `TokenPair` |
| GET | `/api/v1/auth/me` | Me | — | `UserRead` |
| GET | `/api/v1/users` | List Users | — | `Page_UserRead_` |
| PATCH | `/api/v1/users/me` | Update Me | `UserUpdate` | `UserRead` |
| PATCH | `/api/v1/users/{user_id}/role` | Change Role | `UserRoleUpdate` | `UserRead` |
| POST | `/api/v1/campaigns` | Create Campaign | `CampaignCreate` | `CampaignDetail` |
| GET | `/api/v1/campaigns` | List Campaigns | — | `Page_CampaignRead_` |
| GET | `/api/v1/campaigns/calendar` | Calendar | — | `CalendarEvent[]` |
| GET | `/api/v1/campaigns/{campaign_id}` | Get Campaign | — | `CampaignDetail` |
| DELETE | `/api/v1/campaigns/{campaign_id}` | Delete Campaign | — | 204/202 |
| PATCH | `/api/v1/campaigns/{campaign_id}/status` | Update Status | `CampaignStatusUpdate` | `CampaignDetail` |
| POST | `/api/v1/campaigns/{campaign_id}/generate` | Generate | — | `CampaignDetail` |
| GET | `/api/v1/content-items/{item_id}` | Get Content Item | — | `ContentItemDetail` |
| POST | `/api/v1/content-items/{item_id}/regenerate` | Regenerate | — | `ContentItemDetail` |
| GET | `/api/v1/content-items/{item_id}/video-url` | Video Url | — | `VideoUrl` |
| GET | `/api/v1/platform-accounts` | List Accounts | — | `PlatformAccountRead[]` |
| POST | `/api/v1/platform-accounts` | Connect Account | `PlatformAccountCreate` | `PlatformAccountRead` |
| DELETE | `/api/v1/platform-accounts/{account_id}` | Disconnect Account | — | 204/202 |
| GET | `/api/v1/analytics/summary` | Summary | — | `AnalyticsSummary` |
| GET | `/api/v1/analytics/timeseries` | Timeseries | — | `TimeseriesPoint[]` |
| GET | `/api/v1/analytics/campaigns/{campaign_id}` | Campaign Analytics | — | `CampaignAnalytics` |

## Schemas

### AnalyticsSummary

| Field | Type | Required |
|---|---|---|
| `totals` | MetricTotals | yes |
| `published_count` | integer | yes |
| `scheduled_count` | integer | yes |
| `failed_count` | integer | yes |
| `campaign_count` | integer | yes |
| `by_platform` | array | yes |

### CalendarEvent

| Field | Type | Required |
|---|---|---|
| `content_item_id` | string | yes |
| `campaign_id` | string | yes |
| `campaign_name` | string | yes |
| `title` | string | yes |
| `scheduled_at` | string | yes |
| `status` | string | yes |
| `platforms` | array | yes |

### CampaignAnalytics

| Field | Type | Required |
|---|---|---|
| `campaign_id` | string | yes |
| `totals` | MetricTotals | yes |
| `timeseries` | array | yes |
| `top_content` | array | yes |

### CampaignCreate

| Field | Type | Required |
|---|---|---|
| `instruction` | string | yes |
| `name` | string \| null |  |
| `platforms` | array |  |
| `start_date` | string \| null |  |
| `timezone` | string \| null |  |
| `tone` | string \| null |  |
| `target_audience` | string \| null |  |
| `auto_generate` | boolean |  |

### CampaignDetail

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `owner_id` | string | yes |
| `name` | string | yes |
| `instruction` | string | yes |
| `topic` | string | yes |
| `total_items` | integer | yes |
| `interval_hours` | integer | yes |
| `publish_time` | string | yes |
| `timezone` | string | yes |
| `start_date` | string | yes |
| `platforms` | array | yes |
| `tone` | string \| null | yes |
| `target_audience` | string \| null | yes |
| `status` | CampaignStatus | yes |
| `created_at` | string | yes |
| `updated_at` | string | yes |
| `content_items` | array |  |

### CampaignRead

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `owner_id` | string | yes |
| `name` | string | yes |
| `instruction` | string | yes |
| `topic` | string | yes |
| `total_items` | integer | yes |
| `interval_hours` | integer | yes |
| `publish_time` | string | yes |
| `timezone` | string | yes |
| `start_date` | string | yes |
| `platforms` | array | yes |
| `tone` | string \| null | yes |
| `target_audience` | string \| null | yes |
| `status` | CampaignStatus | yes |
| `created_at` | string | yes |
| `updated_at` | string | yes |

### CampaignStatusUpdate

| Field | Type | Required |
|---|---|---|
| `status` | CampaignStatus | yes |

### ContentItemDetail

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `campaign_id` | string | yes |
| `sequence_number` | integer | yes |
| `subtopic` | string \| null | yes |
| `status` | ContentStatus | yes |
| `scheduled_at` | string | yes |
| `research` | object \| null | yes |
| `script` | object \| null | yes |
| `seo` | object \| null | yes |
| `error` | string \| null | yes |
| `created_at` | string | yes |
| `updated_at` | string | yes |
| `video` | VideoRead \| null |  |
| `publishing_jobs` | array |  |

### ContentItemRead

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `campaign_id` | string | yes |
| `sequence_number` | integer | yes |
| `subtopic` | string \| null | yes |
| `status` | ContentStatus | yes |
| `scheduled_at` | string | yes |
| `research` | object \| null | yes |
| `script` | object \| null | yes |
| `seo` | object \| null | yes |
| `error` | string \| null | yes |
| `created_at` | string | yes |
| `updated_at` | string | yes |

### LoginRequest

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `password` | string | yes |

### MetricTotals

| Field | Type | Required |
|---|---|---|
| `views` | integer |  |
| `likes` | integer |  |
| `comments` | integer |  |
| `shares` | integer |  |
| `watch_time_seconds` | integer |  |

### Page_CampaignRead_

| Field | Type | Required |
|---|---|---|
| `items` | array | yes |
| `total` | integer | yes |
| `limit` | integer | yes |
| `offset` | integer | yes |

### Page_UserRead_

| Field | Type | Required |
|---|---|---|
| `items` | array | yes |
| `total` | integer | yes |
| `limit` | integer | yes |
| `offset` | integer | yes |

### PlatformAccountCreate

| Field | Type | Required |
|---|---|---|
| `platform` | Platform | yes |
| `account_name` | string | yes |
| `external_account_id` | string | yes |
| `access_token` | string | yes |
| `refresh_token` | string \| null |  |
| `token_expires_at` | string \| null |  |
| `scopes` | array |  |

### PlatformAccountRead

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `platform` | Platform | yes |
| `account_name` | string | yes |
| `external_account_id` | string | yes |
| `token_expires_at` | string \| null | yes |
| `scopes` | array | yes |
| `is_active` | boolean | yes |
| `created_at` | string | yes |

### PlatformBreakdown

| Field | Type | Required |
|---|---|---|
| `views` | integer |  |
| `likes` | integer |  |
| `comments` | integer |  |
| `shares` | integer |  |
| `watch_time_seconds` | integer |  |
| `platform` | Platform | yes |
| `published_count` | integer |  |

### PublishingJobRead

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `content_item_id` | string | yes |
| `platform` | Platform | yes |
| `status` | JobStatus | yes |
| `scheduled_at` | string | yes |
| `published_at` | string \| null | yes |
| `external_id` | string \| null | yes |
| `external_url` | string \| null | yes |
| `attempts` | integer | yes |
| `last_error` | string \| null | yes |

### RefreshRequest

| Field | Type | Required |
|---|---|---|
| `refresh_token` | string | yes |

### RegisterRequest

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `password` | string | yes |
| `full_name` | string \| null |  |

### TimeseriesPoint

| Field | Type | Required |
|---|---|---|
| `views` | integer |  |
| `likes` | integer |  |
| `comments` | integer |  |
| `shares` | integer |  |
| `watch_time_seconds` | integer |  |
| `day` | string | yes |

### TokenPair

| Field | Type | Required |
|---|---|---|
| `access_token` | string | yes |
| `refresh_token` | string | yes |
| `token_type` | string |  |
| `expires_in` | integer | yes |

### TopContent

| Field | Type | Required |
|---|---|---|
| `views` | integer |  |
| `likes` | integer |  |
| `comments` | integer |  |
| `shares` | integer |  |
| `watch_time_seconds` | integer |  |
| `content_item_id` | string | yes |
| `title` | string | yes |
| `platform` | Platform | yes |
| `external_url` | string \| null | yes |

### UserRead

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `email` | string | yes |
| `full_name` | string \| null | yes |
| `role` | UserRole | yes |
| `is_active` | boolean | yes |
| `created_at` | string | yes |

### UserRoleUpdate

| Field | Type | Required |
|---|---|---|
| `role` | UserRole | yes |

### UserUpdate

| Field | Type | Required |
|---|---|---|
| `full_name` | string \| null |  |

### VideoRead

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `status` | VideoStatus | yes |
| `storyboard` | array | yes |
| `captions_srt` | string \| null | yes |
| `video_key` | string \| null | yes |
| `audio_key` | string \| null | yes |
| `duration_seconds` | number \| null | yes |
| `error` | string \| null | yes |

### VideoUrl

| Field | Type | Required |
|---|---|---|
| `url` | string | yes |
