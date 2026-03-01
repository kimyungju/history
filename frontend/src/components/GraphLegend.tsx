import { CATEGORY_COLORS } from "../constants/graphColors";
import { useAppStore } from "../stores/useAppStore";

const categories = Object.entries(CATEGORY_COLORS);

export default function GraphLegend() {
  const hiddenCategories = useAppStore((s) => s.hiddenCategories);
  const toggleCategory = useAppStore((s) => s.toggleCategory);

  return (
    <div className="absolute bottom-3 left-3 z-10 rounded-lg bg-stone-900/85 backdrop-blur-sm border border-stone-700/50 p-3 select-none">
      <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">
        Categories
      </h4>
      <ul className="space-y-1.5">
        {categories.map(([name, color]) => {
          const isHidden = hiddenCategories.has(name);
          return (
            <li key={name}>
              <button
                onClick={() => toggleCategory(name)}
                className={`flex items-center gap-2 text-xs transition-opacity w-full text-left ${
                  isHidden ? "opacity-30" : "opacity-100"
                } hover:opacity-80`}
              >
                <span
                  className="inline-block w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="text-stone-300 truncate">{name}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
