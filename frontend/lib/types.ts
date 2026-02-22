export interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
}

export interface Connector {
  id: string;
  provider: string;
  status: "disconnected" | "connected" | "syncing" | "ready" | "error";
  last_synced_at: string | null;
  error_message: string | null;
  config: Record<string, unknown> | null;
}

export interface Citation {
  index: number;
  title: string | null;
  url: string | null;
  snippet: string;
  author_name: string | null;
  provider: string;
  source_created_at: string | null;
  metadata: Record<string, unknown> | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number;
}

export interface GitHubRepo {
  full_name: string;
  description: string | null;
  private: boolean;
  updated_at: string | null;
  language: string | null;
  stargazers_count: number;
}

export interface GoogleDriveFolder {
  id: string;
  name: string;
}

export interface OverlapItem {
  title: string | null;
  url: string | null;
  snippet: string;
  provider: string;
  author_name: string | null;
  relevance_score: number;
}

export interface PersonOverlap {
  name: string | null;
  email: string | null;
  overlap_count: number;
  providers: string[];
}

export interface ScanResult {
  overlaps: OverlapItem[];
  people: PersonOverlap[];
  draft_message: string;
  summary: string;
}
