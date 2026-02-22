const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { "Content-Type": "application/json" };
    if (this.token) {
      h["Authorization"] = `Bearer ${this.token}`;
    }
    return h;
  }

  async login(nextAuthToken: string): Promise<{ access_token: string }> {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: nextAuthToken }),
    });
    if (!res.ok) throw new Error("Login failed");
    return res.json();
  }

  async getMe() {
    const res = await fetch(`${API_URL}/api/auth/me`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Unauthorized");
    return res.json();
  }

  async getConnectors() {
    const res = await fetch(`${API_URL}/api/connectors`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to fetch connectors");
    return res.json();
  }

  async getOAuthUrl(provider: string): Promise<{ url: string }> {
    const res = await fetch(
      `${API_URL}/api/connectors/${provider}/oauth-url`,
      { headers: this.headers() }
    );
    if (!res.ok) throw new Error("Failed to get OAuth URL");
    return res.json();
  }

  async disconnectConnector(provider: string) {
    const res = await fetch(`${API_URL}/api/connectors/${provider}`, {
      method: "DELETE",
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to disconnect");
    return res.json();
  }

  async getGitHubRepos() {
    const res = await fetch(`${API_URL}/api/connectors/github/repos`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to fetch repos");
    return res.json();
  }

  async getGoogleDriveFolders() {
    const res = await fetch(`${API_URL}/api/connectors/google_drive/folders`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to fetch folders");
    return res.json();
  }

  async updateConnectorConfig(provider: string, config: Record<string, unknown>) {
    const res = await fetch(`${API_URL}/api/connectors/${provider}/config`, {
      method: "PATCH",
      headers: this.headers(),
      body: JSON.stringify({ config }),
    });
    if (!res.ok) throw new Error("Failed to update config");
    return res.json();
  }

  async triggerIngest(provider: string) {
    const res = await fetch(`${API_URL}/api/ingest/${provider}/trigger`, {
      method: "POST",
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to trigger ingestion");
    return res.json();
  }

  async getIngestStatus(provider: string) {
    const res = await fetch(`${API_URL}/api/ingest/${provider}/status`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to get status");
    return res.json();
  }

  chatStream(
    query: string,
    filters?: Record<string, unknown>
  ): EventSource | null {
    // SSE via EventSource requires GET, so we use fetch for POST SSE
    return null; // Use fetchChat instead
  }

  async *fetchChatStream(
    query: string,
    filters?: Record<string, unknown>
  ): AsyncGenerator<{ event: string; data: string }> {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ query, filters }),
    });

    if (!res.ok) throw new Error("Chat request failed");
    if (!res.body) throw new Error("No response body");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("event:")) {
          const event = line.slice(6).trim();
          // Next line should be data
          continue;
        }
        if (line.startsWith("data:")) {
          const data = line.slice(5).trim();
          yield { event: "data", data };
        }
      }
    }
  }

  async scan(
    content: string,
    contentType: "text" | "url" = "text"
  ) {
    const res = await fetch(`${API_URL}/api/scan`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ content, content_type: contentType }),
    });
    if (!res.ok) throw new Error("Scan failed");
    return res.json();
  }

  async clearChat() {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: "DELETE",
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to clear chat");
    return res.json();
  }

  async getChatHistory(before?: string, limit: number = 50) {
    const params = new URLSearchParams();
    if (before) params.set("before", before);
    params.set("limit", String(limit));
    const res = await fetch(`${API_URL}/api/chat/history?${params}`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to fetch chat history");
    return res.json();
  }

  async getNotifications() {
    const res = await fetch(`${API_URL}/api/notifications`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to fetch notifications");
    return res.json();
  }

  async getUnreadCount(): Promise<{ unread_count: number }> {
    const res = await fetch(`${API_URL}/api/notifications/unread-count`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to fetch unread count");
    return res.json();
  }

  async markNotificationsRead(alertIds: string[]) {
    const res = await fetch(`${API_URL}/api/notifications/mark-read`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ alert_ids: alertIds }),
    });
    if (!res.ok) throw new Error("Failed to mark as read");
    return res.json();
  }

  async markAllNotificationsRead() {
    const res = await fetch(`${API_URL}/api/notifications/mark-all-read`, {
      method: "POST",
      headers: this.headers(),
    });
    if (!res.ok) throw new Error("Failed to mark all as read");
    return res.json();
  }
}

export const apiClient = new ApiClient();
