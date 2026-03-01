import { useAppStore } from "./stores/useAppStore";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";
import GraphCanvas from "./components/GraphCanvas";
import GraphSearchBar from "./components/GraphSearchBar";
import NodeSidebar from "./components/NodeSidebar";
import PdfModal from "./components/PdfModal";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 overflow-hidden">
      <div
        className="h-full grid"
        style={{
          gridTemplateColumns: `${splitRatio * 100}% 4px 1fr`,
        }}
      >
        {/* Graph panel */}
        <div className="relative overflow-hidden bg-gray-900">
          <GraphSearchBar />
          <GraphCanvas />
          <NodeSidebar />
        </div>

        <ResizableSplitter />

        <ChatPanel />
      </div>

      <PdfModal />
    </div>
  );
}
