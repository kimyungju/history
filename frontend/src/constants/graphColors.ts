/**
 * Category color map for the knowledge graph visualization.
 * Colors match the 5 MAIN_CATEGORIES from the Colonial Archives schema.
 */
export const CATEGORY_COLORS: Record<string, string> = {
  "General and Establishment": "#3B82F6",
  "Defence and Military": "#EF4444",
  "Economic and Financial": "#10B981",
  "Internal Relations and Research": "#8B5CF6",
  "Social Services": "#F59E0B",
};

/** Fallback color for nodes with unknown or multiple categories. */
export const DEFAULT_NODE_COLOR = "#6B7280";

/**
 * Get the display color for a node based on its first main_categories entry.
 */
export function getNodeColor(mainCategories: string[]): string {
  if (!mainCategories || mainCategories.length === 0) return DEFAULT_NODE_COLOR;
  return CATEGORY_COLORS[mainCategories[0]] ?? DEFAULT_NODE_COLOR;
}

/**
 * Threshold: only nodes with connection_count above this show labels by default.
 * Set dynamically in GraphCanvas based on the dataset.
 */
export const LABEL_VISIBILITY_PERCENTILE = 0.8; // top 20% show labels
