"use client";

import { useEffect, useRef, useState } from "react";

const WORDS = ["OVERLAP", "SIGNAL", "INSIGHT", "CLARITY"];
const CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

export function ScrambleText() {
  const [display, setDisplay] = useState(WORDS[0]);
  const indexRef = useRef(0);

  useEffect(() => {
    const scramble = (target: string) => {
      let iterations = 0;
      const interval = setInterval(() => {
        setDisplay(
          target
            .split("")
            .map((letter, i) => {
              if (i < iterations) return target[i];
              return CHARS[Math.floor(Math.random() * CHARS.length)];
            })
            .join(""),
        );

        if (iterations >= target.length) clearInterval(interval);
        iterations += 1 / 3;
      }, 30);
    };

    const cycleInterval = setInterval(() => {
      indexRef.current = (indexRef.current + 1) % WORDS.length;
      scramble(WORDS[indexRef.current]);
    }, 3000);

    return () => clearInterval(cycleInterval);
  }, []);

  return (
    <div className="text-3xl text-white font-light tracking-widest opacity-80">
      {display}
    </div>
  );
}
