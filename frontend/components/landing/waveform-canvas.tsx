"use client";

import { useEffect, useRef } from "react";

export function WaveformCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      canvas.width = parent.offsetWidth;
      canvas.height = parent.offsetHeight;
    };

    resize();
    window.addEventListener("resize", resize);

    let offset = 0;
    let animationId: number;

    const draw = () => {
      animationId = requestAnimationFrame(draw);

      ctx.fillStyle = "#0a0a0a";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = "#333";
      ctx.lineWidth = 1;
      ctx.beginPath();

      const cy = canvas.height / 2;

      for (let i = 0; i < canvas.width; i += 5) {
        const amplitude =
          Math.sin(i * 0.02 + offset) * (Math.sin(offset * 0.5) * 40);
        ctx.moveTo(i, cy - amplitude);
        ctx.lineTo(i, cy + amplitude);
      }

      ctx.stroke();

      // Random glitch dots
      ctx.fillStyle = "#fff";
      for (let i = 0; i < 5; i++) {
        const rx = Math.random() * canvas.width;
        const ry = cy + (Math.random() - 0.5) * 10;
        ctx.fillRect(rx, ry, 2, 2);
      }

      offset += 0.05;
    };

    draw();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="w-full h-full opacity-60" />;
}
