import type {
  QueryRequest,
  QueryResponse,
  SignedUrlResponse,
  PageTextResponse,
  GraphNode,
  GraphOverviewPayload,
} from "../types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      `API error ${res.status}: ${body.detail ?? res.statusText}`
    );
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  postQuery(req: QueryRequest): Promise<QueryResponse> {
    return request<QueryResponse>(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  },

  getSignedUrl(docId: string, page: number): Promise<SignedUrlResponse> {
    return request<SignedUrlResponse>(
      `${API_BASE}/document/signed_url?doc_id=${encodeURIComponent(docId)}&page=${page}`,
      { method: "GET" }
    );
  },

  searchGraph(
    query: string,
    limit = 20,
    categories?: string[]
  ): Promise<GraphNode[]> {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    if (categories?.length) {
      categories.forEach((c) => params.append("categories", c));
    }
    return request<GraphNode[]>(`${API_BASE}/graph/search?${params}`, {
      method: "GET",
    });
  },

  listDocuments(): Promise<{ documents: string[] }> {
    return request<{ documents: string[] }>(`${API_BASE}/admin/documents`, {
      method: "GET",
    });
  },

  getPageText(docId: string, page: number): Promise<PageTextResponse> {
    return request<PageTextResponse>(
      `${API_BASE}/document/${encodeURIComponent(docId)}/pages/${page}/text`,
      { method: "GET" }
    );
  },

  getOverview(): Promise<GraphOverviewPayload> {
    return request<GraphOverviewPayload>(`${API_BASE}/graph/overview`, {
      method: "GET",
    });
  },

  getDocumentText(
    docId: string,
    pageStart?: number,
    pageEnd?: number,
  ): Promise<{ doc_id: string; total_pages: number; pages: Array<{ page_number: number; text: string; confidence: number }> }> {
    const params = new URLSearchParams();
    if (pageStart !== undefined) params.set("page_start", String(pageStart));
    if (pageEnd !== undefined) params.set("page_end", String(pageEnd));
    const qs = params.toString();
    const url = `${API_BASE}/document/${encodeURIComponent(docId)}/text${qs ? `?${qs}` : ""}`;
    return request(url);
  },

  getOcrQuality(docId: string): Promise<{
    doc_id: string;
    total_pages: number;
    avg_confidence: number;
    flagged_pages: { page: number; confidence: number }[];
    flagged_count: number;
  }> {
    return request(`${API_BASE}/admin/documents/${encodeURIComponent(docId)}/ocr`, {
      method: "GET",
    });
  },
};
