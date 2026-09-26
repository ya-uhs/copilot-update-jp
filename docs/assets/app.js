const state = { articles: [] };
const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function addOptions(id, values) {
  const select = byId(id);
  [...new Set(values.filter(Boolean))].sort().forEach(value => {
    const option = document.createElement("option");
    option.value = option.textContent = value;
    select.appendChild(option);
  });
}

function render() {
  const product = byId("product").value;
  const importance = byId("importance").value;
  const status = byId("status").value;
  const visible = state.articles.filter(a =>
    (!product || a.product === product) && (!importance || a.importance === importance) && (!status || a.status === status));
  byId("count").textContent = `${visible.length}件`;
  byId("articles").innerHTML = visible.length ? visible.map(article => {
    const date = new Intl.DateTimeFormat("ja-JP", {dateStyle: "medium"}).format(new Date(article.published_at));
    const title = article.title_ja || article.title_original;
    const summary = article.summary_ja || article.excerpt_original || "要約はありません。";
    const changes = (article.changes || []).map(change => `<li>${escapeHtml(change)}</li>`).join("");
    return `<article>
      <div class="meta"><time>${escapeHtml(date)}</time><span>${escapeHtml(article.product || "unknown")}</span><span class="importance ${escapeHtml(article.importance)}">${escapeHtml(article.importance)}</span></div>
      <h2><a href="${escapeHtml(article.source_url)}" rel="noopener noreferrer">${escapeHtml(title)}</a></h2>
      <p>${escapeHtml(summary)}</p>
      ${changes ? `<ul>${changes}</ul>` : ""}
      <div class="foot"><span>Status: ${escapeHtml(article.status || "unknown")}</span>${article.translated ? "" : "<span>English / 翻訳待ち</span>"}<a href="${escapeHtml(article.source_url)}" rel="noopener noreferrer">公式原文 →</a></div>
    </article>`;
  }).join("") : "<p class='empty'>条件に一致する記事はありません。</p>";
}

fetch("data.json", {cache: "no-cache"}).then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(articles => {
  state.articles = articles.sort((a, b) => String(b.published_at).localeCompare(String(a.published_at)));
  addOptions("product", articles.map(a => a.product));
  addOptions("status", articles.map(a => a.status));
  ["product", "importance", "status"].forEach(id => byId(id).addEventListener("change", render));
  render();
}).catch(error => { byId("articles").innerHTML = `<p class="empty">データを読み込めませんでした: ${escapeHtml(error.message)}</p>`; });

