import React, { useEffect, useState } from "react";
import { CheckCircle2, Truck } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import { Stars, StarInput } from "@/components/StarRating";

export default function ProductReviews({ productId }) {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const [data, setData] = useState({ items: [], count: 0, rating_avg: 0, delivery_avg: 0 });
  const [can, setCan] = useState(null);
  const [form, setForm] = useState({ rating: 5, delivery_rating: 5, comment: "" });
  const [submitting, setSubmitting] = useState(false);

  const load = () => api.get(`/products/${productId}/reviews`).then((r) => setData(r.data));
  useEffect(() => { load(); }, [productId]);
  useEffect(() => {
    if (user) api.get(`/products/${productId}/can-review`).then((r) => setCan(r.data)).catch(() => setCan(null));
    else setCan(null);
  }, [user, productId]);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post(`/products/${productId}/reviews`, form);
      toast.success(t.reviews.thanks);
      setForm({ rating: 5, delivery_rating: 5, comment: "" });
      await load();
      setCan({ can_review: false, already_reviewed: true, purchased: true });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="mt-20 border-t border-ink/10 pt-16" data-testid="reviews-section">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        <div>
          <h2 className="font-display font-black uppercase tracking-tighter text-4xl md:text-5xl">{t.reviews.title}</h2>
          <div className="mt-8 space-y-6">
            <div className="flex items-center gap-4" data-testid="reviews-avg-product">
              <span className="font-display font-black text-5xl">{data.rating_avg.toFixed(1)}</span>
              <div>
                <Stars value={data.rating_avg} size={20} />
                <p className="text-stone text-sm mt-1">{data.count} {t.reviews.based}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 border border-ink/10 p-4" data-testid="reviews-avg-delivery">
              <Truck className="w-6 h-6 text-brand shrink-0" strokeWidth={1.5} />
              <div className="flex-1">
                <p className="text-xs tracking-[0.15em] uppercase font-bold text-stone">{t.reviews.transport}</p>
                <div className="flex items-center gap-2 mt-1">
                  <Stars value={data.delivery_avg} size={16} />
                  <span className="text-sm font-medium">{data.delivery_avg.toFixed(1)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Review form / states */}
          <div className="mt-8">
            {!user && <p className="text-stone text-sm">{t.reviews.loginToReview}</p>}
            {user && can && can.already_reviewed && <p className="text-stone text-sm">{t.reviews.already}</p>}
            {user && can && !can.purchased && <p className="text-stone text-sm">{t.reviews.mustBuy}</p>}
            {user && can && can.can_review && (
              <form onSubmit={submit} className="bg-surface p-6 space-y-5" data-testid="review-form">
                <div>
                  <p className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2">{t.reviews.yourRating}</p>
                  <StarInput value={form.rating} onChange={(v) => setForm({ ...form, rating: v })} testid="review-rating" />
                </div>
                <div>
                  <p className="text-xs tracking-[0.15em] uppercase font-bold text-stone mb-2">{t.reviews.deliveryRating}</p>
                  <StarInput value={form.delivery_rating} onChange={(v) => setForm({ ...form, delivery_rating: v })} testid="review-delivery" />
                </div>
                <textarea
                  value={form.comment}
                  onChange={(e) => setForm({ ...form, comment: e.target.value })}
                  placeholder={t.reviews.placeholder}
                  rows={4}
                  className="w-full px-4 py-3 border border-ink/20 bg-cream outline-none focus:border-ink transition-colors"
                  data-testid="review-comment"
                />
                <button type="submit" disabled={submitting} className="w-full bg-brand text-white py-3.5 rounded-full font-medium hover:bg-ink transition-colors disabled:opacity-50" data-testid="review-submit">
                  {submitting ? t.common.loading : t.reviews.submit}
                </button>
              </form>
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          {data.items.length === 0 ? (
            <div className="text-stone py-10" data-testid="reviews-empty">{t.reviews.empty}</div>
          ) : (
            <div className="divide-y divide-ink/10">
              {data.items.map((r) => (
                <div key={r.id} className="py-6" data-testid={`review-${r.id}`}>
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-ink text-cream flex items-center justify-center font-display font-bold">
                        {r.user_name?.[0]?.toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium leading-tight">{r.user_name}</p>
                        {r.verified_purchase && (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" /> {t.reviews.verified}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-stone text-xs">{new Date(r.created_at).toLocaleDateString(lang)}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-4">
                    <div className="flex items-center gap-2">
                      <span className="text-xs tracking-wide uppercase text-stone font-bold">{t.reviews.product}</span>
                      <Stars value={r.rating} size={15} />
                    </div>
                    <div className="flex items-center gap-2">
                      <Truck className="w-4 h-4 text-stone" />
                      <Stars value={r.delivery_rating} size={15} />
                    </div>
                  </div>
                  {r.comment && <p className="text-ink/80 mt-3 leading-relaxed">{r.comment}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
