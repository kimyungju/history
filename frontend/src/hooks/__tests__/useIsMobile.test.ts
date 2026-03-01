import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useIsMobile } from "../useIsMobile";

describe("useIsMobile", () => {
  let matchMediaMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    matchMediaMock = vi.fn((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    window.matchMedia = matchMediaMock;
  });

  it("returns false for desktop viewport", () => {
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it("returns true when media query matches", () => {
    matchMediaMock.mockReturnValue({
      matches: true,
      media: "(max-width: 768px)",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });

    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });
});
