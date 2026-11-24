// API contracts mirrored from backend/app/schemas (see docs/openapi.json).
export type Role = "admin" | "editor" | "viewer";
export type Platform = "youtube" | "instagram";
export type CampaignStatus = "draft" | "generating" | "scheduled" | "completed" | "paused" | "failed";
export type ContentStatus = "pending" | "generating" | "ready" | "publishing" | "published" | "failed";
export type JobStatus = "scheduled" | "in_progress" | "published" | "failed" | "cancelled";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Campaign {
  id: string;
  owner_id: string;
  name: string;
  instruction: string;
  topic: string;
  total_items: number;
  interval_hours: number;
  publish_time: string;
  timezone: string;
  start_date: string;
  platforms: Platform[];
  tone: string | null;
  target_audience: string | null;
  status: CampaignStatus;
  mode: CampaignMode;
  created_at: string;
  updated_at: string;
}

export interface SEO {
  title: string;
  description: string;
  hashtags: string[];
  tags?: string[];
}

export interface Script {
  hook: string;
  body: string[];
  cta: string;
  estimated_duration_seconds?: number;
}

export interface Research {
  summary: string;
  facts: string[];
  outline: string[];
  keywords?: string[];
}

export interface ContentItem {
  id: string;
  campaign_id: string;
  sequence_number: number;
  subtopic: string | null;
  status: ContentStatus;
  scheduled_at: string;
  research: Research | null;
  script: Script | null;
  seo: SEO | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Video {
  id: string;
  status: "pending" | "rendering" | "ready" | "failed";
  storyboard: Array<{
    index: number;
    narration: string;
    on_screen_text: string;
    visual_prompt: string;
    duration_seconds: number;
    background_color?: string;
  }>;
  captions_srt: string | null;
  video_key: string | null;
  audio_key: string | null;
  duration_seconds: number | null;
  error: string | null;
}

export interface PublishingJob {
  id: string;
  content_item_id: string;
  platform: Platform;
  status: JobStatus;
  scheduled_at: string;
  published_at: string | null;
  external_id: string | null;
  external_url: string | null;
  attempts: number;
  last_error: string | null;
}

export interface ContentItemDetail extends ContentItem {
  video: Video | null;
  publishing_jobs: PublishingJob[];
}

export interface CampaignDetail extends Campaign {
  content_items: ContentItem[];
}

export type CampaignMode = "scheduled" | "now";

export interface CampaignCreate {
  instruction: string;
  mode?: CampaignMode;
  name?: string;
  platforms: Platform[];
  timezone?: string;
  tone?: string;
  target_audience?: string;
  auto_generate?: boolean;
}

export interface CalendarEvent {
  content_item_id: string;
  campaign_id: string;
  campaign_name: string;
  title: string;
  scheduled_at: string;
  status: string;
  platforms: Platform[];
}

export interface MetricTotals {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  watch_time_seconds: number;
}

export interface AnalyticsSummary {
  totals: MetricTotals;
  published_count: number;
  scheduled_count: number;
  failed_count: number;
  campaign_count: number;
  by_platform: Array<MetricTotals & { platform: Platform; published_count: number }>;
}

export interface TimeseriesPoint extends MetricTotals {
  day: string;
}

export interface CampaignAnalytics {
  campaign_id: string;
  totals: MetricTotals;
  timeseries: TimeseriesPoint[];
  top_content: Array<MetricTotals & { content_item_id: string; title: string; platform: Platform; external_url: string | null }>;
}

export interface PlatformAccount {
  id: string;
  platform: Platform;
  account_name: string;
  external_account_id: string;
  token_expires_at: string | null;
  scopes: string[];
  is_active: boolean;
  created_at: string;
}

export type OAuthProviders = Record<Platform, boolean>;

export interface PlatformAccountCreate {
  platform: Platform;
  account_name: string;
  external_account_id: string;
  access_token: string;
  refresh_token?: string;
  scopes?: string[];
}
