const defaults = JSON.parse(document.getElementById("defaults").textContent);

const $ = (id) => document.getElementById(id);
const systemEl = $("system-prompt");
const userEl = $("user-prompt");
const taskEl = $("task");
const topicEl = $("topic-md");
const threadsEl = $("seed-threads");
const entriesEl = $("seed-entries");

function resetPrompts() {
  systemEl.value = defaults.system;
  userEl.value = taskEl.value === "topic_curation" ? defaults.user_topic : defaults.user_synthesis;
  topicEl.value = defaults.topic_md;
  threadsEl.value = JSON.stringify(defaults.threads, null, 2);
  entriesEl.value = JSON.stringify(defaults.entries, null, 2);
}
resetPrompts();

taskEl.addEventListener("change", () => {
  // Swap the user prompt to the matching task default, but only if the user
  // hasn't diverged from the existing default (avoids nuking edits).
  const current = userEl.value.trim();
  const otherDefault = taskEl.value === "topic_curation" ? defaults.user_synthesis : defaults.user_topic;
  if (current === defaults.user_synthesis.trim() || current === defaults.user_topic.trim()
      || current === otherDefault.trim()) {
    userEl.value = taskEl.value === "topic_curation" ? defaults.user_topic : defaults.user_synthesis;
  }
});

$("reset-btn").addEventListener("click", (e) => {
  e.preventDefault();
  resetPrompts();
});

function selectedModels() {
  const rows = document.querySelectorAll(".model-row");
  const out = [];
  rows.forEach(row => {
    const check = row.querySelector(".model-check");
    const slug = row.querySelector(".model-slug").value.trim();
    const label = check.dataset.label;
    if (check.checked && slug) out.push({ label, slug });
  });
  return out;
}

function parseSeed(el, name) {
  try {
    const v = JSON.parse(el.value);
    if (!Array.isArray(v)) throw new Error(`${name} must be a JSON array`);
    return v;
  } catch (e) {
    throw new Error(`invalid ${name}: ${e.message}`);
  }
}

