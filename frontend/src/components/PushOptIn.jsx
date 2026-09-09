import React, { useState, useEffect } from "react";
import { Bell, BellRing } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export default function PushOptIn() {
  const [state, setState] = useState("idle"); // idle | subscribed | unsupported | busy
  const supported = typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window;

  useEffect(() => {
    if (!supported) { setState("unsupported"); return; }
    navigator.serviceWorker.ready
      .then((reg) => reg.pushManager.getSubscription())
      .then((sub) => setState(sub ? "subscribed" : "idle"))
      .catch(() => {});
  }, [supported]);

  const enable = async () => {
    if (!supported) { toast.error("Notifications non supportées par ce navigateur"); return; }
    setState("busy");
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { toast.error("Autorisation refusée"); setState("idle"); return; }
      const { data } = await api.get("/push/vapid-public-key");
      if (!data.configured) { toast.error("Notifications non configurées côté serveur"); setState("idle"); return; }
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(data.public_key),
      });
      const json = sub.toJSON();
      await api.post("/push/subscribe", { endpoint: json.endpoint, keys: json.keys });
      setState("subscribed");
      toast.success("Notifications activées ! Vous serez alerté des ventes flash 🔔");
    } catch (e) {
      setState("idle");
      toast.error("Impossible d'activer les notifications");
    }
  };

  if (state === "unsupported") return null;

  return (
    <button
      onClick={enable}
      disabled={state === "busy" || state === "subscribed"}
      className="inline-flex items-center gap-2 text-sm text-white/70 hover:text-brand transition-colors disabled:text-brand disabled:cursor-default"
      data-testid="push-optin-btn"
    >
      {state === "subscribed" ? <BellRing className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
      {state === "subscribed" ? "Notifications activées" : state === "busy" ? "Activation…" : "Activer les notifications"}
    </button>
  );
}
