import { useCallback, useRef } from "react";
import { useAppStore } from "../stores/useAppStore";

export default function ResizableSplitter() {
  const setSplitRatio = useAppStore((s) => s.setSplitRatio);
  const isDragging = useRef(false);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;

      const onMouseMove = (moveEvent: MouseEvent) => {
        if (!isDragging.current) return;
        const ratio = moveEvent.clientX / window.innerWidth;
        setSplitRatio(ratio);
      };

      const onMouseUp = () => {
        isDragging.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [setSplitRatio]
  );

  const onTouchStart = useCallback(
    () => {
      isDragging.current = true;

      const onTouchMove = (moveEvent: TouchEvent) => {
        if (!isDragging.current) return;
        const touch = moveEvent.touches[0];
        const ratio = touch.clientX / window.innerWidth;
        setSplitRatio(ratio);
      };

      const onTouchEnd = () => {
        isDragging.current = false;
        document.removeEventListener("touchmove", onTouchMove);
        document.removeEventListener("touchend", onTouchEnd);
      };

      document.addEventListener("touchmove", onTouchMove);
      document.addEventListener("touchend", onTouchEnd);
    },
    [setSplitRatio]
  );

  return (
    <div
      className="bg-stone-700 cursor-col-resize hover:bg-ink-500 active:bg-ink-400 transition-colors"
      onMouseDown={onMouseDown}
      onTouchStart={onTouchStart}
      role="separator"
      aria-orientation="vertical"
    />
  );
}
