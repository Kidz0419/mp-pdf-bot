async function refreshStatus() {
  try {
    const r = await fetch("/api/status");
    const s = await r.json();
    const dot = document.getElementById("status-dot");
    const txt = document.getElementById("status-text");
    dot.className = "dot dot-" + (s.syncing ? "blue" : (s.launchd === "running" && s.http === 200 ? "green" : "red"));
    txt.textContent = s.syncing ? "正在同步…" :
                      (s.launchd === "running" && s.http === 200) ? `服务运行中 · HTTP ${s.http}` :
                      "服务异常";
    document.getElementById("db-size").textContent = `DB ${s.db_kb} KB`;
    document.getElementById("pdf-count").textContent = `PDF ${s.pdf_count} 篇`;
  } catch (e) {
    document.getElementById("status-text").textContent = "GUI 后端不可达";
  }
}

async function refreshFeeds() {
  const r = await fetch("/api/feeds");
  const feeds = await r.json();
  const wrap = document.getElementById("feeds-list");
  if (feeds.length === 0) {
    wrap.innerHTML = "<p style='color:var(--muted)'>还没有 PDF。先到 Dashboard 加公众号 → 等 wewe-rss 拉文章 → Sync Now。</p>";
    return;
  }
  wrap.innerHTML = feeds.map(f => `
    <details class="feed" ${feeds.length === 1 ? "open" : ""}>
      <summary>${escapeHTML(f.mp_name)} (${f.count})</summary>
      <ul class="feed-pdfs">
        ${f.pdfs.map(p => `
          <li>
            <a href="/pdfs/${encodeURIComponent(f.mp_name)}/${encodeURIComponent(p.name)}" target="_blank">📄 ${escapeHTML(p.name)}</a>
            <span class="size">${p.size_kb} KB</span>
          </li>`).join("")}
      </ul>
    </details>
  `).join("");
}

function escapeHTML(s) {
  return s.replace(/[<>&"']/g, c => ({"<":"&lt;",">":"&gt;","&":"&amp;","\"":"&quot;","'":"&#39;"}[c]));
}

async function triggerSync() {
  const btn = document.getElementById("sync-btn");
  btn.disabled = true;
  btn.textContent = "同步中…";
  try {
    await fetch("/api/sync", { method: "POST" });
    // Poll until idle
    while (true) {
      await new Promise(r => setTimeout(r, 2000));
      const s = await (await fetch("/api/sync/status")).json();
      if (s.state === "idle") {
        const r = s.last_result;
        btn.textContent = r ? `完成（成功 ${r.ok} / 跳过 ${r.skip} / 失败 ${r.fail}）` : "同步完成";
        await refreshFeeds();
        await refreshStatus();
        break;
      }
    }
  } finally {
    setTimeout(() => { btn.disabled = false; btn.textContent = "Sync Now"; }, 4000);
  }
}

function tickHeader() {
  document.getElementById("header-time").textContent = new Date().toLocaleString("zh-CN");
}

document.getElementById("sync-btn").addEventListener("click", triggerSync);
tickHeader(); setInterval(tickHeader, 1000);
refreshStatus(); setInterval(refreshStatus, 5000);
refreshFeeds(); setInterval(refreshFeeds, 30000);
