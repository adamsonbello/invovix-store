import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Euro, ShoppingCart, Package, Users, Plus, Trash2, Download, Search, X, Edit, Mail, Tag, Settings, Sparkles, Wand2, ImagePlus, Gauge, Bot, Send, Gift, Zap } from "lucide-react";
import { useI18n } from "@/i18n";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import BlogEditor from "@/components/BlogEditor";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function Admin() {
  const { t } = useI18n();
  const [tab, setTab] = useState("analytics");
  const [stats, setStats] = useState(null);

  const loadStats = () => api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => {});
  useEffect(() => { loadStats(); }, []);

  const cards = stats
    ? [
        { icon: Euro, label: t.admin.revenue, value: `${stats.revenue.toFixed(2)}€` },
        { icon: ShoppingCart, label: t.admin.orders, value: stats.total_orders, sub: `${stats.paid_orders} ${t.admin.paid}` },
        { icon: Package, label: t.admin.products, value: stats.total_products },
        { icon: Users, label: t.admin.customers, value: stats.total_users },
      ]
    : [];

  return (
    <div className="pt-28 md:pt-32 pb-32" data-testid="admin-page">
      <div className="max-w-[1600px] mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-5xl md:text-7xl mb-10">{t.admin.title}</h1>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-ink/10 border border-ink/10 mb-12">
          {cards.map((c) => (
            <div key={c.label} className="bg-cream p-6">
              <c.icon className="w-6 h-6 text-brand mb-4" strokeWidth={1.5} />
              <p className="text-xs tracking-[0.15em] uppercase font-bold text-stone">{c.label}</p>
              <p className="font-display font-black text-3xl mt-1">{c.value}</p>
              {c.sub && <p className="text-stone text-xs mt-1">{c.sub}</p>}
            </div>
          ))}
        </div>

        <div className="flex gap-2 border-b border-ink/10 mb-10">
          {[
            { key: "analytics", label: t.admin.tabAnalytics },
            { key: "ai", label: t.admin.tabAi },
            { key: "products", label: t.admin.tabProducts },
            { key: "orders", label: t.admin.tabOrders },
            { key: "returns", label: t.admin.tabReturns },
            { key: "suppliers", label: "Fournisseurs" },
            { key: "rules", label: "Règles & Alertes" },
            { key: "cj", label: t.admin.tabCj },
            { key: "blog", label: t.admin.tabBlog },
            { key: "messages", label: t.admin.tabMessages },
            { key: "promos", label: t.admin.tabPromos },
            { key: "marketing", label: "Marketing & CRM" },
            { key: "settings", label: t.admin.tabSettings },
          ].map((tb) => (
            <button
              key={tb.key}
              onClick={() => setTab(tb.key)}
              className={`px-5 py-3 font-medium border-b-2 -mb-px transition-colors ${tab === tb.key ? "border-brand text-ink" : "border-transparent text-stone hover:text-ink"}`}
              data-testid={`admin-tab-${tb.key}`}
            >
              {tb.label}
            </button>
          ))}
        </div>

        {tab === "analytics" && <AnalyticsTab />}
        {tab === "ai" && <AiTab />}
        {tab === "products" && <ProductsTab onChange={loadStats} />}
        {tab === "orders" && <OrdersTab />}
        {tab === "returns" && <ReturnsTab />}
        {tab === "suppliers" && <SuppliersTab />}
        {tab === "rules" && <RulesTab />}
        {tab === "cj" && <CjTab onImport={loadStats} />}
        {tab === "blog" && <BlogTab />}
        {tab === "messages" && <MessagesTab />}
        {tab === "promos" && <PromosTab />}
        {tab === "marketing" && <MarketingTab />}
        {tab === "settings" && <SettingsTab />}
      </div>
    </div>
  );
}

const AI_SUBTABS = [
  { key: "rewrite", label: "Réécriture de fiche", icon: Wand2 },
  { key: "image", label: "Générateur d'images", icon: ImagePlus },
  { key: "score", label: "Scoring produit gagnant", icon: Gauge },
  { key: "assistant", label: "Assistant d'analyse", icon: Bot },
];

