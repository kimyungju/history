import { useGraphSearch } from "../hooks/useGraphSearch";

export default function GraphSearchBar() {
  const { query, search, isSearching } = useGraphSearch();

  return (
    <div className="absolute top-3 left-3 right-3 z-10">
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => search(e.target.value)}
          placeholder="Search entities..."
          className="w-full bg-stone-800/90 backdrop-blur-sm text-stone-100 rounded-lg pl-10 pr-4 py-2 text-sm outline-none border border-stone-700/50 focus:border-ink-500/50 focus:ring-1 focus:ring-ink-500/30 placeholder:text-stone-500 transition-colors"
        />
        {isSearching && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-ink-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
}
