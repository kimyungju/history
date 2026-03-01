import { describe, it, expect } from "vitest";
import type {
  ArchiveCitation,
  WebCitation,
  Citation,
  GraphNode,
  GraphPayload,
  QueryResponse,
  ChatMessage,
} from "./index";
import { MAIN_CATEGORIES } from "./index";

describe("TypeScript types", () => {
  it("ArchiveCitation has correct shape", () => {
    const citation: ArchiveCitation = {
      type: "archive",
      id: 1,
      doc_id: "doc_042",
      pages: [3, 4],
      text_span: "The colonial administration...",
      confidence: 0.92,
    };
    expect(citation.type).toBe("archive");
    expect(citation.pages).toHaveLength(2);
  });

  it("WebCitation has correct shape", () => {
    const citation: WebCitation = {
      type: "web",
      id: 2,
      title: "Wikipedia: Straits Settlements",
      url: "https://en.wikipedia.org/wiki/Straits_Settlements",
    };
    expect(citation.type).toBe("web");
  });

  it("Citation discriminated union narrows on type", () => {
    const citation: Citation = {
      type: "archive",
      id: 1,
      doc_id: "doc_001",
      pages: [1],
      text_span: "...",
      confidence: 0.9,
    };
    if (citation.type === "archive") {
      expect(citation.doc_id).toBe("doc_001");
    }
  });

  it("GraphNode has all required fields", () => {
    const node: GraphNode = {
      canonical_id: "entity_123",
      name: "Straits Settlements",
      main_categories: ["General and Establishment"],
      sub_category: null,
      attributes: { founded: "1826" },
      highlighted: true,
    };
    expect(node.highlighted).toBe(true);
  });

  it("GraphPayload contains nodes, edges, center_node", () => {
    const payload: GraphPayload = {
      nodes: [],
      edges: [],
      center_node: "entity_123",
    };
    expect(payload.center_node).toBe("entity_123");
  });

  it("QueryResponse allows null graph", () => {
    const response: QueryResponse = {
      answer: "The answer is...",
      source_type: "archive",
      citations: [],
      graph: null,
    };
    expect(response.graph).toBeNull();
  });

  it("ChatMessage stores role and content", () => {
    const msg: ChatMessage = {
      role: "assistant",
      content: "Based on the archives...",
      citations: [],
      graph: null,
    };
    expect(msg.role).toBe("assistant");
  });

  it("MAIN_CATEGORIES has 5 entries", () => {
    expect(MAIN_CATEGORIES).toHaveLength(5);
  });
});
