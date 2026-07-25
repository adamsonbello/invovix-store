import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { CreditCard, Loader2, Lock } from "lucide-react";
import { useI18n } from "@/i18n";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";

export default function Checkout() {
  const { t, lang } = useI18n();
  const { items, subtotal, clear } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [method, setMethod] = useState("stripe");
  const [config, setConfig] = useState({ paypal: false });
  const [processing, setProcessing] = useState(false);
  const [form, setForm] = useState({
    full_name: user?.name || "",
    email: user?.email || "",
    address: "",
    city: "",
    postal_code: "",
    country: "France",
    phone: "",
  });

  const shipping = subtotal >= 50 ? 0 : 4.9;
  const total = subtotal + shipping;

  useEffect(() => {
    api.get("/payments/config").then((r) => setConfig(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (items.length === 0) navigate("/cart");
  }, [items.length, navigate]);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const createOrder = async () => {
    const res = await api.post("/orders", {
      items: items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
      shipping_address: form,
    });
    return res.data;
  };

  const payStripe = async () => {
    setProcessing(true);
    try {
      const order = await createOrder();
      const res = await api.post("/payments/stripe/checkout", {
        order_id: order.id,
        origin_url: window.location.origin,
      });
      window.location.href = res.data.checkout_url;
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
      setProcessing(false);
    }
  };

  const payPaypal = async () => {
    setProcessing(true);
    try {
      const order = await createOrder();
      const res = await api.post(`/payments/paypal/create/${order.id}`);
      // A full PayPal JS SDK flow will be wired once live keys are set.
      toast.success("PayPal order created: " + res.data.paypal_order_id);
      setProcessing(false);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
      setProcessing(false);
    }
  };

  const submit = (e) => {
    e.preventDefault();
    if (!user) {
      toast.error(t.checkout.loginFirst);
      navigate("/login");
      return;
    }
    if (method === "stripe") payStripe();
    else payPaypal();
  };

  const required = ["full_name", "email", "address", "city", "postal_code", "country"];
  const valid = required.every((k) => form[k]?.trim());

  return (
    <div className="pt-28 md:pt-36 pb-32" data-testid="checkout-page">
      <div className="max-w-[1400px] mx-auto px-5 md:px-10">
        <h1 className="font-display font-black uppercase tracking-tighter text-5xl md:text-7xl mb-4">{t.checkout.title}</h1>
        {!user && (
          <p className="text-brand mb-8" data-testid="login-notice">
            {t.checkout.loginFirst} <Link to="/login" className="underline font-medium">{t.auth.signin}</Link>
          </p>
        )}

        <form onSubmit={submit} className="grid grid-cols-1 lg:grid-cols-5 gap-12 mt-8">
          <div className="lg:col-span-3 space-y-8">
            <div>
              <h2 className="font-display font-bold text-xl mb-6">{t.checkout.contact}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field name="full_name" label={t.checkout.fullName} value={form.full_name} onChange={handleChange} span2 />
                <Field name="email" type="email" label={t.checkout.email} value={form.email} onChange={handleChange} span2 />
                <Field name="address" label={t.checkout.address} value={form.address} onChange={handleChange} span2 />
                <Field name="postal_code" label={t.checkout.postal} value={form.postal_code} onChange={handleChange} />
                <Field name="city" label={t.checkout.city} value={form.city} onChange={handleChange} />
                <Field name="country" label={t.checkout.country} value={form.country} onChange={handleChange} />
                <Field name="phone" label={t.checkout.phone} value={form.phone} onChange={handleChange} />
              </div>
            </div>

            <div>
              <h2 className="font-display font-bold text-xl mb-6">{t.checkout.payment}</h2>
              <div className="space-y-3">
                <label className={`flex items-center gap-4 p-5 border cursor-pointer transition-colors ${method === "stripe" ? "border-ink bg-surface" : "border-ink/20"}`} data-testid="pay-stripe">
                  <input type="radio" name="method" checked={method === "stripe"} onChange={() => setMethod("stripe")} className="accent-brand" />
                  <CreditCard className="w-5 h-5" />
                  <span className="font-medium">{t.checkout.card}</span>
                </label>
                <label className={`flex items-center gap-4 p-5 border transition-colors ${config.paypal ? "cursor-pointer" : "opacity-50 cursor-not-allowed"} ${method === "paypal" ? "border-ink bg-surface" : "border-ink/20"}`} data-testid="pay-paypal">
                  <input type="radio" name="method" disabled={!config.paypal} checked={method === "paypal"} onChange={() => setMethod("paypal")} className="accent-brand" />
                  <span className="font-bold text-[#003087] italic">Pay<span className="text-[#0070E0]">Pal</span></span>
                  {!config.paypal && <span className="text-xs text-stone ml-auto">{t.checkout.paypalSoon}</span>}
                </label>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-surface p-8 sticky top-28">
              <h2 className="font-display font-bold text-xl mb-6">{t.checkout.summary}</h2>
              <div className="space-y-4 max-h-64 overflow-auto mb-6">
                {items.map((it) => {
                  const title = lang === "en" ? it.title_en || it.title : it.title;
                  return (
                    <div key={it.product_id} className="flex gap-3 items-center text-sm">
                      <img src={it.image} alt={title} className="w-12 h-14 object-cover bg-[#e8e7e4]" />
                      <div className="flex-1">
                        <p className="font-medium leading-tight">{title}</p>
                        <p className="text-stone">×{it.quantity}</p>
                      </div>
                      <span className="font-medium">{(it.price * it.quantity).toFixed(2)}€</span>
                    </div>
                  );
                })}
              </div>
              <div className="space-y-2 text-sm border-t border-ink/10 pt-4">
                <div className="flex justify-between"><span className="text-stone">{t.cart.subtotal}</span><span>{subtotal.toFixed(2)}€</span></div>
                <div className="flex justify-between"><span className="text-stone">{t.cart.shipping}</span><span>{shipping === 0 ? t.cart.free : `${shipping.toFixed(2)}€`}</span></div>
              </div>
              <div className="flex justify-between items-baseline py-5 border-t border-ink/10 mt-2">
                <span className="font-display font-bold text-lg">{t.cart.total}</span>
                <span className="font-display font-black text-2xl">{total.toFixed(2)}€</span>
              </div>
              <button
                type="submit"
                disabled={processing || !valid}
                className="w-full bg-brand text-white px-6 py-4 rounded-full font-medium hover:bg-ink transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                data-testid="pay-submit"
              >
                {processing ? <><Loader2 className="w-4 h-4 animate-spin" /> {t.checkout.processing}</> : <><Lock className="w-4 h-4" /> {t.checkout.pay} {total.toFixed(2)}€</>}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ name, label, value, onChange, type = "text", span2 = false }) {
  return (
    <div className={span2 ? "md:col-span-2" : ""}>
      <label className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2 block">{label}</label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        className="w-full px-4 py-3 border border-ink/20 bg-transparent outline-none focus:border-ink transition-colors"
        data-testid={`field-${name}`}
      />
    </div>
  );
}
