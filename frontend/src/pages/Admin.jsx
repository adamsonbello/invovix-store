import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Euro, ShoppingCart, Package, Users, Plus, Trash2, Download, Search, X, Edit, Mail, Tag, Settings } from "lucide-react";
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
            { key: "products", label: t.admin.tabProducts },
            { key: "orders", label: t.admin.tabOrders },
            { key: "returns", label: t.admin.tabReturns },
            { key: "cj", label: t.admin.tabCj },
            { key: "blog", label: t.admin.tabBlog },
            { key: "messages", label: t.admin.tabMessages },
            { key: "promos", label: t.admin.tabPromos },
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
        {tab === "products" && <ProductsTab onChange={loadStats} />}
        {tab === "orders" && <OrdersTab />}
        {tab === "returns" && <ReturnsTab />}
        {tab === "cj" && <CjTab onImport={loadStats} />}
        {tab === "blog" && <BlogTab />}
        {tab === "messages" && <MessagesTab />}
        {tab === "promos" && <PromosTab />}
        {tab === "settings" && <SettingsTab />}
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

  const [syncing, setSyncing] = useState(false);
  const syncStocks = async () => {
    setSyncing(true);
    try {
      const r = await api.post("/admin/products/sync-stock-all");
      toast.success(`${t.admin.syncStock} (${r.data.queued})`);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSyncing(false); }
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
      });
      toast.success(t.admin.settingsSaved);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSaving(false);
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
        <label className="flex items-center gap-3 font-medium">
          <input type="checkbox" checked={s.whatsapp_enabled} onChange={(e) => setS({ ...s, whatsapp_enabled: e.target.checked })} className="accent-brand w-4 h-4" data-testid="settings-whatsapp-enabled" />
          {t.admin.whatsappEnabled}
        </label>
        <div>
          <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{t.admin.whatsappNumber}</label>
          <input value={s.whatsapp_number} onChange={(e) => setS({ ...s, whatsapp_number: e.target.value })} placeholder="33612345678" className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink" data-testid="settings-whatsapp-number" />
        </div>
      </div>

      <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-brand text-white px-8 py-3.5 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="settings-save-btn">
        <Settings className="w-4 h-4" /> {saving ? t.common.loading : t.admin.saveSettings}
      </button>
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
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
        {kpis.map((k) => (
          <div key={k.key} className="bg-surface p-5" data-testid={`kpi-${k.key}`}>
            <p className="text-xs tracking-[0.12em] uppercase font-bold text-stone">{k.label}</p>
            <p className="font-display font-black text-2xl mt-2">{k.value}</p>
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
                <Bar dataKey="qty" fill="#0a0a0a" radius={[0, 4, 4, 0]} />
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
