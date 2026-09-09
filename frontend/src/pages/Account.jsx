import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Package, FileDown, RotateCcw, User, Send } from "lucide-react";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";

const statusColor = {
  pending: "bg-amber-100 text-amber-700",
  processing: "bg-blue-100 text-blue-700",
  shipped: "bg-indigo-100 text-indigo-700",
  delivered: "bg-emerald-100 text-emerald-700",
  cancelled: "bg-red-100 text-red-700",
};

export default function Account() {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [returns, setReturns] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [loyalty, setLoyalty] = useState(null);
  const [profile, setProfile] = useState({ name: "", email: "", phone: "", address: "", city: "", postal_code: "", country: "" });
  const [savingProfile, setSavingProfile] = useState(false);
  const [msg, setMsg] = useState({ subject: "", message: "" });
  const [sendingMsg, setSendingMsg] = useState(false);

  const load = () => {
    api.get("/orders").then((r) => setOrders(r.data.items)).finally(() => setLoading(false));
    api.get("/returns").then((r) => {
      const map = {};
      (r.data.items || []).forEach((x) => { map[x.order_id] = x; });
      setReturns(map);
    }).catch(() => {});
    api.get("/loyalty").then((r) => setLoyalty(r.data)).catch(() => {});
    api.get("/account/profile").then((r) => setProfile(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const saveProfile = async (e) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      const { email, ...payload } = profile;
      await api.put("/account/profile", payload);
      toast.success("Coordonnées mises à jour");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSavingProfile(false); }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!msg.message.trim()) { toast.error("Écrivez votre message"); return; }
    setSendingMsg(true);
    try {
      await api.post("/account/message", msg);
      toast.success("Message envoyé à la direction");
      setMsg({ subject: "", message: "" });
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSendingMsg(false); }
  };

  const downloadInvoice = async (id) => {
    setBusy(id + "-inv");
    try {
      const res = await api.get(`/orders/${id}/invoice`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `Invovix-Facture-${id.slice(0, 8).toUpperCase()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(t.account.invoiceErr);
    } finally {
      setBusy("");
    }
  };

  const requestReturn = async (id) => {
    const reason = window.prompt(t.account.returnPrompt);
    if (!reason) return;
    setBusy(id + "-ret");
    try {
      await api.post("/returns", { order_id: id, reason });
      toast.success(t.account.returnOk);
      load();
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="account-page">
      <div className="max-w-[1200px] mx-auto px-5 md:px-10">
        <p className="text-xs tracking-[0.2em] uppercase font-bold text-brand mb-3">{t.account.hello}, {user?.name}</p>
        <div className="flex flex-wrap items-end justify-between gap-4 mb-12">
          <h1 className="font-display font-black uppercase tracking-tighter text-5xl md:text-7xl">{t.account.title}</h1>
          <Link to="/wishlist" className="text-sm font-medium hover:text-brand transition-colors">{t.wishlist.title} →</Link>
        </div>

        {loyalty && (
          <div className="border border-ink/10 bg-ink text-cream p-6 md:p-8 mb-12 flex flex-wrap items-center gap-6" data-testid="loyalty-card">
            <div>
              <p className="text-xs tracking-[0.2em] uppercase font-bold text-brand mb-1">Programme fidélité</p>
              <p className="font-display font-black text-4xl">{loyalty.points} <span className="text-lg font-bold text-cream/60">points</span></p>
            </div>
            <div className="h-12 w-px bg-cream/20 hidden md:block" />
            <div>
              <p className="text-xs uppercase text-cream/60 font-bold">Statut</p>
              <p className="font-display font-black text-2xl">{loyalty.tier}</p>
              <p className="text-cream/70 text-sm">{loyalty.perk}</p>
            </div>
            {loyalty.next_tier && (
              <div className="flex-1 min-w-[180px]">
                <p className="text-sm text-cream/70 mb-2">Plus que <strong className="text-brand">{loyalty.to_next.toFixed(2)}€</strong> pour atteindre <strong>{loyalty.next_tier}</strong></p>
                <div className="h-2 bg-cream/15 rounded-full overflow-hidden">
                  <div className="h-2 bg-brand rounded-full" style={{ width: `${Math.min(100, (loyalty.total_spent / (loyalty.total_spent + loyalty.to_next)) * 100)}%` }} />
                </div>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
          <form onSubmit={saveProfile} className="border border-ink/10 p-6" data-testid="account-profile-form">
            <p className="font-display font-bold text-xl mb-5 flex items-center gap-2"><User className="w-5 h-5 text-brand" /> Mes coordonnées</p>
            <div className="grid grid-cols-2 gap-3">
              <Afield label="Nom complet" value={profile.name} onChange={(v) => setProfile({ ...profile, name: v })} span2 testid="profile-name" />
              <div className="col-span-2">
                <label className="text-xs uppercase font-bold text-stone mb-1.5 block">Email</label>
                <input value={profile.email} readOnly aria-readonly="true" className="w-full px-4 py-2.5 border border-ink/10 bg-ink/5 text-stone outline-none cursor-not-allowed" data-testid="profile-email" />
              </div>
              <Afield label="Téléphone" value={profile.phone} onChange={(v) => setProfile({ ...profile, phone: v })} span2 testid="profile-phone" />
              <Afield label="Adresse" value={profile.address} onChange={(v) => setProfile({ ...profile, address: v })} span2 testid="profile-address" />
              <Afield label="Ville" value={profile.city} onChange={(v) => setProfile({ ...profile, city: v })} testid="profile-city" />
              <Afield label="Code postal" value={profile.postal_code} onChange={(v) => setProfile({ ...profile, postal_code: v })} testid="profile-postal" />
              <Afield label="Pays" value={profile.country} onChange={(v) => setProfile({ ...profile, country: v })} span2 testid="profile-country" />
            </div>
            <button type="submit" disabled={savingProfile} className="mt-5 bg-ink text-cream px-6 py-3 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="profile-save-btn">{savingProfile ? "…" : "Enregistrer"}</button>
          </form>

          <form onSubmit={sendMessage} className="border border-ink/10 p-6" data-testid="account-message-form">
            <p className="font-display font-bold text-xl mb-2 flex items-center gap-2"><Send className="w-5 h-5 text-brand" /> Contacter la direction</p>
            <p className="text-stone text-sm mb-5">Une question, une réclamation, une suggestion ? Écrivez-nous, nous vous répondrons par email.</p>
            <Afield label="Sujet" value={msg.subject} onChange={(v) => setMsg({ ...msg, subject: v })} span2 testid="message-subject" />
            <div className="mt-3">
              <label className="text-xs uppercase font-bold text-stone mb-1.5 block">Message</label>
              <textarea value={msg.message} onChange={(e) => setMsg({ ...msg, message: e.target.value })} rows={5} className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" data-testid="message-body" />
            </div>
            <button type="submit" disabled={sendingMsg} className="mt-4 bg-ink text-cream px-6 py-3 rounded-full font-medium hover:bg-brand transition-colors disabled:opacity-50" data-testid="message-send-btn">{sendingMsg ? "Envoi…" : "Envoyer le message"}</button>
          </form>
        </div>

        <h2 className="font-display font-bold text-2xl mb-6">{t.account.orders}</h2>
        {loading ? (
          <p className="text-stone">{t.common.loading}</p>
        ) : orders.length === 0 ? (
          <div className="border border-ink/10 p-12 text-center">
            <Package className="w-10 h-10 mx-auto text-ink/30" strokeWidth={1.2} />
            <p className="text-stone mt-4">{t.account.noOrders}</p>
            <Link to="/shop" className="inline-block mt-6 bg-ink text-cream px-6 py-3 rounded-full font-medium hover:bg-brand transition-colors">{t.payment.shop}</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((o) => {
              const ret = returns[o.id];
              const paid = o.payment_status === "paid";
              const canReturn = paid && ["processing", "shipped", "delivered"].includes(o.status) && !ret;
              return (
                <div key={o.id} className="border border-ink/10 p-6" data-testid={`order-${o.id}`}>
                  <div className="flex flex-wrap justify-between gap-4 items-start">
                    <div>
                      <p className="font-display font-bold">{t.account.order} #{o.id.slice(0, 8).toUpperCase()}</p>
                      <p className="text-stone text-sm mt-1">{new Date(o.created_at).toLocaleDateString(lang)} · {o.items.length} {t.account.items}</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full ${statusColor[o.status] || "bg-gray-100 text-gray-700"}`}>{o.status}</span>
                      <p className="font-display font-black text-xl mt-2">{o.total.toFixed(2)}€</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4 pt-4 border-t border-ink/10 overflow-auto">
                    {o.items.map((it, i) => (
                      <img key={it.product_id + "-" + i} src={it.image} alt={it.title} className="w-14 h-16 object-cover bg-[#f0efed]" title={it.title} />
                    ))}
                  </div>

                  {o.tracking_number && (
                    <a
                      href={o.tracking_url || `https://parcelsapp.com/en/tracking/${o.tracking_number}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 mt-4 text-brand font-medium text-sm hover:text-ink transition-colors"
                      data-testid={`account-tracking-${o.id}`}
                    >
                      📦 {t.account.track}: {o.logistic_name ? `${o.logistic_name} · ` : ""}{o.tracking_number}
                    </a>
                  )}

                  <div className="flex flex-wrap items-center gap-3 mt-4">
                    {paid && (
                      <button
                        onClick={() => downloadInvoice(o.id)}
                        disabled={busy === o.id + "-inv"}
                        className="inline-flex items-center gap-2 text-sm border border-ink/20 px-4 py-2 rounded-full hover:border-ink transition-colors disabled:opacity-50"
                        data-testid={`invoice-${o.id}`}
                      >
                        <FileDown className="w-4 h-4" /> {t.account.invoice}
                      </button>
                    )}
                    {canReturn && (
                      <button
                        onClick={() => requestReturn(o.id)}
                        disabled={busy === o.id + "-ret"}
                        className="inline-flex items-center gap-2 text-sm border border-ink/20 px-4 py-2 rounded-full hover:border-ink transition-colors disabled:opacity-50"
                        data-testid={`return-${o.id}`}
                      >
                        <RotateCcw className="w-4 h-4" /> {t.account.requestReturn}
                      </button>
                    )}
                    {ret && (
                      <span className="text-sm text-stone" data-testid={`return-status-${o.id}`}>
                        {t.account.returnStatus}: <strong>{ret.status}</strong>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function Afield({ label, value, onChange, span2, testid }) {
  return (
    <div className={span2 ? "col-span-2" : ""}>
      <label className="text-xs uppercase font-bold text-stone mb-1.5 block">{label}</label>
      <input value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={testid} className="w-full px-4 py-2.5 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors" />
    </div>
  );
}