async function run() {
  const models = selectedModels();
  if (!models.length) { alert("Tick at least one model."); return; }

  const body = {
    api_key: $("api-key").value.trim(),
    system: systemEl.value,
    user: userEl.value,
    models,
    temperature: parseFloat($("temperature").value),
    max_tokens: parseInt($("max-tokens").value, 10),
  };

  const btn = $("run-btn");
  btn.disabled = true;
  btn.textContent = `Running ${models.length} model${models.length>1?"s":""}...`;
  renderRunning(models);
  try {
    const r = await fetch("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) { alert(data.error || "run failed"); renderResults([]); return; }
    renderResults(data.results);
  } catch (e) {
    alert("request failed: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run against selected models";
  }
}
$("run-btn").addEventListener("click", run);

function renderRunning(models) {
  const results = $("results");
  results.classList.remove("results-empty");
  results.innerHTML = models.map(m => `
    <div class="result" data-label="${escapeHtml(m.label)}">
      <header>
        <h3>${escapeHtml(m.label)}</h3>
        <span class="meta">${escapeHtml(m.slug)} · running…</span>
      </header>
      <p class="muted">Awaiting response…</p>
    </div>
  `).join("");
}

function renderResults(results) {
  const el = $("results");
  if (!results.length) {
    el.classList.add("results-empty");
    el.innerHTML = `<p class="muted">No results.</p>`;
    return;
  }
  el.classList.remove("results-empty");
  el.innerHTML = results.map((r, i) => renderResultCard(r, i)).join("");
  // Wire up per-card buttons.
  document.querySelectorAll("[data-action=deploy]").forEach(btn => {
    btn.addEventListener("click", () => startDeploy(btn.dataset.idx));
  });
  document.querySelectorAll("[data-action=toggle-raw]").forEach(btn => {
    btn.addEventListener("click", () => {
      const pre = btn.parentElement.querySelector("pre.raw");
      pre.hidden = !pre.hidden;
      btn.textContent = pre.hidden ? "Show raw JSON" : "Hide raw JSON";
    });
  });
  window.__results = results; // so deploy has access by idx
}

function renderResultCard(r, idx) {
  const usage = r.usage ? ` · ${fmtUsage(r.usage)}` : "";
  const status = r.ok
    ? `<span class="status-ok">ok</span>`
    : `<span class="status-err">failed</span>`;
  const rationale = r.parsed?.rationale
    ? `<p class="rationale">“${escapeHtml(r.parsed.rationale)}”</p>` : "";
  const topic = r.parsed?.topic_md
    ? `<p class="rationale">proposed topic: “${escapeHtml(r.parsed.topic_md)}”</p>` : "";
  const ops = Array.isArray(r.parsed?.operations) && r.parsed.operations.length
    ? `<ul class="ops">${r.parsed.operations.map(o => `
        <li>${escapeHtml(o.op||"?")} ${escapeHtml(o.collection||"?")}/<strong>${escapeHtml(o.slug||"?")}</strong>
          ${o.frontmatter?.title ? `— ${escapeHtml(o.frontmatter.title)}` : ""}
        </li>`).join("")}</ul>` : "";
  const reply = r.parsed?.reply_summary
    ? `<p class="muted"><em>reply:</em> ${escapeHtml(r.parsed.reply_summary)}</p>` : "";
  const err = r.error ? `<p class="status-err">${escapeHtml(r.error)}</p>` : "";
  const canDeploy = r.ok && r.parsed && Array.isArray(r.parsed.operations);

  return `
    <div class="result" data-idx="${idx}">
      <header>
        <h3>${escapeHtml(r.model_label)}</h3>
        <span class="meta">${status} · ${r.duration_ms}ms${usage} · ${escapeHtml(r.slug)}</span>
      </header>
      ${rationale}${topic}${ops}${reply}${err}
      <div class="result-actions">
        ${canDeploy ? `<button class="primary" data-action="deploy" data-idx="${idx}">Build &amp; preview site</button>` : ""}
        <button class="ghost" data-action="toggle-raw">Show raw JSON</button>
      </div>
      <pre class="raw" hidden>${escapeHtml(r.raw_text || "(empty)")}</pre>
      <div class="preview-box" hidden></div>
    </div>
  `;
}

function fmtUsage(u) {
  const bits = [];
  if (u.prompt_tokens != null) bits.push(`${u.prompt_tokens}→`);
  if (u.completion_tokens != null) bits.push(`${u.completion_tokens}`);
  if (u.total_tokens != null && !bits.length) bits.push(`${u.total_tokens}t`);
  return bits.join(" ") + " tok";
}

async function startDeploy(idx) {
  const r = window.__results[idx];
  if (!r) return;
  const card = document.querySelector(`.result[data-idx="${idx}"]`);
  const box = card.querySelector(".preview-box");
  box.hidden = false;
  box.innerHTML = `<div class="phase-line">queued…</div>`;

  let seed_threads, seed_entries;
  try {
    seed_threads = parseSeed(threadsEl, "seed threads");
    seed_entries = parseSeed(entriesEl, "seed entries");
  } catch (e) {
    box.innerHTML = `<div class="phase-line status-err">${escapeHtml(e.message)}</div>`;
    return;
  }

  const body = {
    model_label: r.model_label,
    plan: r.parsed,
    topic_md: r.parsed?.topic_md || topicEl.value,
    seed_threads, seed_entries,
  };

  let res;
  try {
    const resp = await fetch("/api/deploy", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    res = await resp.json();
    if (!resp.ok) throw new Error(res.error || "deploy failed");
  } catch (e) {
    box.innerHTML = `<div class="phase-line status-err">${escapeHtml(e.message)}</div>`;
    return;
  }

  const previewId = res.preview_id;
  pollDeploy(previewId, box);
}

async function pollDeploy(previewId, box) {
  const terminal = new Set(["ready", "failed"]);
  const t0 = Date.now();
  while (true) {
    let state;
    try {
      const r = await fetch(`/api/deploy/${previewId}`);
      state = await r.json();
    } catch (e) {
      box.innerHTML = `<div class="phase-line status-err">poll failed: ${escapeHtml(e.message)}</div>`;
      return;
    }
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    box.querySelector(".phase-line")
      ? box.querySelector(".phase-line").textContent =
          `${state.phase}: ${state.detail || ""} (${elapsed}s)`
      : (box.innerHTML = `<div class="phase-line">${escapeHtml(state.phase)}: ${escapeHtml(state.detail || "")} (${elapsed}s)</div>`);

    if (terminal.has(state.phase)) {
      if (state.phase === "failed") {
        box.innerHTML = `
          <div class="phase-line status-err">failed: ${escapeHtml(state.error || "")}</div>
          ${state.build_log_tail ? `<pre>${escapeHtml(state.build_log_tail)}</pre>` : ""}
        `;
      } else {
        const url = state.preview_url;
        box.innerHTML = `
          <div class="phase-line status-ok">deployed (simulated) in ${elapsed}s — files: ${state.files_written.length}</div>
          <a class="open-link" href="${url}" target="_blank" rel="noopener">open in new tab ↗</a>
          <iframe src="${url}" title="preview"></iframe>
        `;
      }
      return;
    }
    await new Promise(r => setTimeout(r, 900));
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
