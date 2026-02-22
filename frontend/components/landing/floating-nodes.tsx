"use client";

import { useEffect, useRef } from "react";

const NODE_COUNT = 8;

export function FloatingNodes() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const nodes: HTMLDivElement[] = [];
    const intervals: ReturnType<typeof setInterval>[] = [];

    for (let i = 0; i < NODE_COUNT; i++) {
      const node = document.createElement("div");
      node.className =
        "absolute w-2 h-2 bg-gray-600 rounded-full transition-all duration-1000";
      node.style.top = Math.random() * 80 + 10 + "%";
      node.style.left = Math.random() * 80 + 10 + "%";
      container.appendChild(node);
      nodes.push(node);

      const interval = setInterval(
        () => {
          node.style.top = Math.random() * 80 + 10 + "%";
          node.style.left = Math.random() * 80 + 10 + "%";

          if (Math.random() > 0.7) {
            node.style.backgroundColor = "#fff";
            node.style.boxShadow = "0 0 10px rgba(255,255,255,0.5)";
            setTimeout(() => {
              node.style.backgroundColor = "#4b5563";
              node.style.boxShadow = "none";
            }, 500);
          }
        },
        2000 + Math.random() * 1000,
      );

      intervals.push(interval);
    }

    return () => {
      intervals.forEach(clearInterval);
      nodes.forEach((node) => {
        if (container.contains(node)) container.removeChild(node);
      });
    };
  }, []);

  return <div ref={containerRef} className="relative w-full h-full" />;
}
