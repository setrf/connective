"use client";

import { useState } from "react";
import type { Citation } from "@/lib/types";

export function useEvidence() {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(
    null
  );
  const [activeTab, setActiveTab] = useState<"citations" | "timeline">(
    "citations"
  );

  return { selectedCitation, setSelectedCitation, activeTab, setActiveTab };
}
