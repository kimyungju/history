import { useAppStore } from "../stores/useAppStore";

export default function NodeSidebar() {
  const selectedNode = useAppStore((s) => s.selectedNode);
  const isSidebarOpen = useAppStore((s) => s.isSidebarOpen);
  const selectNode = useAppStore((s) => s.selectNode);
  const setChatInput = useAppStore((s) => s.setChatInput);
  const openPdfModal = useAppStore((s) => s.openPdfModal);

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

        {selectedNode.evidence_doc_id && (
          <div>
            <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1.5">
              Source Document
            </h3>
            <button
              onClick={() =>
                openPdfModal(
                  selectedNode.evidence_doc_id!,
                  selectedNode.evidence_page ?? 1,
                )
              }
              className="flex items-center gap-2 w-full text-left group"
            >
              <div className="flex-shrink-0 w-8 h-8 bg-stone-800 rounded flex items-center justify-center">
                <svg
                  className="w-4 h-4 text-ink-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-ink-400 group-hover:text-ink-300 transition-colors truncate">
                  {selectedNode.evidence_doc_id}
                </p>
                {selectedNode.evidence_page != null && (
                  <p className="text-xs text-stone-500">
                    Page {selectedNode.evidence_page}
                  </p>
                )}
              </div>
              <svg
                className="w-4 h-4 text-stone-600 group-hover:text-stone-400 transition-colors flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                />
              </svg>
            </button>
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