function AiTab() {
  const [sub, setSub] = useState("rewrite");
  const [products, setProducts] = useState([]);
  useEffect(() => { api.get("/products?size=200").then((r) => setProducts(r.data.items)).catch(() => {}); }, []);
  return (
    <div data-testid="admin-ai-tab">
      <div className="flex flex-wrap gap-2 mb-8">
        {AI_SUBTABS.map((s) => (
          <button key={s.key} onClick={() => setSub(s.key)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium border transition-colors ${sub === s.key ? "bg-ink text-cream border-ink" : "border-ink/20 text-stone hover:border-ink"}`}
            data-testid={`ai-subtab-${s.key}`}>
            <s.icon className="w-4 h-4" /> {s.label}
          </button>
        ))}
      </div>
      {sub === "rewrite" && <AiRewritePanel products={products} onSaved={() => api.get("/products?size=200").then((r) => setProducts(r.data.items))} />}
      {sub === "image" && <AiImagePanel products={products} />}
      {sub === "score" && <AiScorePanel products={products} />}
      {sub === "assistant" && <AiAssistantPanel />}
    </div>
  );
}

function AiRewritePanel({ products, onSaved }) {
  const [pid, setPid] = useState("");
  const [form, setForm] = useState({ title: "", description: "", category: "domotique", keywords_hint: "" });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);

  const pickProduct = (id) => {
    setPid(id);
    const p = products.find((x) => x.id === id);
    if (p) setForm({ title: p.title, description: (p.description || "").replace(/<[^>]+>/g, " ").slice(0, 800), category: p.category || "domotique", keywords_hint: "" });
  };

  const run = async () => {
    if (!form.title) { toast.error("Renseignez un titre"); return; }
    setLoading(true); setResult(null);
    try {
      const r = await api.post("/admin/ai/rewrite-product", form);
      setResult(r.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  };

  const applyToProduct = async () => {
    if (!pid || !result) return;
    setSaving(true);
    try {
      const p = products.find((x) => x.id === pid);
      await api.put(`/admin/products/${pid}`, {
        title: result.title || p.title,
        title_en: result.title_en || p.title_en || p.title,
        description: result.description || p.description,
        description_en: result.description_en || p.description_en || p.description,
        price: p.price,
        compare_at_price: p.compare_at_price || 0,
        category: p.category,
        images: p.images || [],
        featured: !!p.featured,
        stock: 100, active: true,
      });
      toast.success("Fiche mise à jour avec le contenu IA");
      onSaved && onSaved();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="space-y-4">
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Produit existant (optionnel)</label>
          <select value={pid} onChange={(e) => pickProduct(e.target.value)} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="ai-rewrite-product-select">
            <option value="">— Saisie libre —</option>
            {products.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
        </div>
        <In label="Titre brut" value={form.title} onChange={(v) => setForm({ ...form, title: v })} />
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Description brute</label>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={4} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="ai-rewrite-desc" />
        </div>
        <In label="Mots-clés souhaités (optionnel)" value={form.keywords_hint} onChange={(v) => setForm({ ...form, keywords_hint: v })} />
        <button onClick={run} disabled={loading} className="inline-flex items-center gap-2 bg-brand text-white px-6 py-3 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="ai-rewrite-run-btn">
          <Sparkles className="w-4 h-4" /> {loading ? "Génération…" : "Générer le contenu optimisé"}
        </button>
      </div>
      <div className="border border-ink/10 p-6 bg-white/40 min-h-[300px]" data-testid="ai-rewrite-result">
        {!result && <p className="text-stone text-sm">Le contenu optimisé apparaîtra ici (titre, description, bullet points, SEO, FAQ).</p>}
        {result && (
          <div className="space-y-4 text-sm">
            <div><p className="text-xs uppercase font-bold text-stone">Titre</p><p className="font-medium">{result.title}</p></div>
            {result.title_en && <div><p className="text-xs uppercase font-bold text-stone">Title (EN)</p><p>{result.title_en}</p></div>}
            <div><p className="text-xs uppercase font-bold text-stone">Description</p><div className="prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: result.description }} /></div>
            {result.bullet_points?.length > 0 && <div><p className="text-xs uppercase font-bold text-stone">Arguments</p><ul className="list-disc pl-5">{result.bullet_points.map((b, i) => <li key={i}>{b}</li>)}</ul></div>}
            <div><p className="text-xs uppercase font-bold text-stone">SEO</p><p className="font-medium">{result.seo_title}</p><p className="text-stone">{result.seo_description}</p></div>
            {result.keywords?.length > 0 && <div className="flex flex-wrap gap-1">{result.keywords.map((k, i) => <span key={i} className="text-xs bg-ink/5 px-2 py-1 rounded">{k}</span>)}</div>}
            {result.faq?.length > 0 && <div><p className="text-xs uppercase font-bold text-stone">FAQ</p>{result.faq.map((f, i) => <div key={i} className="mb-2"><p className="font-medium">{f.q}</p><p className="text-stone">{f.a}</p></div>)}</div>}
            {pid && <button onClick={applyToProduct} disabled={saving} className="w-full bg-ink text-cream py-3 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="ai-rewrite-apply-btn">{saving ? "…" : "Appliquer à la fiche produit"}</button>}
          </div>
        )}
      </div>
    </div>
  );
}

function AiImagePanel({ products }) {
  const [pid, setPid] = useState("");
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("lifestyle");
  const [useRef, setUseRef] = useState(true);
  const [loading, setLoading] = useState(false);
  const [img, setImg] = useState(null);
  const styles = [
    { key: "lifestyle", label: "Lifestyle" },
    { key: "white", label: "Fond blanc" },
    { key: "infographic", label: "Infographie" },
    { key: "thumbnail", label: "Miniature" },
  ];
  const run = async () => {
    if (!pid && !prompt) { toast.error("Choisissez un produit ou saisissez un prompt"); return; }
    setLoading(true); setImg(null);
    try {
      const r = await api.post("/admin/ai/generate-image", { product_id: pid || null, prompt, style, use_reference: useRef });
      setImg(r.data.url);
      toast.success(pid ? "Image générée et ajoutée au produit" : "Image générée");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="space-y-4">
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Produit (optionnel)</label>
          <select value={pid} onChange={(e) => setPid(e.target.value)} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="ai-image-product-select">
            <option value="">— Prompt libre —</option>
            {products.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
        </div>
        <In label="Prompt (sujet, optionnel si produit choisi)" value={prompt} onChange={setPrompt} />
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Style</label>
          <div className="flex flex-wrap gap-2">
            {styles.map((s) => (
              <button key={s.key} onClick={() => setStyle(s.key)} className={`px-4 py-2 rounded-full text-sm border transition-colors ${style === s.key ? "bg-ink text-cream border-ink" : "border-ink/20 hover:border-ink"}`} data-testid={`ai-image-style-${s.key}`}>{s.label}</button>
            ))}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={useRef} onChange={(e) => setUseRef(e.target.checked)} className="accent-brand w-4 h-4" data-testid="ai-image-useref" />
          Utiliser l'image produit comme référence
        </label>
        <button onClick={run} disabled={loading} className="inline-flex items-center gap-2 bg-brand text-white px-6 py-3 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="ai-image-run-btn">
          <ImagePlus className="w-4 h-4" /> {loading ? "Génération (≈20s)…" : "Générer l'image"}
        </button>
      </div>
      <div className="border border-ink/10 p-4 bg-white/40 flex items-center justify-center min-h-[300px]" data-testid="ai-image-result">
        {loading && <p className="text-stone text-sm">Génération en cours…</p>}
        {!loading && !img && <p className="text-stone text-sm">L'image générée apparaîtra ici.</p>}
        {!loading && img && <img src={img} alt="IA" className="max-h-[420px] w-auto object-contain" data-testid="ai-image-output" />}
      </div>
    </div>
  );
}

function AiScorePanel({ products }) {
  const [pid, setPid] = useState("");
  const [form, setForm] = useState({ title: "", description: "", category: "domotique", sell_price: "", cost_price: "" });
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(null);
  const pick = (id) => {
    setPid(id);
    const p = products.find((x) => x.id === id);
    if (p) setForm({ title: p.title, description: (p.description || "").replace(/<[^>]+>/g, " ").slice(0, 500), category: p.category || "domotique", sell_price: p.price || "", cost_price: p.buy_price || "" });
  };
  const run = async () => {
    if (!form.title) { toast.error("Renseignez un titre"); return; }
    setLoading(true); setRes(null);
    try {
      const r = await api.post("/admin/ai/product-score", { ...form, sell_price: parseFloat(form.sell_price) || 0, cost_price: parseFloat(form.cost_price) || 0 });
      setRes(r.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  };
  const verdictColor = (v) => v === "gagnant" ? "text-green-600" : v === "à éviter" ? "text-brand" : "text-amber-600";
  const Bar = ({ label, val }) => (
    <div><div className="flex justify-between text-xs mb-1"><span className="text-stone">{label}</span><span className="font-bold">{val}</span></div><div className="h-2 bg-ink/10 rounded"><div className="h-2 bg-brand rounded" style={{ width: `${val}%` }} /></div></div>
  );
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="space-y-4">
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Produit existant (optionnel)</label>
          <select value={pid} onChange={(e) => pick(e.target.value)} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="ai-score-product-select">
            <option value="">— Saisie libre —</option>
            {products.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
        </div>
        <In label="Titre" value={form.title} onChange={(v) => setForm({ ...form, title: v })} />
        <div className="grid grid-cols-2 gap-4">
          <In label="Prix vente (€)" type="number" value={form.sell_price} onChange={(v) => setForm({ ...form, sell_price: v })} />
          <In label="Prix achat (€)" type="number" value={form.cost_price} onChange={(v) => setForm({ ...form, cost_price: v })} />
        </div>
        <button onClick={run} disabled={loading} className="inline-flex items-center gap-2 bg-brand text-white px-6 py-3 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="ai-score-run-btn">
          <Gauge className="w-4 h-4" /> {loading ? "Analyse…" : "Évaluer le produit"}
        </button>
      </div>
      <div className="border border-ink/10 p-6 bg-white/40 min-h-[300px]" data-testid="ai-score-result">
        {!res && <p className="text-stone text-sm">Le score d'opportunité et l'analyse apparaîtront ici.</p>}
        {res && (
          <div className="space-y-4">
            <div className="flex items-end gap-4">
              <div><p className="text-xs uppercase font-bold text-stone">Score d'opportunité</p><p className="font-display font-black text-5xl">{res.opportunity_score}<span className="text-2xl text-stone">/100</span></p></div>
              <p className={`font-bold uppercase ${verdictColor(res.verdict)}`} data-testid="ai-score-verdict">{res.verdict}</p>
            </div>
            <div className="space-y-2">
              <Bar label="Demande" val={res.demand} />
              <Bar label="Marge" val={res.margin} />
              <Bar label="Concurrence" val={res.competition} />
            </div>
            <p className="text-sm"><span className="text-stone">Tendance :</span> <span className="font-medium">{res.trend}</span> · <span className="text-stone">Marge :</span> <span className="font-medium">{res.margin_pct}%</span> · <span className="text-stone">Prix conseillé :</span> <span className="font-medium">{res.recommended_price}€</span></p>
            {res.reasons?.length > 0 && <ul className="list-disc pl-5 text-sm">{res.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
            {res.target_audience && <p className="text-sm text-stone">🎯 {res.target_audience}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

function AiAssistantPanel() {
  const [msgs, setMsgs] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const suggestions = [
    "Quels sont mes produits les plus rentables ?",
    "Quels produits devrais-je retirer du catalogue ?",
    "Comment augmenter mon panier moyen ?",
    "Résume la santé de ma boutique.",
  ];
  const ask = async (question) => {
    const text = question || q;
    if (!text.trim()) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setQ(""); setLoading(true);
    try {
      const r = await api.post("/admin/ai/analyze", { question: text });
      setMsgs((m) => [...m, { role: "ai", text: r.data.answer }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "ai", text: "Erreur : " + formatApiError(e.response?.data?.detail) }]);
    } finally { setLoading(false); }
  };
  return (
    <div className="max-w-3xl" data-testid="ai-assistant">
      {msgs.length === 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => ask(s)} className="text-sm border border-ink/20 rounded-full px-4 py-2 hover:border-ink transition-colors" data-testid={`ai-suggestion-${i}`}>{s}</button>
          ))}
        </div>
      )}
      <div className="space-y-4 mb-6">
        {msgs.map((m, i) => (
          <div key={i} className={`p-4 border ${m.role === "user" ? "border-ink/20 bg-white/40 ml-8" : "border-brand/30 bg-brand/5 mr-8"}`} data-testid={`ai-msg-${m.role}`}>
            <p className="text-xs uppercase font-bold text-stone mb-1">{m.role === "user" ? "Vous" : "Assistant IA"}</p>
            <div className="prose prose-sm max-w-none whitespace-pre-wrap">{m.text}</div>
          </div>
        ))}
        {loading && <div className="p-4 border border-brand/30 bg-brand/5 mr-8 text-stone text-sm">L'assistant réfléchit…</div>}
      </div>
      <div className="flex gap-2 sticky bottom-4">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} placeholder="Posez une question sur votre boutique…" className="flex-1 px-4 py-3 border border-ink/20 bg-cream outline-none focus:border-ink" data-testid="ai-assistant-input" />
        <button onClick={() => ask()} disabled={loading} className="inline-flex items-center gap-2 bg-ink text-cream px-5 py-3 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="ai-assistant-send-btn">
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

const EMPTY = { title: "", title_en: "", price: "", compare_at_price: "", category: "smart-home", subcategory: "", brand: "", sku: "", ean: "", buy_price: "", weight: "", dimensions: "", supplier_id: "", supplier_url: "", video_url: "", images: "", description: "", description_en: "", featured: false };

function ProductsTab({ onChange }) {
  const { t } = useI18n();
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [suppliers, setSuppliers] = useState([]);

  const load = () => api.get("/products?size=100").then((r) => setProducts(r.data.items));
  useEffect(() => { load(); api.get("/admin/suppliers").then((r) => setSuppliers(r.data.items)).catch(() => {}); }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setShowForm(true); };
  const openEdit = (p) => {
    setEditing(p.id);
    setForm({ ...EMPTY, ...p, price: p.price, compare_at_price: p.compare_at_price || "", buy_price: p.buy_price || p.cost_price || "", images: (p.images || []).join(", ") });
    setShowForm(true);
  };

  const save = async (e) => {
    e.preventDefault();
    const payload = {
      title: form.title,
      title_en: form.title_en || form.title,
      description: form.description,
      description_en: form.description_en || form.description,
      price: parseFloat(form.price),
      compare_at_price: form.compare_at_price ? parseFloat(form.compare_at_price) : 0,
      category: form.category,
      subcategory: form.subcategory || "",
      brand: form.brand || "",
      sku: form.sku || "",
      ean: form.ean || "",
      buy_price: form.buy_price ? parseFloat(form.buy_price) : 0,
      weight: form.weight ? parseFloat(form.weight) : 0,
      dimensions: form.dimensions || "",
      supplier_id: form.supplier_id || "",
      supplier_url: form.supplier_url || "",
      video_url: form.video_url || "",
      images: form.images.split(",").map((s) => s.trim()).filter(Boolean),
      featured: !!form.featured,
      stock: 100,
      active: true,
    };
    try {
      if (editing) await api.put(`/admin/products/${editing}`, payload);
      else await api.post("/admin/products", payload);
      toast.success("OK");
      setShowForm(false);
      load();
      onChange();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const del = async (id) => {
    await api.delete(`/admin/products/${id}`);
    load();
    onChange();
    toast.success("OK");
  };

  const [syncing, setSyncing] = useState(false);
  const syncStocks = async () => {
    setSyncing(true);
    try {
      const r = await api.post("/admin/products/sync-stock-all");
      toast.success(`${t.admin.syncStock} (${r.data.queued})`);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSyncing(false); }
  };

  const [aiBusy, setAiBusy] = useState("");
  const optimizeOne = async (id) => {
    setAiBusy(id);
    try {
      const r = await api.post(`/admin/ai/optimize-product/${id}`, { rewrite: true, image: false, score: true });
      toast.success(`Optimisé (${(r.data.done || []).join(", ")})`);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setAiBusy(""); }
  };

  // AI helpers inside the product form
  const [formAi, setFormAi] = useState("");
  const aiRewriteForm = async () => {
    if (!form.title) { toast.error("Renseignez un titre d'abord"); return; }
    setFormAi("rewrite");
    try {
      const r = await api.post("/admin/ai/rewrite-product", {
        title: form.title,
        description: (form.description || "").replace(/<[^>]+>/g, " ").slice(0, 800),
        category: form.category,
      });
      const d = r.data;
      setForm((f) => ({ ...f, title: d.title || f.title, title_en: d.title_en || f.title_en, description: d.description || f.description, description_en: d.description_en || f.description_en }));
      toast.success("Fiche optimisée par l'IA");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setFormAi(""); }
  };
  const aiImageForm = async () => {
    if (!form.title) { toast.error("Renseignez un titre d'abord"); return; }
    setFormAi("image");
    try {
      const r = await api.post("/admin/ai/generate-image", { prompt: form.title, style: "white", use_reference: false });
      setForm((f) => ({ ...f, images: f.images ? `${f.images}, ${r.data.url}` : r.data.url }));
      toast.success("Image IA ajoutée");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setFormAi(""); }
  };

  return (
    <div data-testid="admin-products-tab">
      <div className="flex justify-end gap-3 mb-6">
        <button onClick={syncStocks} disabled={syncing} className="inline-flex items-center gap-2 border border-ink/20 px-5 py-3 rounded-full font-medium hover:border-ink transition-colors disabled:opacity-50" data-testid="sync-stock-btn">
          <Download className="w-4 h-4" /> {syncing ? t.common.loading : t.admin.syncStock}
        </button>
        <button onClick={openNew} className="inline-flex items-center gap-2 bg-ink text-cream px-5 py-3 rounded-full font-medium hover:bg-brand transition-colors" data-testid="add-product-btn">
          <Plus className="w-4 h-4" /> {t.admin.addProduct}
        </button>
      </div>

      <div className="border border-ink/10 divide-y divide-ink/10">
        {products.map((p) => (
          <div key={p.id} className="flex items-center gap-4 p-4" data-testid={`admin-product-${p.id}`}>
            <img src={p.images?.[0]} alt={p.title} className="w-14 h-16 object-cover bg-[#f0efed]" />
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{p.title}</p>
              <p className="text-stone text-sm">
                {p.category} · {p.price.toFixed(2)}€ {p.featured && `· ${t.admin.featured}`}
                {p.ai_score?.opportunity_score != null && <span className="ml-2 inline-block bg-brand/10 text-brand px-2 py-0.5 rounded text-xs font-bold" data-testid={`ai-score-badge-${p.id}`}>IA {p.ai_score.opportunity_score}/100</span>}
                {p.ai_optimized && <span className="ml-1 inline-block text-green-600 text-xs">✨ optimisé</span>}
              </p>
            </div>
            <button onClick={() => optimizeOne(p.id)} disabled={aiBusy === p.id} className="inline-flex items-center gap-1.5 text-sm border border-ink/20 rounded-full px-3 py-1.5 hover:border-brand hover:text-brand transition-colors disabled:opacity-50" data-testid={`ai-optimize-${p.id}`}>
              <Sparkles className="w-3.5 h-3.5" /> {aiBusy === p.id ? "…" : "IA"}
            </button>
            <button onClick={() => openEdit(p)} className="text-sm text-stone hover:text-ink px-3" data-testid={`edit-${p.id}`}>{t.admin.edit}</button>
            <button onClick={() => del(p.id)} className="text-brand hover:opacity-70 p-2" data-testid={`delete-${p.id}`}><Trash2 className="w-4 h-4" /></button>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 bg-ink/40 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <motion.form
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            onClick={(e) => e.stopPropagation()} onSubmit={save}
            className="bg-cream w-full max-w-2xl p-8 max-h-[90vh] overflow-auto" data-testid="product-form"
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-display font-bold text-2xl">{editing ? t.admin.edit : t.admin.newProduct}</h3>
              <button type="button" onClick={() => setShowForm(false)}><X className="w-6 h-6" /></button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <In label={t.admin.ptitle + " (FR)"} value={form.title} onChange={(v) => setForm({ ...form, title: v })} required span2 />
              <In label={t.admin.ptitle + " (EN)"} value={form.title_en} onChange={(v) => setForm({ ...form, title_en: v })} span2 />
              <In label={t.admin.pprice} type="number" value={form.price} onChange={(v) => setForm({ ...form, price: v })} required />
              <In label={t.admin.pcompare} type="number" value={form.compare_at_price} onChange={(v) => setForm({ ...form, compare_at_price: v })} />
              <In label="Prix d'achat (€)" type="number" value={form.buy_price} onChange={(v) => setForm({ ...form, buy_price: v })} />
              <div className="flex items-end pb-3">
                <p className="text-sm" data-testid="form-margin">Marge : <span className="font-bold text-brand">{form.price && form.buy_price ? `${(((parseFloat(form.price) - parseFloat(form.buy_price)) / parseFloat(form.price)) * 100).toFixed(1)}%` : "—"}</span></p>
              </div>
              <In label="Marque" value={form.brand} onChange={(v) => setForm({ ...form, brand: v })} />
              <In label="Sous-catégorie" value={form.subcategory} onChange={(v) => setForm({ ...form, subcategory: v })} />
              <In label="SKU" value={form.sku} onChange={(v) => setForm({ ...form, sku: v })} />
              <In label="EAN / code-barres" value={form.ean} onChange={(v) => setForm({ ...form, ean: v })} />
              <In label="Poids (kg)" type="number" value={form.weight} onChange={(v) => setForm({ ...form, weight: v })} />
              <In label="Dimensions (LxlxH)" value={form.dimensions} onChange={(v) => setForm({ ...form, dimensions: v })} />
              <div>
                <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Fournisseur</label>
                <select value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="form-supplier">
                  <option value="">— Aucun —</option>
                  {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <In label="URL fournisseur" value={form.supplier_url} onChange={(v) => setForm({ ...form, supplier_url: v })} />
              <In label="URL vidéo" value={form.video_url} onChange={(v) => setForm({ ...form, video_url: v })} span2 />
              <div>
                <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.pcat}</label>
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="form-category">
                  <option value="smart-home">smart-home</option>
                  <option value="workspace">workspace</option>
                  <option value="security">security</option>
                </select>
              </div>
              <div className="flex items-end pb-3">
                <label className="flex items-center gap-2 font-medium">
                  <input type="checkbox" checked={form.featured} onChange={(e) => setForm({ ...form, featured: e.target.checked })} className="accent-brand w-4 h-4" data-testid="form-featured" />
                  {t.admin.featured}
                </label>
              </div>
              <In label={t.admin.pimg} value={form.images} onChange={(v) => setForm({ ...form, images: v })} span2 />
              <div className="md:col-span-2">
                <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.pdesc} (FR)</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="form-desc" />
              </div>
            </div>
            <div className="flex flex-wrap gap-3 mt-6">
              <button type="button" onClick={aiRewriteForm} disabled={!!formAi} className="inline-flex items-center gap-2 border border-ink/20 px-4 py-2.5 rounded-full text-sm font-medium hover:border-brand hover:text-brand transition-colors disabled:opacity-50" data-testid="form-ai-rewrite-btn">
                <Wand2 className="w-4 h-4" /> {formAi === "rewrite" ? "Optimisation…" : t.admin.aiRewriteBtn}
              </button>
              <button type="button" onClick={aiImageForm} disabled={!!formAi} className="inline-flex items-center gap-2 border border-ink/20 px-4 py-2.5 rounded-full text-sm font-medium hover:border-brand hover:text-brand transition-colors disabled:opacity-50" data-testid="form-ai-image-btn">
                <ImagePlus className="w-4 h-4" /> {formAi === "image" ? "Génération (≈20s)…" : t.admin.aiImageBtn}
              </button>
            </div>
            <button type="submit" className="w-full mt-4 bg-brand text-white py-4 rounded-full font-medium hover:bg-ink transition-colors" data-testid="save-product-btn">{t.admin.save}</button>
          </motion.form>
        </div>
      )}
    </div>
  );
}

function OrdersTab() {
  const { t } = useI18n();
  const [orders, setOrders] = useState([]);
  const [busy, setBusy] = useState("");
  const statuses = ["pending", "processing", "shipped", "delivered", "cancelled"];
  const load = () => api.get("/admin/orders").then((r) => setOrders(r.data.items));
  useEffect(() => { load(); }, []);

  const setStatus = async (id, status) => {
    await api.put(`/admin/orders/${id}/status?status=${status}`);
    load();
    toast.success("OK");
  };

  const fulfill = async (id) => {
    setBusy(id + "-f");
    try {
      const r = await api.post(`/admin/orders/${id}/fulfill`);
      if (r.data.cj_order_id) toast.success(`CJ #${r.data.cj_order_id}`);
      else toast.error(r.data.fulfillment_error || "Erreur CJ");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const syncCj = async (id) => {
    setBusy(id + "-s");
    try {
      const r = await api.post(`/admin/orders/${id}/sync-cj`);
      toast.success(r.data.ok ? `${r.data.status || "OK"}${r.data.tracking_number ? " · " + r.data.tracking_number : ""}` : (r.data.reason || "—"));
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  return (
    <div className="border border-ink/10 divide-y divide-ink/10" data-testid="admin-orders-tab">
      {orders.length === 0 && <p className="p-8 text-stone text-center">{t.account.noOrders}</p>}
      {orders.map((o) => (
        <div key={o.id} className="p-5" data-testid={`admin-order-${o.id}`}>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[180px]">
              <p className="font-medium">#{o.id.slice(0, 8).toUpperCase()}</p>
              <p className="text-stone text-sm">{o.user_email} · {new Date(o.created_at).toLocaleDateString()}</p>
            </div>
            <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${o.payment_status === "paid" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{o.payment_status}</span>
            <p className="font-display font-bold text-lg w-24 text-right">{o.total.toFixed(2)}€</p>
            <select value={o.status} onChange={(e) => setStatus(o.id, e.target.value)} className="border border-ink/20 px-3 py-2 bg-transparent outline-none text-sm" data-testid={`order-status-${o.id}`}>
              {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-3 mt-3 text-sm">
            {o.cj_order_id ? (
              <span className="text-stone">CJ #{o.cj_order_id}{o.cj_shipping_status ? ` · ${o.cj_shipping_status}` : ""}</span>
            ) : (
              <button onClick={() => fulfill(o.id)} disabled={busy === o.id + "-f"} className="px-3 py-1.5 border border-ink text-xs font-medium hover:bg-ink hover:text-cream transition-colors disabled:opacity-50" data-testid={`order-fulfill-${o.id}`}>
                {busy === o.id + "-f" ? "…" : "Fulfill CJ"}
              </button>
            )}
            {o.cj_order_id && (
              <button onClick={() => syncCj(o.id)} disabled={busy === o.id + "-s"} className="px-3 py-1.5 border border-ink/30 text-xs font-medium hover:border-ink transition-colors disabled:opacity-50" data-testid={`order-sync-${o.id}`}>
                {busy === o.id + "-s" ? "…" : "Sync suivi"}
              </button>
            )}
            {o.tracking_number && (
              <span className="text-brand font-medium" data-testid={`order-tracking-${o.id}`}>📦 {o.logistic_name || ""} {o.tracking_number}</span>
            )}
            {o.fulfillment_error && <span className="text-red-500 text-xs">{o.fulfillment_error}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

function CjTab({ onImport }) {
  const { t } = useI18n();
  const [configured, setConfigured] = useState(null);
  const [q, setQ] = useState("smart home");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [margin, setMargin] = useState(60);
  const [category, setCategory] = useState("smart-home");
  const [importedPids, setImportedPids] = useState({});
  const [busy, setBusy] = useState(false);
  const [autoOptimize, setAutoOptimize] = useState(false);

  useEffect(() => {
    api.get("/admin/cj/status").then((r) => setConfigured(r.data.configured)).catch(() => setConfigured(false));
  }, []);

  const search = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/admin/cj/search?q=${encodeURIComponent(q)}`);
      setResults(r.data.items || []);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  const importOne = async (pid) => {
    setImportedPids((s) => ({ ...s, [pid]: "loading" }));
    try {
      const r = await api.post(`/admin/cj/import/${pid}?margin=${Number(margin)}&category=${category}&optimize=${autoOptimize}`);
      setImportedPids((s) => ({ ...s, [pid]: "done" }));
      toast.success(`${t.admin.imported}: ${(r.data.title || "").slice(0, 28)} · ${r.data.price}€${autoOptimize ? " · ✨ IA" : ""}`);
      onImport();
    } catch (e) {
      setImportedPids((s) => ({ ...s, [pid]: undefined }));
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  const importAll = async () => {
    const pids = results.map((p) => p.pid).filter((pid) => importedPids[pid] !== "done");
    if (!pids.length) return;
    setBusy(true);
    try {
      const r = await api.post(`/admin/cj/import-bulk`, { pids, margin: Number(margin), category, optimize: autoOptimize });
      const done = {};
      (r.data.results || []).forEach((x) => {
        if (x.status === "imported" || x.status === "skipped") done[x.pid] = "done";
      });
      setImportedPids((s) => ({ ...s, ...done }));
      toast.success(`${r.data.imported} importés · ${r.data.skipped} déjà présents · ${r.data.errors} erreurs`);
      onImport();
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  if (configured === false) {
    return (
      <div className="border border-dashed border-ink/20 p-12 text-center" data-testid="cj-not-configured">
        <Download className="w-10 h-10 mx-auto text-ink/30" strokeWidth={1.2} />
        <p className="text-stone mt-4 max-w-md mx-auto">{t.admin.cjNotConfigured}</p>
      </div>
    );
  }

  return (
    <div data-testid="admin-cj-tab">
      <div className="flex gap-2 mb-4 max-w-xl">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-stone" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder={t.admin.cjSearch}
            className="w-full pl-11 pr-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink"
            data-testid="cj-search-input"
          />
        </div>
        <button onClick={search} className="bg-ink text-cream px-6 font-medium hover:bg-brand transition-colors" data-testid="cj-search-btn">
          {loading ? "…" : t.admin.cjSearch}
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-4 mb-8 p-4 bg-surface border border-ink/10">
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.margin}</label>
          <input
            type="number"
            value={margin}
            onChange={(e) => setMargin(e.target.value)}
            className="w-28 px-4 py-2.5 border border-ink/20 bg-cream outline-none focus:border-ink"
            data-testid="cj-margin"
          />
        </div>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.pcat}</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="px-4 py-2.5 border border-ink/20 bg-cream outline-none" data-testid="cj-category">
            <option value="smart-home">smart-home</option>
            <option value="workspace">workspace</option>
            <option value="security">security</option>
          </select>
        </div>
        <label className="flex items-center gap-2 font-medium text-sm pb-2.5 cursor-pointer" title="Réécrit la fiche + calcule un score IA à chaque import">
          <input type="checkbox" checked={autoOptimize} onChange={(e) => setAutoOptimize(e.target.checked)} className="accent-brand w-4 h-4" data-testid="cj-auto-optimize" />
          <Sparkles className="w-4 h-4 text-brand" /> Optimiser à l'import (IA)
        </label>
        {results.length > 0 && (
          <button
            onClick={importAll}
            disabled={busy}
            className="ml-auto bg-brand text-white px-6 py-3 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50 flex items-center gap-2"
            data-testid="cj-import-all"
          >
            <Download className="w-4 h-4" /> {busy ? t.admin.importing : `${t.admin.importAll} (${results.length})`}
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {results.map((p) => {
          const st = importedPids[p.pid];
          return (
            <div key={p.pid} className="border border-ink/10 p-3">
              <img
                src={p.productImage || (p.productImageSet || [])[0]}
                alt=""
                referrerPolicy="no-referrer"
                className="w-full aspect-square object-cover bg-[#f0efed]"
              />
              <p className="text-sm mt-2 line-clamp-2 h-10">{p.productNameEn || p.productName}</p>
              <button
                onClick={() => importOne(p.pid)}
                disabled={st === "loading" || st === "done"}
                className={`w-full mt-2 text-sm py-2 transition-colors disabled:opacity-70 ${
                  st === "done" ? "bg-emerald-600 text-white" : "border border-ink hover:bg-ink hover:text-cream"
                }`}
                data-testid={`cj-import-${p.pid}`}
              >
                {st === "done" ? t.admin.imported : st === "loading" ? t.admin.importing : t.admin.cjImport}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function In({ label, value, onChange, type = "text", required, span2 }) {
  return (
    <div className={span2 ? "md:col-span-2" : ""}>
      <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{label}</label>
      <input type={type} step="any" value={value} required={required} onChange={(e) => onChange(e.target.value)} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" />
    </div>
  );
}

function BlogTab() {
  const { t, lang } = useI18n();
  const [posts, setPosts] = useState([]);
  const [editing, setEditing] = useState(null); // post object or "new"

  const load = () => api.get("/admin/blog").then((r) => setPosts(r.data.items)).catch(() => {});
  useEffect(() => { load(); }, []);

  const openEdit = async (id) => {
    const r = await api.get(`/admin/blog/${id}`);
    setEditing(r.data);
  };

  const remove = async (id, title) => {
    if (!window.confirm(`${t.admin.delete} : ${title} ?`)) return;
    await api.delete(`/admin/blog/${id}`);
    toast.success("OK");
    load();
  };

  return (
    <div data-testid="admin-blog-tab">
      <div className="flex justify-between items-center mb-6">
        <p className="text-stone text-sm">{posts.length}</p>
        <button
          onClick={() => setEditing("new")}
          className="inline-flex items-center gap-2 bg-brand text-white px-5 py-2.5 rounded-full font-medium hover:bg-ink transition-colors"
          data-testid="blog-new-btn"
        >
          <Plus className="w-4 h-4" /> {t.admin.newPost}
        </button>
      </div>

      {posts.length === 0 ? (
        <p className="text-stone py-16 text-center" data-testid="admin-blog-empty">{t.admin.noPosts}</p>
      ) : (
        <div className="border border-ink/10 divide-y divide-ink/10">
          {posts.map((p) => (
            <div key={p.id} className="flex items-center gap-4 p-4" data-testid={`admin-blog-row-${p.slug}`}>
              <div className="w-16 h-12 bg-[#f0efed] overflow-hidden shrink-0">
                {p.cover_image && <img src={p.cover_image} alt="" className="w-full h-full object-cover" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{p.title}</p>
                <p className="text-stone text-xs">{new Date(p.created_at).toLocaleDateString(lang)} · {p.published ? t.admin.published : "—"}</p>
              </div>
              <button onClick={() => openEdit(p.id)} className="text-stone hover:text-brand transition-colors" data-testid={`blog-edit-${p.slug}`}>
                <Edit className="w-4 h-4" />
              </button>
              <button onClick={() => remove(p.id, p.title)} className="text-stone hover:text-red-500 transition-colors" data-testid={`blog-delete-${p.slug}`}>
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {editing && (
        <BlogEditor
          post={editing === "new" ? null : editing}
          onSaved={() => { setEditing(null); load(); }}
          onCancel={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function MessagesTab() {
  const { t, lang } = useI18n();
  const [items, setItems] = useState([]);

  useEffect(() => { api.get("/admin/contacts").then((r) => setItems(r.data.items)).catch(() => {}); }, []);

  return (
    <div data-testid="admin-messages-tab">
      {items.length === 0 ? (
        <p className="text-stone py-16 text-center" data-testid="admin-messages-empty">{t.admin.noMessages}</p>
      ) : (
        <div className="space-y-4">
          {items.map((m) => (
            <div key={m.id} className="border border-ink/10 p-5" data-testid={`admin-message-${m.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-display font-bold text-lg">{m.subject || "—"}</p>
                  <p className="text-sm text-stone flex items-center gap-2 mt-1">
                    <Mail className="w-3.5 h-3.5" /> {m.name} · {m.email}
                  </p>
                </div>
                <span className="text-xs text-stone shrink-0">{new Date(m.created_at).toLocaleDateString(lang)}</span>
              </div>
              <p className="mt-3 text-ink/80 whitespace-pre-wrap">{m.message}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const EMPTY_PROMO = { code: "", type: "percent", value: "", min_subtotal: "0", active: true };

function PromosTab() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(EMPTY_PROMO);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/admin/promos").then((r) => setItems(r.data.items)).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    if (!form.code.trim() || !form.value) return toast.error(t.admin.promoCode);
    setSaving(true);
    try {
      await api.post("/admin/promos", {
        code: form.code,
        type: form.type,
        value: Number(form.value),
        min_subtotal: Number(form.min_subtotal) || 0,
        active: form.active,
      });
      toast.success("OK");
      setForm(EMPTY_PROMO);
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (code) => {
    if (!window.confirm(`${t.admin.delete} ${code} ?`)) return;
    await api.delete(`/admin/promos/${code}`);
    toast.success("OK");
    load();
  };

  return (
    <div data-testid="admin-promos-tab">
      <form onSubmit={save} className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end bg-surface p-6 mb-8">
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.promoCode}</label>
          <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none focus:border-ink uppercase" data-testid="promo-code-input" />
        </div>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.promoType}</label>
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="promo-type-input">
            <option value="percent">{t.admin.percent}</option>
            <option value="fixed">{t.admin.fixed}</option>
          </select>
        </div>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.promoValue}</label>
          <input type="number" step="any" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="promo-value-input" />
        </div>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.promoMin}</label>
          <input type="number" step="any" value={form.min_subtotal} onChange={(e) => setForm({ ...form, min_subtotal: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="promo-min-input" />
        </div>
        <button type="submit" disabled={saving} className="inline-flex items-center justify-center gap-2 bg-brand text-white px-5 py-2.5 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="promo-add-btn">
          <Plus className="w-4 h-4" /> {t.admin.addPromo}
        </button>
      </form>

      {items.length === 0 ? (
        <p className="text-stone py-12 text-center" data-testid="admin-promos-empty">{t.admin.noPromos}</p>
      ) : (
        <div className="border border-ink/10 divide-y divide-ink/10">
          {items.map((p) => (
            <div key={p.code} className="flex items-center gap-4 p-4" data-testid={`promo-row-${p.code}`}>
              <Tag className="w-4 h-4 text-brand shrink-0" />
              <span className="font-display font-bold tracking-wide">{p.code}</span>
              <span className="text-sm text-stone">
                {p.type === "percent" ? `−${p.value}%` : `−${p.value}€`}
                {p.min_subtotal > 0 ? ` · min ${p.min_subtotal}€` : ""}
              </span>
              <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ml-auto ${p.active ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-500"}`}>
                {p.active ? t.admin.promoActive : "—"}
              </span>
              <button onClick={() => remove(p.code)} className="text-stone hover:text-red-500 transition-colors" data-testid={`promo-delete-${p.code}`}>
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SettingsTab() {
  const { t } = useI18n();
  const [s, setS] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get("/settings").then((r) => setS(r.data)).catch(() => {}); }, []);

  if (!s) return <p className="text-stone py-12 text-center">{t.common.loading}</p>;

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/admin/settings", {
        banner_enabled: s.banner_enabled,
        banner_text: s.banner_text,
        banner_text_en: s.banner_text_en,
        whatsapp_number: s.whatsapp_number,
        whatsapp_enabled: s.whatsapp_enabled,
        company_name: s.company_name,
        company_legal_form: s.company_legal_form,
        siren: s.siren,
        siret: s.siret,
        vat_number: s.vat_number,
        company_address: s.company_address,
        vat_regime: s.vat_regime,
        vat_rate: Number(s.vat_rate) || 0,
        ad_spend_30d: Number(s.ad_spend_30d) || 0,
        discord_webhook_url: s.discord_webhook_url || "",
        slack_webhook_url: s.slack_webhook_url || "",
        notify_new_order: !!s.notify_new_order,
      });
      toast.success(t.admin.settingsSaved);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const exportEreporting = async () => {
    try {
      const res = await api.get("/admin/ereporting?format=csv&days=90", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `ereporting-B2C-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  return (
    <div className="max-w-2xl space-y-8" data-testid="admin-settings-tab">
      <div className="border border-ink/10 p-6 space-y-4">
        <label className="flex items-center gap-3 font-medium">
          <input type="checkbox" checked={s.banner_enabled} onChange={(e) => setS({ ...s, banner_enabled: e.target.checked })} className="accent-brand w-4 h-4" data-testid="settings-banner-enabled" />
          {t.admin.bannerEnabled}
        </label>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.bannerText}</label>
          <input value={s.banner_text} onChange={(e) => setS({ ...s, banner_text: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-banner-text" />
        </div>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.bannerTextEn}</label>
          <input value={s.banner_text_en} onChange={(e) => setS({ ...s, banner_text_en: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-banner-text-en" />
        </div>
      </div>

      <div className="border border-ink/10 p-6 space-y-4">
        <p className="font-display font-bold text-lg">Marketing & rentabilité</p>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Dépenses publicitaires — 30 derniers jours (€)</label>
          <input type="number" step="any" value={s.ad_spend_30d ?? 0} onChange={(e) => setS({ ...s, ad_spend_30d: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-ad-spend" />
          <p className="text-stone text-xs mt-1">Utilisé pour calculer le ROAS, le ROI et le bénéfice net dans Analytics.</p>
        </div>
      </div>

      <div className="border border-ink/10 p-6 space-y-4">
        <p className="font-display font-bold text-lg">Notifications multi-canal</p>
        <label className="flex items-center gap-3 font-medium">
          <input type="checkbox" checked={!!s.notify_new_order} onChange={(e) => setS({ ...s, notify_new_order: e.target.checked })} className="accent-brand w-4 h-4" data-testid="settings-notify-new-order" />
          M'alerter à chaque nouvelle commande payée
        </label>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Webhook Discord (URL)</label>
          <input value={s.discord_webhook_url || ""} onChange={(e) => setS({ ...s, discord_webhook_url: e.target.value })} placeholder="https://discord.com/api/webhooks/..." className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-discord" />
        </div>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Webhook Slack (URL)</label>
          <input value={s.slack_webhook_url || ""} onChange={(e) => setS({ ...s, slack_webhook_url: e.target.value })} placeholder="https://hooks.slack.com/services/..." className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-slack" />
        </div>
        <button type="button" onClick={async () => { try { await api.post("/admin/notifications/test", { discord_webhook_url: s.discord_webhook_url, slack_webhook_url: s.slack_webhook_url }); toast.success("Notification de test envoyée"); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } }} className="border border-ink/20 px-5 py-2.5 rounded-full text-sm font-medium hover:border-ink transition-colors" data-testid="settings-notify-test">Envoyer un test</button>
        <p className="text-stone text-xs">SMS & WhatsApp (via Twilio) : disponibles prochainement — nécessitent vos identifiants Twilio.</p>
      </div>

      <div className="border border-ink/10 p-6 space-y-4">
        <label className="flex items-center gap-3 font-medium">
          <input type="checkbox" checked={s.whatsapp_enabled} onChange={(e) => setS({ ...s, whatsapp_enabled: e.target.checked })} className="accent-brand w-4 h-4" data-testid="settings-whatsapp-enabled" />
          {t.admin.whatsappEnabled}
        </label>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.whatsappNumber}</label>
          <input value={s.whatsapp_number} onChange={(e) => setS({ ...s, whatsapp_number: e.target.value })} placeholder="33612345678" className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-whatsapp-number" />
        </div>
      </div>

      <div className="border border-ink/10 p-6 space-y-4" data-testid="settings-legal">
        <p className="font-display font-bold text-lg">{t.admin.legalTitle}</p>
        <p className="text-stone text-sm -mt-2">{t.admin.legalHelp}</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SIn label={t.admin.companyName} v={s.company_name} on={(v) => setS({ ...s, company_name: v })} tid="settings-company-name" />
          <SIn label={t.admin.legalForm} v={s.company_legal_form} on={(v) => setS({ ...s, company_legal_form: v })} tid="settings-legal-form" />
          <SIn label="SIREN" v={s.siren} on={(v) => setS({ ...s, siren: v })} tid="settings-siren" />
          <SIn label="SIRET" v={s.siret} on={(v) => setS({ ...s, siret: v })} tid="settings-siret" />
          <SIn label={t.admin.vatNumber} v={s.vat_number} on={(v) => setS({ ...s, vat_number: v })} tid="settings-vat-number" />
          <SIn label={t.admin.companyAddress} v={s.company_address} on={(v) => setS({ ...s, company_address: v })} tid="settings-company-address" />
          <div>
            <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.vatRegime}</label>
            <select value={s.vat_regime} onChange={(e) => setS({ ...s, vat_regime: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-vat-regime">
              <option value="franchise">{t.admin.regimeFranchise}</option>
              <option value="assujetti">{t.admin.regimeAssujetti}</option>
            </select>
          </div>
          {s.vat_regime === "assujetti" && (
            <SIn label={t.admin.vatRate} v={s.vat_rate} on={(v) => setS({ ...s, vat_rate: v })} tid="settings-vat-rate" type="number" />
          )}
        </div>
        <button onClick={exportEreporting} className="inline-flex items-center gap-2 mt-2 border border-ink/20 px-5 py-2.5 rounded-full text-sm font-medium hover:border-ink transition-colors" data-testid="ereporting-export-btn">
          <Download className="w-4 h-4" /> {t.admin.ereportingExport}
        </button>
      </div>

      <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-brand text-white px-8 py-3.5 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="settings-save-btn">
        <Settings className="w-4 h-4" /> {saving ? t.common.loading : t.admin.saveSettings}
      </button>
    </div>
  );
}

function SIn({ label, v, on, tid, type = "text" }) {
  return (
    <div>
      <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{label}</label>
      <input type={type} value={v || ""} onChange={(e) => on(e.target.value)} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid={tid} />
    </div>
  );
}


function AnalyticsTab() {
  const { t } = useI18n();
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/admin/analytics").then((r) => setD(r.data)).catch(() => {}); }, []);
  if (!d) return <p className="text-stone py-12 text-center">{t.common.loading}</p>;

  const kpis = [
    { key: "revenue", label: t.admin.kpiRevenue, value: `${d.revenue.toFixed(2)}€` },
    { key: "paid-orders", label: t.admin.kpiOrders, value: d.paid_orders },
    { key: "aov", label: t.admin.kpiAov, value: `${d.aov.toFixed(2)}€` },
    { key: "conversion", label: t.admin.kpiConversion, value: `${d.conversion_rate}%` },
    { key: "visits", label: t.admin.kpiVisits, value: d.visits_30d },
    { key: "customers", label: t.admin.kpiCustomers, value: d.total_customers },
  ];

  return (
    <div data-testid="admin-analytics-tab">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
        {kpis.map((k) => (
          <div key={k.key} className="bg-surface p-5" data-testid={`kpi-${k.key}`}>
            <p className="text-xs tracking-[0.12em] uppercase font-bold text-stone">{k.label}</p>
            <p className="font-display font-black text-2xl mt-2">{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
        {[
          { key: "gross-profit", label: "Bénéfice brut", value: `${(d.gross_profit ?? 0).toFixed(2)}€`, accent: true },
          { key: "revenue-30d", label: "CA (30j)", value: `${(d.revenue_30d ?? 0).toFixed(2)}€` },
          { key: "net-profit", label: "Bénéfice net (30j)", value: `${(d.net_profit_30d ?? 0).toFixed(2)}€`, accent: true },
          { key: "ad-spend", label: "Dépenses pub (30j)", value: `${(d.ad_spend_30d ?? 0).toFixed(2)}€` },
          { key: "roas", label: "ROAS", value: `${d.roas ?? 0}x` },
          { key: "roi", label: "ROI", value: `${d.roi ?? 0}%` },
        ].map((k) => (
          <div key={k.key} className={`p-5 ${k.accent ? "bg-ink text-cream" : "bg-surface"}`} data-testid={`kpi-${k.key}`}>
            <p className={`text-xs tracking-[0.12em] uppercase font-bold ${k.accent ? "text-cream/70" : "text-stone"}`}>{k.label}</p>
            <p className="font-display font-black text-2xl mt-2">{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
        {[
          { key: "to-ship", label: "Commandes à expédier", value: d.to_ship ?? 0, warn: (d.to_ship ?? 0) > 0 },
          { key: "out-of-stock", label: "Produits en rupture", value: d.out_of_stock ?? 0, warn: (d.out_of_stock ?? 0) > 0 },
          { key: "low-stock", label: "Stock faible", value: d.low_stock ?? 0, warn: (d.low_stock ?? 0) > 0 },
          { key: "alerts", label: "Alertes actives", value: d.unresolved_alerts ?? 0, warn: (d.unresolved_alerts ?? 0) > 0 },
        ].map((k) => (
          <div key={k.key} className={`border p-4 text-center ${k.warn ? "border-brand bg-brand/5" : "border-ink/10"}`} data-testid={`ops-${k.key}`}>
            <p className={`font-display font-black text-2xl ${k.warn ? "text-brand" : ""}`}>{k.value}</p>
            <p className="text-xs text-stone uppercase tracking-wide mt-1">{k.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 border border-ink/10 p-5">
          <p className="font-display font-bold text-lg mb-4">{t.admin.chartRevenue}</p>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={d.revenue_series} margin={{ left: -18, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ff3300" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#ff3300" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e2dd" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} interval={4} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Area type="monotone" dataKey="revenue" stroke="#ff3300" strokeWidth={2} fill="url(#rev)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-ink/10 p-5">
          <p className="font-display font-bold text-lg mb-4">{t.admin.chartTop}</p>
          {d.top_products.length === 0 ? (
            <p className="text-stone text-sm">—</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={d.top_products} layout="vertical" margin={{ left: 10, right: 10 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="title" tick={{ fontSize: 9 }} width={90} tickFormatter={(v) => (v || "").slice(0, 14)} />
                <Tooltip />
                <Bar dataKey="qty" fill="#ff3300" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-8">
        {Object.entries(d.status_breakdown).map(([s, n]) => (
          <div key={s} className="border border-ink/10 p-4 text-center">
            <p className="font-display font-black text-xl">{n}</p>
            <p className="text-xs text-stone uppercase tracking-wide">{s}</p>
          </div>
        ))}
      </div>

      {d.revenue_monthly && (
        <div className="border border-ink/10 p-5 mt-8" data-testid="chart-monthly">
          <p className="font-display font-bold text-lg mb-4">Chiffre d'affaires par mois (12 mois)</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={d.revenue_monthly} margin={{ left: -12, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e2dd" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(2)} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="revenue" fill="#ff3300" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

const EMPTY_SUPPLIER = { name: "", contact_email: "", contact_phone: "", website: "", country: "", avg_delay_days: "", quality_rating: "", shipping_cost: "", notes: "" };

function SuppliersTab() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(EMPTY_SUPPLIER);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const load = () => api.get("/admin/suppliers").then((r) => setItems(r.data.items)).catch(() => {});
  useEffect(() => { load(); }, []);

  const num = (v) => (v === "" || v === null ? 0 : Number(v));
  const save = async (e) => {
    e.preventDefault();
    if (!form.name) { toast.error("Nom requis"); return; }
    setSaving(true);
    const payload = { ...form, avg_delay_days: num(form.avg_delay_days), quality_rating: num(form.quality_rating), shipping_cost: num(form.shipping_cost) };
    try {
      if (editing) await api.put(`/admin/suppliers/${editing}`, payload);
      else await api.post("/admin/suppliers", payload);
      toast.success("Fournisseur enregistré");
      setForm(EMPTY_SUPPLIER); setEditing(null); load();
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
    finally { setSaving(false); }
  };
  const edit = (s) => { setEditing(s.id); setForm({ ...EMPTY_SUPPLIER, ...s }); };
  const del = async (id) => { await api.delete(`/admin/suppliers/${id}`); load(); toast.success("Supprimé"); };

  const sorted = [...items].sort((a, b) => (b.score || 0) - (a.score || 0));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8" data-testid="admin-suppliers-tab">
      <form onSubmit={save} className="space-y-3 border border-ink/10 p-5 h-fit">
        <p className="font-display font-bold text-lg mb-2">{editing ? "Modifier le fournisseur" : "Nouveau fournisseur"}</p>
        <In label="Nom" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
        <In label="Email" value={form.contact_email} onChange={(v) => setForm({ ...form, contact_email: v })} />
        <In label="Téléphone" value={form.contact_phone} onChange={(v) => setForm({ ...form, contact_phone: v })} />
        <In label="Site web" value={form.website} onChange={(v) => setForm({ ...form, website: v })} />
        <In label="Pays" value={form.country} onChange={(v) => setForm({ ...form, country: v })} />
        <In label="Délai moyen (jours)" type="number" value={form.avg_delay_days} onChange={(v) => setForm({ ...form, avg_delay_days: v })} />
        <In label="Qualité (0-5)" type="number" value={form.quality_rating} onChange={(v) => setForm({ ...form, quality_rating: v })} />
        <In label="Frais de port (€)" type="number" value={form.shipping_cost} onChange={(v) => setForm({ ...form, shipping_cost: v })} />
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">Notes</label>
          <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="supplier-notes" />
        </div>
        <button type="submit" disabled={saving} className="w-full bg-ink text-cream py-3 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="supplier-save-btn">{saving ? "…" : "Enregistrer"}</button>
        {editing && <button type="button" onClick={() => { setEditing(null); setForm(EMPTY_SUPPLIER); }} className="w-full border border-ink/20 py-2.5 rounded-full text-sm">Annuler</button>}
      </form>

      <div className="lg:col-span-2">
        <p className="font-display font-bold text-lg mb-4">Comparateur de fournisseurs (par score)</p>
        {sorted.length === 0 && <p className="text-stone">Aucun fournisseur. Ajoutez-en un.</p>}
        <div className="space-y-3">
          {sorted.map((s, i) => (
            <div key={s.id} className="border border-ink/10 p-4 flex flex-wrap items-center gap-4" data-testid={`supplier-${s.id}`}>
              <span className="font-display font-black text-2xl w-8 text-stone">{i + 1}</span>
              <div className="flex-1 min-w-[150px]">
                <p className="font-medium">{s.name} {s.country && <span className="text-stone text-sm">· {s.country}</span>}</p>
                <p className="text-stone text-sm">Délai {s.avg_delay_days || 0}j · Qualité {s.quality_rating || 0}/5 · Port {(s.shipping_cost || 0)}€ · {s.product_count || 0} produits</p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase text-stone font-bold">Score</p>
                <p className="font-display font-black text-2xl text-brand" data-testid={`supplier-score-${s.id}`}>{s.score}</p>
              </div>
              <button onClick={() => edit(s)} className="text-sm text-stone hover:text-ink px-2" data-testid={`supplier-edit-${s.id}`}>Modifier</button>
              <button onClick={() => del(s.id)} className="text-brand hover:opacity-70 p-2" data-testid={`supplier-delete-${s.id}`}><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const EMPTY_RULE = { name: "", active: true, cond_type: "out_of_stock", cond_value: "", action_type: "alert", action_value: "" };
const COND_LABELS = { out_of_stock: "En rupture de stock", low_stock: "Stock ≤ seuil", low_margin: "Marge < seuil %" };
const ACTION_LABELS = { alert: "Créer une alerte", hide: "Masquer le produit", set_margin: "Ajuster le prix (marge cible %)" };

function RulesTab() {
  const [rules, setRules] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [form, setForm] = useState(EMPTY_RULE);
  const [busy, setBusy] = useState(false);
  const loadRules = () => api.get("/admin/rules").then((r) => setRules(r.data.items)).catch(() => {});
  const loadAlerts = () => api.get("/admin/alerts").then((r) => setAlerts(r.data.items)).catch(() => {});
  useEffect(() => { loadRules(); loadAlerts(); }, []);

  const save = async (e) => {
    e.preventDefault();
    if (!form.name) { toast.error("Nom requis"); return; }
    try {
      await api.post("/admin/rules", { ...form, cond_value: Number(form.cond_value) || 0, action_value: Number(form.action_value) || 0 });
      toast.success("Règle créée"); setForm(EMPTY_RULE); loadRules();
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };
  const toggle = async (r) => { await api.put(`/admin/rules/${r.id}`, { ...r, active: !r.active }); loadRules(); };
  const del = async (id) => { await api.delete(`/admin/rules/${id}`); loadRules(); };
  const run = async () => {
    setBusy(true);
    try {
      const r = await api.post("/admin/rules/run");
      toast.success(`Règles exécutées : ${r.data.matches} correspondances · ${r.data.alerts} alertes · ${r.data.hidden} masqués · ${r.data.repriced} reprix`);
      loadAlerts();
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const resolve = async (id) => { await api.put(`/admin/alerts/${id}/resolve`); loadAlerts(); };
  const clearAll = async () => { await api.post("/admin/alerts/clear"); loadAlerts(); };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8" data-testid="admin-rules-tab">
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="font-display font-bold text-lg">Moteur de règles (no-code)</p>
          <button onClick={run} disabled={busy} className="inline-flex items-center gap-2 bg-ink text-cream px-4 py-2 rounded-full text-sm font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="rules-run-btn">
            {busy ? "…" : "Exécuter maintenant"}
          </button>
        </div>
        <form onSubmit={save} className="border border-ink/10 p-5 space-y-3 mb-6">
          <In label="Nom de la règle" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs uppercase font-bold text-stone mb-2 block">SI (condition)</label>
              <select value={form.cond_type} onChange={(e) => setForm({ ...form, cond_type: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none" data-testid="rule-cond-type">
                {Object.entries(COND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            {form.cond_type !== "out_of_stock" && <In label="Seuil" type="number" value={form.cond_value} onChange={(v) => setForm({ ...form, cond_value: v })} />}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs uppercase font-bold text-stone mb-2 block">ALORS (action)</label>
              <select value={form.action_type} onChange={(e) => setForm({ ...form, action_type: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none" data-testid="rule-action-type">
                {Object.entries(ACTION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            {form.action_type === "set_margin" && <In label="Marge cible (%)" type="number" value={form.action_value} onChange={(v) => setForm({ ...form, action_value: v })} />}
          </div>
          <button type="submit" className="w-full bg-brand text-white py-3 rounded-full font-medium hover:bg-ink transition-colors" data-testid="rule-save-btn">Ajouter la règle</button>
        </form>
        <div className="space-y-2">
          {rules.length === 0 && <p className="text-stone text-sm">Aucune règle définie.</p>}
          {rules.map((r) => (
            <div key={r.id} className="border border-ink/10 p-3 flex items-center gap-3" data-testid={`rule-${r.id}`}>
              <button onClick={() => toggle(r)} className={`w-10 h-6 rounded-full transition-colors ${r.active ? "bg-brand" : "bg-ink/20"}`} data-testid={`rule-toggle-${r.id}`}>
                <span className={`block w-5 h-5 bg-white rounded-full transition-transform ${r.active ? "translate-x-4" : "translate-x-0.5"}`} />
              </button>
              <div className="flex-1">
                <p className="font-medium text-sm">{r.name}</p>
                <p className="text-stone text-xs">{COND_LABELS[r.cond_type]}{r.cond_type !== "out_of_stock" ? ` (${r.cond_value})` : ""} → {ACTION_LABELS[r.action_type]}{r.action_type === "set_margin" ? ` (${r.action_value}%)` : ""}</p>
              </div>
              <button onClick={() => del(r.id)} className="text-brand hover:opacity-70 p-1" data-testid={`rule-delete-${r.id}`}><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="font-display font-bold text-lg">Alertes ({alerts.length})</p>
          {alerts.length > 0 && <button onClick={clearAll} className="text-sm text-stone hover:text-ink" data-testid="alerts-clear-btn">Tout marquer résolu</button>}
        </div>
        {alerts.length === 0 && <p className="text-stone text-sm">Aucune alerte active. 🎉</p>}
        <div className="space-y-2">
          {alerts.map((a) => (
            <div key={a.id} className="border border-brand/30 bg-brand/5 p-3 flex items-start gap-3" data-testid={`alert-${a.id}`}>
              <span className="text-brand text-lg leading-none">•</span>
              <div className="flex-1">
                <p className="text-sm">{a.message}</p>
                <p className="text-stone text-xs mt-0.5">{new Date(a.created_at).toLocaleString()}</p>
              </div>
              <button onClick={() => resolve(a.id)} className="text-xs border border-ink/20 rounded-full px-3 py-1 hover:border-ink" data-testid={`alert-resolve-${a.id}`}>Résoudre</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const MARKETING_SUBTABS = [
  { key: "crm", label: "Clients (CRM)", icon: Users },
  { key: "abandoned", label: "Paniers abandonnés", icon: ShoppingCart },
  { key: "campaigns", label: "Campagnes email", icon: Mail },
  { key: "bundles", label: "Packs / Bundles", icon: Gift },
  { key: "flash", label: "Ventes flash", icon: Zap },
];

function MarketingTab() {
  const [sub, setSub] = useState("crm");
  return (
    <div data-testid="admin-marketing-tab">
      <div className="flex flex-wrap gap-2 mb-8">
        {MARKETING_SUBTABS.map((s) => (
          <button key={s.key} onClick={() => setSub(s.key)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium border transition-colors ${sub === s.key ? "bg-ink text-cream border-ink" : "border-ink/20 text-stone hover:border-ink"}`}
            data-testid={`marketing-subtab-${s.key}`}>
            <s.icon className="w-4 h-4" /> {s.label}
          </button>
        ))}
      </div>
      {sub === "crm" && <CrmPanel />}
      {sub === "abandoned" && <AbandonedPanel />}
      {sub === "campaigns" && <CampaignsPanel />}
      {sub === "bundles" && <BundlesPanel />}
      {sub === "flash" && <FlashPanel />}
    </div>
  );
}

function CampaignsPanel() {
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [form, setForm] = useState({ subject: "", body_html: "", segment: "newsletter" });
  const [sending, setSending] = useState(false);
  const load = () => { api.get("/admin/campaigns").then((r) => setItems(r.data.items)).catch(() => {}); api.get("/admin/segments/count").then((r) => setCounts(r.data)).catch(() => {}); };
  useEffect(() => { load(); }, []);
  const send = async (e) => {
    e.preventDefault();
    if (!form.subject || !form.body_html) { toast.error("Sujet et contenu requis"); return; }
    setSending(true);
    try { const r = await api.post("/admin/campaigns", form); toast.success(`Campagne créée → ${r.data.recipients} destinataire(s)`); setForm({ subject: "", body_html: "", segment: "newsletter" }); setTimeout(load, 1500); }
    catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
    finally { setSending(false); }
  };
  const segLabel = { newsletter: "Abonnés newsletter", customers: "Tous les clients", vip: "Clients VIP", all: "Tout le monde" };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8" data-testid="campaigns-panel">
      <form onSubmit={send} className="space-y-3 border border-ink/10 p-5 h-fit">
        <p className="font-display font-bold text-lg mb-2">Nouvelle campagne</p>
        <In label="Sujet" value={form.subject} onChange={(v) => setForm({ ...form, subject: v })} />
        <div>
          <label className="text-xs uppercase font-bold text-stone mb-2 block">Segment</label>
          <select value={form.segment} onChange={(e) => setForm({ ...form, segment: e.target.value })} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" data-testid="campaign-segment">
            {Object.entries(segLabel).map(([k, l]) => <option key={k} value={k}>{l} ({counts[k] ?? "…"})</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs uppercase font-bold text-stone mb-2 block">Contenu (HTML autorisé)</label>
          <textarea value={form.body_html} onChange={(e) => setForm({ ...form, body_html: e.target.value })} rows={6} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none" placeholder="<h2>Nos nouveautés...</h2><p>...</p>" data-testid="campaign-body" />
        </div>
        <button type="submit" disabled={sending} className="w-full bg-brand text-white py-3 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="campaign-send-btn">{sending ? "Envoi…" : "Envoyer la campagne"}</button>
      </form>
      <div>
        <p className="font-display font-bold text-lg mb-4">Historique</p>
        {items.length === 0 && <p className="text-stone text-sm">Aucune campagne.</p>}
        <div className="space-y-2">
          {items.map((c) => (
            <div key={c.id} className="border border-ink/10 p-4" data-testid={`campaign-${c.id}`}>
              <div className="flex items-center justify-between">
                <p className="font-medium">{c.subject}</p>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${c.status === "sent" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{c.status}</span>
              </div>
              <p className="text-stone text-sm mt-1">{segLabel[c.segment]} · {c.sent}/{c.recipients} envoyés · {new Date(c.created_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const EMPTY_BUNDLE = { title: "", description: "", product_ids: [], bundle_price: "", image: "" };
function BundlesPanel() {
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(EMPTY_BUNDLE);
  const load = () => api.get("/admin/bundles").then((r) => setItems(r.data.items)).catch(() => {});
  useEffect(() => { load(); api.get("/products?size=200").then((r) => setProducts(r.data.items)).catch(() => {}); }, []);
  const toggleProduct = (id) => setForm((f) => ({ ...f, product_ids: f.product_ids.includes(id) ? f.product_ids.filter((x) => x !== id) : [...f.product_ids, id] }));
  const save = async (e) => {
    e.preventDefault();
    if (!form.title || !form.product_ids.length || !form.bundle_price) { toast.error("Titre, produits et prix requis"); return; }
    try { await api.post("/admin/bundles", { ...form, bundle_price: parseFloat(form.bundle_price) }); toast.success("Pack créé"); setForm(EMPTY_BUNDLE); load(); }
    catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };
  const del = async (id) => { await api.delete(`/admin/bundles/${id}`); load(); };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8" data-testid="bundles-panel">
      <form onSubmit={save} className="space-y-3 border border-ink/10 p-5 h-fit">
        <p className="font-display font-bold text-lg mb-2">Nouveau pack</p>
        <In label="Titre" value={form.title} onChange={(v) => setForm({ ...form, title: v })} />
        <In label="Prix du pack (€)" type="number" value={form.bundle_price} onChange={(v) => setForm({ ...form, bundle_price: v })} />
        <In label="Image (URL, optionnel)" value={form.image} onChange={(v) => setForm({ ...form, image: v })} />
        <div>
          <label className="text-xs uppercase font-bold text-stone mb-2 block">Produits inclus ({form.product_ids.length})</label>
          <div className="max-h-56 overflow-auto border border-ink/10 divide-y divide-ink/10">
            {products.map((p) => (
              <label key={p.id} className="flex items-center gap-2 p-2 text-sm cursor-pointer hover:bg-surface">
                <input type="checkbox" checked={form.product_ids.includes(p.id)} onChange={() => toggleProduct(p.id)} className="accent-brand" data-testid={`bundle-prod-${p.id}`} />
                <span className="truncate flex-1">{p.title}</span><span className="text-stone">{p.price.toFixed(2)}€</span>
              </label>
            ))}
          </div>
        </div>
        <button type="submit" className="w-full bg-brand text-white py-3 rounded-full font-medium hover:bg-ink transition-colors" data-testid="bundle-save-btn">Créer le pack</button>
      </form>
      <div className="space-y-3">
        <p className="font-display font-bold text-lg mb-1">Packs ({items.length})</p>
        {items.length === 0 && <p className="text-stone text-sm">Aucun pack.</p>}
        {items.map((b) => (
          <div key={b.id} className="border border-ink/10 p-4 flex items-center gap-4" data-testid={`bundle-${b.id}`}>
            {b.image && <img src={b.image} alt="" className="w-14 h-16 object-cover bg-surface" />}
            <div className="flex-1">
              <p className="font-medium">{b.title}</p>
              <p className="text-stone text-sm">{b.products.length} produits · <span className="line-through">{b.normal_price.toFixed(2)}€</span> → <strong className="text-brand">{b.bundle_price.toFixed(2)}€</strong> (-{b.savings_pct}%)</p>
            </div>
            <button onClick={() => del(b.id)} className="text-brand hover:opacity-70 p-2" data-testid={`bundle-delete-${b.id}`}><Trash2 className="w-4 h-4" /></button>
          </div>
        ))}
      </div>
    </div>
  );
}

const EMPTY_FLASH = { title: "", scope: "category", target: "smart-home", discount_percent: "15", ends_at: "", active: true };
function FlashPanel() {
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(EMPTY_FLASH);
  const load = () => api.get("/admin/flash-sales").then((r) => setItems(r.data.items)).catch(() => {});
  useEffect(() => { load(); api.get("/products?size=200").then((r) => setProducts(r.data.items)).catch(() => {}); }, []);
  const save = async (e) => {
    e.preventDefault();
    if (!form.title || !form.ends_at) { toast.error("Titre et date de fin requis"); return; }
    try {
      await api.post("/admin/flash-sales", { ...form, discount_percent: parseFloat(form.discount_percent) || 0, ends_at: new Date(form.ends_at).toISOString() });
      toast.success("Vente flash créée"); setForm(EMPTY_FLASH); load();
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };
  const del = async (id) => { await api.delete(`/admin/flash-sales/${id}`); load(); };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8" data-testid="flash-panel">
      <form onSubmit={save} className="space-y-3 border border-ink/10 p-5 h-fit">
        <p className="font-display font-bold text-lg mb-2">Nouvelle vente flash</p>
        <In label="Titre" value={form.title} onChange={(v) => setForm({ ...form, title: v })} />
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs uppercase font-bold text-stone mb-2 block">Portée</label>
            <select value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none" data-testid="flash-scope">
              <option value="category">Catégorie</option>
              <option value="product">Produit</option>
              <option value="all">Toute la boutique</option>
            </select>
          </div>
          <In label="Réduction (%)" type="number" value={form.discount_percent} onChange={(v) => setForm({ ...form, discount_percent: v })} />
        </div>
        {form.scope === "category" && (
          <div>
            <label className="text-xs uppercase font-bold text-stone mb-2 block">Catégorie</label>
            <select value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none" data-testid="flash-target-cat">
              <option value="smart-home">smart-home</option><option value="workspace">workspace</option><option value="security">security</option>
            </select>
          </div>
        )}
        {form.scope === "product" && (
          <div>
            <label className="text-xs uppercase font-bold text-stone mb-2 block">Produit</label>
            <select value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} className="w-full px-3 py-2.5 border border-ink/20 bg-transparent outline-none" data-testid="flash-target-prod">
              <option value="">— Choisir —</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </div>
        )}
        <In label="Fin de la vente" type="datetime-local" value={form.ends_at} onChange={(v) => setForm({ ...form, ends_at: v })} />
        <button type="submit" className="w-full bg-brand text-white py-3 rounded-full font-medium hover:bg-ink transition-colors" data-testid="flash-save-btn">Lancer la vente flash</button>
      </form>
      <div className="space-y-3">
        <p className="font-display font-bold text-lg mb-1">Ventes flash ({items.length})</p>
        {items.length === 0 && <p className="text-stone text-sm">Aucune vente flash.</p>}
        {items.map((s) => (
          <div key={s.id} className="border border-ink/10 p-4 flex items-center gap-4" data-testid={`flash-${s.id}`}>
            <Zap className={`w-5 h-5 ${s.is_active ? "text-brand" : "text-stone"}`} />
            <div className="flex-1">
              <p className="font-medium">{s.title} <span className="text-brand font-bold">-{s.discount_percent}%</span></p>
              <p className="text-stone text-sm">{s.scope === "all" ? "Toute la boutique" : `${s.scope}: ${s.target}`} · fin {new Date(s.ends_at).toLocaleString()} {s.is_active ? "· 🟢 active" : "· ⚪ inactive"}</p>
            </div>
            <button onClick={() => del(s.id)} className="text-brand hover:opacity-70 p-2" data-testid={`flash-delete-${s.id}`}><Trash2 className="w-4 h-4" /></button>
          </div>
        ))}
      </div>
    </div>
  );
}

function CrmPanel() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [segment, setSegment] = useState("");
  const [detail, setDetail] = useState(null);
  const load = () => api.get(`/admin/customers?q=${encodeURIComponent(q)}&segment=${segment}`).then((r) => setItems(r.data.items)).catch(() => {});
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [segment]);
  const openDetail = async (id) => {
    try { const r = await api.get(`/admin/customers/${id}`); setDetail(r.data); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const tierColor = (t) => t === "Platine" ? "bg-slate-800 text-white" : t === "Or" ? "bg-amber-100 text-amber-700" : t === "Argent" ? "bg-gray-200 text-gray-700" : "bg-orange-50 text-orange-700";
  const segments = [{ k: "", l: "Tous" }, { k: "vip", l: "VIP" }, { k: "active", l: "Actifs" }, { k: "new", l: "Nouveaux" }];

  return (
    <div data-testid="crm-panel">
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-stone" />
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder="Rechercher un client…" className="w-full pl-11 pr-4 py-2.5 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="crm-search" />
        </div>
        <div className="flex gap-2">
          {segments.map((s) => (
            <button key={s.k} onClick={() => setSegment(s.k)} className={`px-4 py-2 rounded-full text-sm border transition-colors ${segment === s.k ? "bg-brand text-white border-brand" : "border-ink/20 hover:border-ink"}`} data-testid={`crm-segment-${s.k || "all"}`}>{s.l}</button>
          ))}
        </div>
      </div>

      <div className="border border-ink/10 divide-y divide-ink/10">
        {items.length === 0 && <p className="p-8 text-stone text-center">Aucun client.</p>}
        {items.map((c) => (
          <div key={c.id} className="flex flex-wrap items-center gap-4 p-4" data-testid={`crm-customer-${c.id}`}>
            <div className="flex-1 min-w-[180px]">
              <p className="font-medium">{c.name || c.email}</p>
              <p className="text-stone text-sm">{c.email}</p>
            </div>
            <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${tierColor(c.tier)}`}>{c.tier}</span>
            <span className={`text-xs uppercase font-bold px-2 py-1 rounded ${c.status === "VIP" ? "bg-brand/10 text-brand" : "bg-ink/5 text-stone"}`}>{c.status}</span>
            <div className="text-right w-28">
              <p className="font-display font-bold">{c.total_spent.toFixed(2)}€</p>
              <p className="text-stone text-xs">{c.orders_count} cmd · {c.loyalty_points} pts</p>
            </div>
            <button onClick={() => openDetail(c.id)} className="text-sm border border-ink/20 rounded-full px-4 py-1.5 hover:border-ink transition-colors" data-testid={`crm-view-${c.id}`}>Fiche</button>
          </div>
        ))}
      </div>

      {detail && (
        <div className="fixed inset-0 z-50 bg-ink/40 flex items-center justify-center p-4" onClick={() => setDetail(null)}>
          <div onClick={(e) => e.stopPropagation()} className="bg-cream w-full max-w-2xl p-8 max-h-[90vh] overflow-auto" data-testid="crm-detail-modal">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="font-display font-bold text-2xl">{detail.customer.name || detail.customer.email}</h3>
                <p className="text-stone">{detail.customer.email}</p>
              </div>
              <button onClick={() => setDetail(null)}><X className="w-6 h-6" /></button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {[["Dépensé", `${detail.customer.total_spent.toFixed(2)}€`], ["Commandes", detail.customer.orders_count], ["Panier moyen", `${detail.customer.aov.toFixed(2)}€`], ["Points fidélité", detail.customer.loyalty_points]].map(([l, v]) => (
                <div key={l} className="bg-surface p-3"><p className="text-xs uppercase text-stone font-bold">{l}</p><p className="font-display font-black text-xl mt-1">{v}</p></div>
              ))}
            </div>
            <p className="font-bold uppercase text-xs tracking-wide text-stone mb-2">Historique commandes ({detail.orders.length})</p>
            <div className="space-y-2 mb-6">
              {detail.orders.slice(0, 20).map((o) => (
                <div key={o.id} className="flex items-center gap-3 text-sm border border-ink/10 p-3">
                  <span className="font-medium">#{o.id.slice(0, 8).toUpperCase()}</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${o.payment_status === "paid" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{o.payment_status}</span>
                  <span className="text-stone">{new Date(o.created_at).toLocaleDateString()}</span>
                  <span className="ml-auto font-display font-bold">{(o.total || 0).toFixed(2)}€</span>
                </div>
              ))}
            </div>
            {detail.returns.length > 0 && <p className="text-sm text-stone">{detail.returns.length} demande(s) de retour</p>}
          </div>
        </div>
      )}
    </div>
  );
}

function AbandonedPanel() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState("");
  const load = () => api.get("/admin/abandoned").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const remind = async (id) => {
    setBusy(id);
    try { await api.post(`/admin/abandoned/${id}/remind`); toast.success("Email de relance envoyé"); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };
  const runAll = async () => {
    setBusy("all");
    try { const r = await api.post("/admin/abandoned/run"); toast.success(`${r.data.sent} relance(s) envoyée(s) sur ${r.data.candidates} candidat(s)`); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };
  if (!data) return <p className="text-stone py-12 text-center">Chargement…</p>;

  return (
    <div data-testid="abandoned-panel">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          ["Paniers abandonnés", data.count],
          ["CA potentiel", `${data.potential_revenue.toFixed(2)}€`],
          ["Relancés", data.reminded],
          ["Récupérés", `${data.recovered} · ${data.recovered_revenue.toFixed(2)}€`],
        ].map(([l, v]) => (
          <div key={l} className="bg-surface p-5" data-testid={`abandoned-kpi-${l}`}><p className="text-xs uppercase text-stone font-bold">{l}</p><p className="font-display font-black text-2xl mt-1">{v}</p></div>
        ))}
      </div>
      <div className="flex justify-end mb-4">
        <button onClick={runAll} disabled={busy === "all"} className="inline-flex items-center gap-2 bg-ink text-cream px-5 py-2.5 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="abandoned-run-all">
          <Mail className="w-4 h-4" /> {busy === "all" ? "Envoi…" : "Relancer tout"}
        </button>
      </div>
      <div className="border border-ink/10 divide-y divide-ink/10">
        {data.items.length === 0 && <p className="p-8 text-stone text-center">Aucun panier abandonné. 🎉</p>}
        {data.items.map((o) => (
          <div key={o.id} className="flex flex-wrap items-center gap-4 p-4" data-testid={`abandoned-${o.id}`}>
            <div className="flex-1 min-w-[180px]">
              <p className="font-medium">#{o.id.slice(0, 8).toUpperCase()} · {(o.shipping_address?.email || o.user_email || "—")}</p>
              <p className="text-stone text-sm">{new Date(o.created_at).toLocaleString()} · {(o.items || []).length} article(s)</p>
            </div>
            <p className="font-display font-bold text-lg w-24 text-right">{(o.total || 0).toFixed(2)}€</p>
            {o.abandoned_email_sent && <span className="text-xs text-emerald-600 font-medium">✓ relancé</span>}
            <button onClick={() => remind(o.id)} disabled={busy === o.id} className="text-sm border border-ink/20 rounded-full px-4 py-1.5 hover:border-brand hover:text-brand transition-colors disabled:opacity-50" data-testid={`abandoned-remind-${o.id}`}>
              {busy === o.id ? "…" : "Relancer"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReturnsTab() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState("");
  const load = () => api.get("/admin/returns").then((r) => setItems(r.data.items)).catch(() => {});
  useEffect(() => { load(); }, []);

  const decide = async (id, action) => {
    const note = action === "reject" ? (window.prompt(t.admin.returnNote) || "") : "";
    setBusy(id);
    try {
      const r = await api.put(`/admin/returns/${id}`, { action, admin_note: note });
      toast.success(r.data.status + (r.data.refund?.refunded ? " · remboursé" : ""));
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const badge = { requested: "bg-amber-100 text-amber-700", approved: "bg-blue-100 text-blue-700", refunded: "bg-emerald-100 text-emerald-700", rejected: "bg-red-100 text-red-700" };

  return (
    <div data-testid="admin-returns-tab">
      {items.length === 0 ? (
        <p className="text-stone py-16 text-center" data-testid="admin-returns-empty">{t.admin.noReturns}</p>
      ) : (
        <div className="space-y-4">
          {items.map((r) => (
            <div key={r.id} className="border border-ink/10 p-5" data-testid={`return-row-${r.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-display font-bold">#{r.order_ref} · {r.amount?.toFixed(2)}€</p>
                  <p className="text-sm text-stone mt-1">{r.user_email} · {new Date(r.created_at).toLocaleDateString()}</p>
                  <p className="mt-2 text-ink/80">{r.reason}</p>
                  {r.admin_note && <p className="mt-1 text-xs text-stone">Note: {r.admin_note}</p>}
                </div>
                <span className={`text-xs font-bold uppercase px-2.5 py-1 rounded-full ${badge[r.status] || "bg-gray-100"}`}>{r.status}</span>
              </div>
              {r.status === "requested" && (
                <div className="flex gap-3 mt-4">
                  <button onClick={() => decide(r.id, "approve")} disabled={busy === r.id} className="px-4 py-2 bg-brand text-white text-sm rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid={`return-approve-${r.id}`}>
                    {t.admin.approveRefund}
                  </button>
                  <button onClick={() => decide(r.id, "reject")} disabled={busy === r.id} className="px-4 py-2 border border-ink/20 text-sm rounded-full font-medium hover:border-ink transition-colors disabled:opacity-50" data-testid={`return-reject-${r.id}`}>
                    {t.admin.reject}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
