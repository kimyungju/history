import { useState, useEffect } from "react";
import { apiClient } from "../api/client";
import { useAppStore } from "../stores/useAppStore";

interface OcrQuality {
  doc_id: string;
  total_pages: number;
  avg_confidence: number;
  flagged_pages: { page: number; confidence: number }[];
  flagged_count: number;
}

export default function AdminPanel() {
  const isAdminOpen = useAppStore((s) => s.isAdminOpen);
  const toggleAdmin = useAppStore((s) => s.toggleAdmin);
  const openPdfModal = useAppStore((s) => s.openPdfModal);

  const [documents, setDocuments] = useState<string[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [ocrData, setOcrData] = useState<OcrQuality | null>(null);
  useEffect(() => {
    if (!isAdminOpen) return;
    let cancelled = false;
    apiClient
      .listDocuments()
      .then((data) => { if (!cancelled) setDocuments(data.documents); })
      .catch(() => { if (!cancelled) setDocuments([]); });
    return () => { cancelled = true; };
  }, [isAdminOpen]);

  useEffect(() => {
    if (!selectedDoc) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clearing derived state on deselect
      setOcrData(null);
      return;
    }
    let cancelled = false;
    apiClient
      .getOcrQuality(selectedDoc)
      .then((data) => { if (!cancelled) setOcrData(data); })
      .catch(() => { if (!cancelled) setOcrData(null); });
    return () => { cancelled = true; };
  }, [selectedDoc]);

  if (!isAdminOpen) return null;

  return (
    <div className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center">
      <div className="bg-stone-900 rounded-xl shadow-2xl w-[700px] max-h-[80vh] flex flex-col animate-fade-in-up">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-stone-700/60">
          <h2 className="text-sm font-display font-semibold text-stone-200">
            OCR Quality — Ingested Documents
          </h2>
          <button
            onClick={toggleAdmin}
            className="text-stone-400 hover:text-stone-100 p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {documents.length === 0 && (
            <p className="text-stone-500 text-sm text-center py-8">
              No ingested documents found.
            </p>
          )}

          {documents.length > 0 && (
            <div className="space-y-2">
              {documents.map((docId) => (
                <button
                  key={docId}
                  onClick={() =>
                    setSelectedDoc(selectedDoc === docId ? null : docId)
                  }
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedDoc === docId
                      ? "bg-stone-700 text-white"
                      : "text-stone-300 hover:bg-stone-800"
                  }`}
                >
                  {docId}
                </button>
              ))}
            </div>
          )}

          {/* OCR detail for selected doc */}
          {ocrData && (
            <div className="mt-4 border-t border-stone-700/60 pt-4">
              <div className="flex items-center gap-4 mb-3">
                <span className="text-sm text-stone-300">
                  Pages: {ocrData.total_pages}
                </span>
                <span className="text-sm text-stone-300">
                  Avg confidence:{" "}
                  <span
                    className={
                      ocrData.avg_confidence < 0.7
                        ? "text-red-400"
                        : "text-green-400"
                    }
                  >
                    {(ocrData.avg_confidence * 100).toFixed(1)}%
                  </span>
                </span>
                <span className="text-sm text-stone-300">
                  Flagged: {ocrData.flagged_count}
                </span>
              </div>

              {ocrData.flagged_pages.length > 0 ? (
                <div className="space-y-1">
                  <p className="text-xs text-stone-500 mb-2">
                    Flagged pages (click to view in PDF):
                  </p>
                  {ocrData.flagged_pages.map((fp) => (
                    <button
                      key={fp.page}
                      onClick={() => openPdfModal(ocrData.doc_id, fp.page)}
                      className="flex items-center gap-3 w-full px-3 py-1.5 rounded text-sm text-left hover:bg-stone-800 transition-colors"
                    >
                      <span className="text-stone-400">
                        Page {fp.page}
                      </span>
                      <span className="text-red-400 text-xs">
                        {(fp.confidence * 100).toFixed(1)}% confidence
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-green-400">
                  All pages above confidence threshold.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
