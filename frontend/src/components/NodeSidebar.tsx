import { useAppStore } from "../stores/useAppStore";

export default function NodeSidebar() {
  const selectedNode = useAppStore((s) => s.selectedNode);
  const isSidebarOpen = useAppStore((s) => s.isSidebarOpen);
  const selectNode = useAppStore((s) => s.selectNode);
  const setChatInput = useAppStore((s) => s.setChatInput);

  if (!isSidebarOpen || !selectedNode) return null;

  const attrs = selectedNode.attributes ?? {};

  return (
    <div className="absolute top-0 right-0 h-full w-[300px] bg-stone-900 border-l border-stone-700/60 z-20 flex flex-col shadow-2xl animate-slide-in">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-stone-800/60">
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-display font-semibold text-stone-100 truncate">
            {selectedNode.name}
          </h2>
          <p className="text-xs text-stone-500 mt-0.5 truncate font-mono">
            {selectedNode.canonical_id}
          </p>
        </div>
        <button
          onClick={() => selectNode(null)}
          className="text-stone-400 hover:text-stone-200 ml-2 p-1 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {selectedNode.main_categories.length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1.5">Categories</h3>
            <div className="flex flex-wrap gap-1">
              {selectedNode.main_categories.map((cat) => (
                <span
                  key={cat}
                  className="px-2 py-0.5 bg-stone-800 text-stone-300 rounded text-xs"
                >
                  {cat}
                </span>
              ))}
            </div>
          </div>
        )}

        {selectedNode.sub_category && (
          <div>
            <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1">Sub-category</h3>
            <p className="text-sm text-stone-300">{selectedNode.sub_category}</p>
          </div>
        )}

        {Object.keys(attrs).length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1.5">Attributes</h3>
            <table className="w-full text-xs">
              <tbody>
                {Object.entries(attrs).map(([key, val]) => (
                  <tr key={key} className="border-b border-stone-800/60">
                    <td className="py-1.5 pr-2 text-stone-500 font-medium align-top whitespace-nowrap">
                      {key}
                    </td>
                    <td className="py-1.5 text-stone-300 break-words">
                      {String(val)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-stone-800/60">
        <button
          onClick={() => {
            setChatInput(`Tell me about ${selectedNode.name}`);
            selectNode(null);
          }}
          className="w-full bg-ink-600 hover:bg-ink-500 text-white text-sm font-medium py-2 rounded-lg transition-colors"
        >
          Ask about this entity
        </button>
      </div>
    </div>
  );
}
