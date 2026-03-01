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
    <div className="flex flex-wrap gap-1.5 px-4 py-2 border-b border-gray-800">
      {MAIN_CATEGORIES.map((cat) => {
        const active = filterCategories.includes(cat);
        return (
          <button
            key={cat}
            onClick={() => toggle(cat)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              active
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {cat}
          </button>
        );
      })}
    </div>
  );
}
