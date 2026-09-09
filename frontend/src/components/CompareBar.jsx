import React from "react";
import { useNavigate } from "react-router-dom";
import { GitCompare, X } from "lucide-react";
import { useCompare } from "@/context/CompareContext";

export default function CompareBar() {
  const { count, clear } = useCompare();
  const navigate = useNavigate();
  if (count === 0) return null;
  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-40 bg-ink text-cream rounded-full shadow-xl flex items-center gap-4 pl-5 pr-2 py-2" data-testid="compare-bar">
      <span className="text-sm font-medium flex items-center gap-2"><GitCompare className="w-4 h-4" /> {count} produit{count > 1 ? "s" : ""} à comparer</span>
      <button onClick={() => navigate("/compare")} className="bg-brand text-white text-sm font-medium px-4 py-2 rounded-full hover:opacity-90 transition-opacity" data-testid="compare-open-btn">
        Comparer
      </button>
      <button onClick={clear} className="p-2 hover:text-brand transition-colors" data-testid="compare-clear-btn" aria-label="vider">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
