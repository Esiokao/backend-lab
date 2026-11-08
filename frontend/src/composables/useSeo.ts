// SEO 標籤管理：title / meta description / canonical 的統一寫入點。
// 每頁在 setup 呼叫一次即可；router 的 afterEach 會對未覆寫的頁面套用
// meta.title 預設值（見 router/index.ts）。

const SITE_NAME = "Backend Lab";

function upsertMeta(attr: "name" | "property", key: string, content: string): void {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

function upsertCanonical(href: string): void {
  let el = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", "canonical");
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
}

export function applySeo(options: {
  title?: string;
  description?: string;
  path?: string;
}): void {
  const { title, description, path } = options;

  if (title) document.title = `${title} · ${SITE_NAME}`;

  if (description) upsertMeta("name", "description", description);

  // canonical：相對路徑轉絕對（同源）——告訴爬蟲正式網址，防 query
  // 變體（?cat=&q=）被當重複內容。
  if (path) upsertCanonical(`${window.location.origin}${path}`);
}
