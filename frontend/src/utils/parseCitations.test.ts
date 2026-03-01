import { describe, it, expect } from "vitest";
import { parseCitations } from "./parseCitations";
import type { Citation } from "../types";

const citations: Citation[] = [
  {
    type: "archive",
    id: 1,
    doc_id: "doc_042",
    pages: [3],
    text_span: "The colonial government...",
    confidence: 0.92,
  },
  {
    type: "web",
    id: 2,
    title: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Straits",
  },
];

describe("parseCitations", () => {
  it("returns plain text when no markers present", () => {
    const result = parseCitations("Hello world", []);
    expect(result).toEqual([{ type: "text", content: "Hello world" }]);
  });

  it("parses a single archive marker", () => {
    const result = parseCitations(
      "The governor arrived [archive:1] in 1819.",
      citations
    );
    expect(result).toEqual([
      { type: "text", content: "The governor arrived " },
      { type: "citation", citation: citations[0] },
      { type: "text", content: " in 1819." },
    ]);
  });

  it("parses a web marker", () => {
    const result = parseCitations("See also [web:2].", citations);
    expect(result).toEqual([
      { type: "text", content: "See also " },
      { type: "citation", citation: citations[1] },
      { type: "text", content: "." },
    ]);
  });

  it("parses multiple markers", () => {
    const result = parseCitations(
      "Fact [archive:1] and source [web:2].",
      citations
    );
    expect(result).toHaveLength(5);
    expect(result[1]).toEqual({ type: "citation", citation: citations[0] });
    expect(result[3]).toEqual({ type: "citation", citation: citations[1] });
  });

  it("leaves unmatched markers as plain text", () => {
    const result = parseCitations("Unknown [archive:99] ref.", citations);
    expect(result).toEqual([
      { type: "text", content: "Unknown [archive:99] ref." },
    ]);
  });
});
