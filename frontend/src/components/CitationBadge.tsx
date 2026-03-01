import type { Citation } from "../types";
import { useAppStore } from "../stores/useAppStore";

interface Props {
  citation: Citation;
}

export default function CitationBadge({ citation }: Props) {
  const openPdfModal = useAppStore((s) => s.openPdfModal);

  if (citation.type === "archive") {
    return (
      <button
        className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-medium bg-ink-500/20 text-ink-400 hover:bg-ink-500/30 transition-colors cursor-pointer font-mono"
        title={citation.text_span}
        onClick={() => openPdfModal(citation.doc_id, citation.pages[0])}
      >
        {citation.doc_id}:p{citation.pages.join(",")}
      </button>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
      title={citation.title}
    >
      {citation.title}
    </a>
  );
}
