const SITE_KEY = process.env.REACT_APP_RECAPTCHA_SITE_KEY;
let loadPromise;

export function loadRecaptcha() {
  if (!SITE_KEY) return Promise.resolve();
  if (loadPromise) return loadPromise;
  loadPromise = new Promise((resolve) => {
    if (window.grecaptcha) return resolve();
    const s = document.createElement("script");
    s.src = `https://www.google.com/recaptcha/api.js?render=${SITE_KEY}`;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => resolve();
    document.body.appendChild(s);
  });
  return loadPromise;
}

export async function executeRecaptcha(action) {
  if (!SITE_KEY) return "";
  await loadRecaptcha();
  return new Promise((resolve) => {
    if (!window.grecaptcha) return resolve("");
    window.grecaptcha.ready(() => {
      window.grecaptcha
        .execute(SITE_KEY, { action })
        .then(resolve)
        .catch(() => resolve(""));
    });
  });
}
