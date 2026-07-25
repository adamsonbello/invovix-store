import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, X, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useI18n } from "@/i18n";
import api from "@/lib/api";

export default function SearchModal({ open, onClose }) {
  const { t, lang } = useI18n();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
    else {
      setQ("");
      setResults([]);
    }
  }, [open]);

  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    const id = setTimeout(() => {
      api
        .get(`/products?q=${encodeURIComponent(q)}&size=6`)
        .then((r) => setResults(r.data.items))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(id);
  }, [q]);

  const go = (id) => {
    onClose();
    navigate(`/product/${id}`);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[70] bg-ink/50 backdrop-blur-sm"
          onClick={onClose}
          data-testid="search-modal"
        >
          <motion.div
            initial={{ y: -30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -20, opacity: 0 }}
            className="bg-cream max-w-2xl mx-auto mt-24 md:mt-28 p-6 md:p-8"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-ink/20 pb-4">
              <Search className="w-5 h-5 text-stone" />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t.search.placeholder}
                className="flex-1 bg-transparent outline-none text-lg"
                data-testid="search-modal-input"
              />
              <button onClick={onClose} data-testid="search-modal-close"><X className="w-5 h-5 text-stone hover:text-ink" /></button>
            </div>

            <div className="mt-5 max-h-[50vh] overflow-auto">
              {loading ? (
                <p className="text-stone py-8 text-center">{t.common.loading}</p>
              ) : q && results.length === 0 ? (
                <p className="text-stone py-8 text-center" data-testid="search-empty">{t.search.empty}</p>
              ) : (
                results.map((p) => {
                  const title = lang === "en" ? p.title_en || p.title : p.title;
                  return (
                    <button
                      key={p.id}
                      onClick={() => go(p.id)}
                      className="w-full flex items-center gap-4 py-3 group text-left"
                      data-testid={`search-result-${p.id}`}
                    >
                      <img src={p.images?.[0]} alt={title} className="w-12 h-14 object-cover bg-[#f0efed]" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate group-hover:text-brand transition-colors">{title}</p>
                        <p className="text-stone text-sm">{p.price?.toFixed(2)}€</p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-stone opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  );
                })
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
