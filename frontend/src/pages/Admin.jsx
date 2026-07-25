import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Euro, ShoppingCart, Package, Users, Plus, Trash2, Download, Search, X } from "lucide-react";
import { useI18n } from "@/i18n";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";

export default function Admin() {
  const { t } = useI18n();
  const [tab, setTab] = useState("products");
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
            { key: "products", label: t.admin.tabProducts },
            { key: "orders", label: t.admin.tabOrders },
            { key: "cj", label: t.admin.tabCj },
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

        {tab === "products" && <ProductsTab onChange={loadStats} />}
        {tab === "orders" && <OrdersTab />}
        {tab === "cj" && <CjTab onImport={loadStats} />}
      </div>
    </div>
  );
}

const EMPTY = { title: "", title_en: "", price: "", compare_at_price: "", category: "smart-home", images: "", description: "", description_en: "", featured: false };

function ProductsTab({ onChange }) {
  const { t } = useI18n();
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const load = () => api.get("/products?size=100").then((r) => setProducts(r.data.items));
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setShowForm(true); };
  const openEdit = (p) => {
    setEditing(p.id);
    setForm({ ...p, price: p.price, compare_at_price: p.compare_at_price || "", images: (p.images || []).join(", ") });
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

  return (
    <div data-testid="admin-products-tab">
      <div className="flex justify-end mb-6">
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
              <p className="text-stone text-sm">{p.category} · {p.price.toFixed(2)}€ {p.featured && `· ${t.admin.featured}`}</p>
            </div>
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
            <button type="submit" className="w-full mt-6 bg-brand text-white py-4 rounded-full font-medium hover:bg-ink transition-colors" data-testid="save-product-btn">{t.admin.save}</button>
          </motion.form>
        </div>
      )}
    </div>
  );
}

function OrdersTab() {
  const { t } = useI18n();
  const [orders, setOrders] = useState([]);
  const statuses = ["pending", "processing", "shipped", "delivered", "cancelled"];
  const load = () => api.get("/admin/orders").then((r) => setOrders(r.data.items));
  useEffect(() => { load(); }, []);

  const setStatus = async (id, status) => {
    await api.put(`/admin/orders/${id}/status?status=${status}`);
    load();
    toast.success("OK");
  };

  return (
    <div className="border border-ink/10 divide-y divide-ink/10" data-testid="admin-orders-tab">
      {orders.length === 0 && <p className="p-8 text-stone text-center">{t.account.noOrders}</p>}
      {orders.map((o) => (
        <div key={o.id} className="p-5 flex flex-wrap items-center gap-4" data-testid={`admin-order-${o.id}`}>
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
      const r = await api.post(`/admin/cj/import/${pid}?margin=${Number(margin)}&category=${category}`);
      setImportedPids((s) => ({ ...s, [pid]: "done" }));
      toast.success(`${t.admin.imported}: ${(r.data.title || "").slice(0, 28)} · ${r.data.price}€`);
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
      const r = await api.post(`/admin/cj/import-bulk`, { pids, margin: Number(margin), category });
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
