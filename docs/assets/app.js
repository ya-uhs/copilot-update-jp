const state = { articles: [] };
const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const formatDateTime = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "不明" : new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tokyo"
  }).format(date);
};

fetch("status.json", {cache: "no-cache"}).then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(status => {
  const error = status.source_error_count ? ` · 取得失敗 ${status.source_error_count}件` : "";
  byId("refresh-info").textContent = `最終確認 ${formatDateTime(status.last_checked_at)} · 最新記事 ${formatDateTime(status.latest_article_at)} · 翻訳 ${status.translated_count}/${status.article_count}${error}`;
}).catch(() => {
  byId("refresh-info").textContent = "更新状況を取得できません · 日本時間 7 / 13 / 19時更新";
});

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
  const query = byId('search').value.trim().toLowerCase();
  const visible = state.articles.filter(a =>
    (!query || `${a.title_ja} ${a.title_original} ${a.summary_ja} ${a.excerpt_original}`.toLowerCase().includes(query)) &&
    (!product || a.product === product) && (!importance || (a.translated && a.importance === importance)) && (!status || a.status === status));
  byId("count").textContent = `${visible.length}件`;
  byId("articles").innerHTML = visible.length ? visible.map(article => {
    const date = new Intl.DateTimeFormat("ja-JP", {dateStyle: "medium"}).format(new Date(article.published_at));
    const title = article.title_ja || article.title_original;
    const summary = article.summary_ja || article.excerpt_original || "要約はありません。";
    const changes = (article.changes || []).map(change => `<li>${escapeHtml(change)}</li>`).join("");
    return `<article class="${article.family === 'github' ? 'github' : 'microsoft'}">
      <div class="meta"><span>${escapeHtml(article.source)}</span><time>${escapeHtml(date)}</time></div>
      <h3><button class="article-open" data-id="${escapeHtml(article.id)}">${escapeHtml(title)}</button></h3>
      <p class="excerpt">${escapeHtml(summary)}</p>
      <div class="tags"><span>${escapeHtml(article.product)}</span><span>${escapeHtml(article.status || 'unknown')}</span></div>
      <div class="foot"><span class="importance ${article.translated ? escapeHtml(article.importance) : ''}">${article.translated ? escapeHtml({high:'重要',medium:'通常',low:'軽微'}[article.importance]) : '翻訳待ち'}</span><a href="${escapeHtml(article.source_url)}" target="_blank" rel="noopener noreferrer">公式原文 ↗</a></div>
    </article>`;
  }).join("") : "<p class='empty'>条件に一致する記事はありません。</p>";
}

byId('articles').addEventListener('click', event => {
  const button = event.target.closest('.article-open'); if (!button) return;
  const a = state.articles.find(a => a.id === button.dataset.id); if (!a) return;
  byId('reader-content').innerHTML = `<p>${escapeHtml(a.source)} · ${escapeHtml(a.published_at.slice(0,10))}</p><h2 id="reader-title">${escapeHtml(a.title_ja || a.title_original)}</h2><p>${escapeHtml(a.summary_ja || a.excerpt_original)}</p><ul>${(a.changes || []).map(c=>`<li>${escapeHtml(c)}</li>`).join('')}</ul><a href="${escapeHtml(a.source_url)}" target="_blank" rel="noopener noreferrer">公式原文を読む ↗</a>`;
  byId('reader').showModal();
});
byId('close-reader').addEventListener('click', () => byId('reader').close());
byId('search').addEventListener('input', render);
['grid','compact'].forEach(id => byId(id).addEventListener('click', () => {
  byId('articles').classList.toggle('compact', id === 'compact');
  ['grid','compact'].forEach(key => byId(key).setAttribute('aria-pressed', String(key === id)));
}));

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
