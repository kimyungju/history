import { useAppStore } from "../stores/useAppStore";
import { MAIN_CATEGORIES } from "../types";

export default function CategoryFilter() {
  const filterCategories = useAppStore((s) => s.filterCategories);
  const setFilterCategories = useAppStore((s) => s.setFilterCategories);

  const toggle = (cat: string) => {
    if (filterCategories.includes(cat)) {
      setFilterCategories(filterCategories.filter((c) => c !== cat));
    } else {
      setFilterCategories([...filterCategories, cat]);
    }
  };

  return (
    <div className="flex flex-wrap gap-1.5 px-4 py-2 border-b border-stone-800/60">
      {MAIN_CATEGORIES.map((cat) => {
        const active = filterCategories.includes(cat);
        return (
          <button
            key={cat}
            onClick={() => toggle(cat)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              active
                ? "bg-ink-600 text-white"
                : "bg-stone-800 text-stone-400 hover:bg-stone-700 hover:text-stone-300"
            }`}
          >
            {cat}
          </button>
        );
      })}
    </div>
  );
}
