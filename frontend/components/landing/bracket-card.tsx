import { ReactNode } from "react";

interface BracketCardProps {
  children: ReactNode;
  className?: string;
}

export function BracketCard({ children, className = "" }: BracketCardProps) {
  return (
    <div
      className={`relative aspect-video bg-[#0a0a0a] active-card group-hover:bg-[#0e0e0e] transition-colors duration-500 flex items-center justify-center overflow-hidden ${className}`}
    >
      <div className="bracket-corner bl-tl" />
      <div className="bracket-corner bl-tr" />
      <div className="bracket-corner bl-br" />
      <div className="bracket-corner bl-bl" />
      {children}
    </div>
  );
}
