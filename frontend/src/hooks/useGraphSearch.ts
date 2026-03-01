import { useState, useRef, useCallback } from "react";
import { apiClient } from "../api/client";
import { useAppStore } from "../stores/useAppStore";

export function useGraphSearch() {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const filterCategories = useAppStore((s) => s.filterCategories);
  const setGraphData = useAppStore((s) => s.setGraphData);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(
    (searchQuery: string) => {
      setQuery(searchQuery);

      if (timerRef.current) clearTimeout(timerRef.current);

      const trimmed = searchQuery.trim();
      if (!trimmed) {
        return;
      }

      timerRef.current = setTimeout(async () => {
        setIsSearching(true);
        try {
          const nodes = await apiClient.searchGraph(
            trimmed,
            20,
            filterCategories.length > 0 ? filterCategories : undefined
          );
          // Convert search results to GraphPayload (no edges, no highlights)
          if (nodes.length > 0) {
            setGraphData({
              nodes: nodes.map((n) => ({ ...n, highlighted: false })),
              edges: [],
              center_node: nodes[0].canonical_id,
            });
          }
        } catch {
          // Silently fail — search is not critical
        } finally {
          setIsSearching(false);
        }
      }, 300);
    },
    [filterCategories, setGraphData]
  );

  return { query, search, isSearching };
}
