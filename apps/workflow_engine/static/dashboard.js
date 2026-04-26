const $ = (s) => document.querySelector(s);
const slugsEl = $('#slugs');
const healthEl = $('#health');
const emptyEl = $('#empty');
const logEl = $('#log');
const refreshBtn = $('#refresh');
const lastRefresh = $('#last-refresh');
const dlg = $('#confirm');
const portHint = $('#port-hint');
if (portHint) portHint.textContent = window.location.port || '(default)';

let modelsCache = {downloaded: [], loaded: []};

function el(tag, attrs = {}, text) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k === 'class') e.className = v;
        else if (k === 'dataset') Object.assign(e.dataset, v);
        else if (v === true) e.setAttribute(k, '');
        else if (v === false || v == null) {}
        else e.setAttribute(k, v);
    }
    if (text !== undefined) e.textContent = text;
    return e;
}

function badge(cls, text) {
    return el('span', {class: `badge ${cls}`}, text);
}

function badgeRow(s) {
    const wrap = el('div', {class: 'badges'});
    wrap.appendChild(s.paused ? badge('paused', 'paused') : badge('active', 'active'));
    if (s.in_flight) wrap.appendChild(badge('inflight', 'in-flight'));
    if (!s.site_exists) wrap.appendChild(badge('missing', 'no site dir'));
    return wrap;
}

function fmtTime(iso) {
    if (!iso) return 'never';
    const d = new Date(iso);
    const ago = Math.round((Date.now() - d.getTime()) / 60000);
    if (ago < 1) return 'just now';
    if (ago < 60) return `${ago}m ago`;
    if (ago < 1440) return `${Math.round(ago / 60)}h ago`;
    return `${Math.round(ago / 1440)}d ago`;
}

function logMsg(result) {
    const cls = !result.ok ? 'err' : (result.warnings && result.warnings.length) ? 'warn' : 'ok';
    const entry = el('div', {class: `entry ${cls}`});
    const title = el('div');
    title.appendChild(document.createTextNode(`${result.action} `));
    title.appendChild(el('b', {}, result.slug || ''));
    title.appendChild(document.createTextNode(` — ${result.ok ? 'OK' : 'FAILED'}`));
    entry.appendChild(title);
    const bits = [...(result.steps || []), ...(result.warnings || []).map(w => `warning: ${w}`)];
    if (result.error) bits.push(`error: ${result.error}`);
    if (bits.length) {
        const steps = el('div', {class: 'steps'});
        bits.forEach((b, i) => {
            if (i > 0) steps.appendChild(el('br'));
            steps.appendChild(document.createTextNode(b));
        });
        entry.appendChild(steps);
    }
    logEl.appendChild(entry);
    setTimeout(() => entry.remove(), 9000);
}

function confirmDialog(title, body) {
    $('#confirm-title').textContent = title;
    $('#confirm-body').textContent = body;
    return new Promise(resolve => {
        dlg.addEventListener('close', function onclose() {
            dlg.removeEventListener('close', onclose);
            resolve(dlg.returnValue === 'ok');
        });
        dlg.showModal();
    });
}

async function doAction(slug, action, method) {
    let ok = true;
    if (action === 'delete') {
        ok = await confirmDialog(
            `Delete "${slug}"?`,
            'Removes the config entry, local site files, local state, and attempts remote cleanup on the hosting provider. This cannot be undone.'
        );
    } else if (action === 'reset') {
        ok = await confirmDialog(
            `Reset "${slug}"?`,
            'Keeps the config entry. Wipes local site + state + remote deployment, then re-bootstraps from the template. Content is lost.'
        );
    }
    if (!ok) return;
    const url = `/api/slugs/${encodeURIComponent(slug)}${action === 'delete' ? '' : '/' + action}`;
    try {
        const resp = await fetch(url, {method});
        const result = await resp.json();
        logMsg(result);
    } catch (e) {
        logMsg({ok: false, slug, action, error: String(e), steps: [], warnings: []});
    }
    await refresh();
}

function metaRow(label, contentNode) {
    const dt = el('dt', {}, label);
    const dd = el('dd');
    if (typeof contentNode === 'string') dd.textContent = contentNode;
    else dd.appendChild(contentNode);
    return [dt, dd];
}

function urlLink(href) {
    if (!href) return el('span', {class: 'muted mono'}, '(not set)');
    const a = el('a', {href, target: '_blank', rel: 'noopener'}, href);
    a.classList.add('mono');
    return a;
}

function modelSelect(slug, currentModel) {
    const sel = el('select', {class: 'model-select', dataset: {slug}});
    sel.appendChild(el('option', {value: ''}, `Global (${currentModel})`));
    for (const m of modelsCache.downloaded) {
        const opt = el('option', {value: m.key}, `${m.key} (${m.size_gb} GB)`);
        if (m.key === currentModel) opt.selected = true;
        sel.appendChild(opt);
    }
    sel.addEventListener('change', async () => {
        const model = sel.value;
        try {
            const resp = await fetch(`/api/slugs/${encodeURIComponent(slug)}/model`, {
                method: 'PATCH',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model}),
            });
            const r = await resp.json();
            if (!resp.ok) throw new Error(r.error || resp.statusText);
            logMsg({ok: true, slug, action: 'model', steps: [`set to ${r.model}`], warnings: []});
        } catch (e) {
            logMsg({ok: false, slug, action: 'model', error: String(e), steps: [], warnings: []});
        }
        await refresh();
    });
    return sel;
}

function buildSlugCard(s) {
    const card = el('div', {class: 'slug-card'});

    const main = el('div', {class: 'slug-card-main'});

    const head = el('div', {class: 'slug-card-head'});
    head.appendChild(el('span', {class: 'slug-name'}, s.slug));
    if (s.site_name && s.site_name !== s.slug) {
        head.appendChild(el('span', {class: 'slug-site-name'}, `· ${s.site_name}`));
    }
    head.appendChild(badgeRow(s));
    main.appendChild(head);

    const meta = el('dl', {class: 'slug-meta'});
    metaRow('Address', el('span', {class: 'mono'}, s.address)).forEach(n => meta.appendChild(n));
    metaRow('URL', urlLink(s.site_url)).forEach(n => meta.appendChild(n));
    metaRow('Model', modelSelect(s.slug, s.model)).forEach(n => meta.appendChild(n));
    metaRow('Provider', s.provider).forEach(n => meta.appendChild(n));
    const lastText = s.last_event
        ? `${fmtTime(s.last_event)}${s.last_outcome ? ` · ${s.last_outcome}` : ''}`
        : 'never';
    metaRow('Last event', lastText).forEach(n => meta.appendChild(n));
    main.appendChild(meta);

    card.appendChild(main);

    const actions = el('div', {class: 'actions'});
    if (s.paused) {
        actions.appendChild(el('button', {class: 'btn-inline', dataset: {act: 'resume', slug: s.slug}}, 'Resume'));
    } else {
        actions.appendChild(el('button', {class: 'btn-inline warn', dataset: {act: 'pause', slug: s.slug}}, 'Pause'));
    }
    actions.appendChild(el('button', {class: 'btn-inline warn', dataset: {act: 'reset', slug: s.slug}}, 'Reset'));
    actions.appendChild(el('button', {class: 'btn-inline danger', dataset: {act: 'delete', slug: s.slug}}, 'Delete'));
    card.appendChild(actions);

    return card;
}

function render(data) {
    const h = data.health || {};
    const cls = h.status === 'running' ? 'ok' : h.status ? 'err' : '';
    healthEl.className = `health ${cls}`;
    healthEl.textContent = h.status
        ? `${h.status} · ${h.inboxes_loaded || 0} topic(s) · up ${Math.round((h.uptime_seconds || 0) / 60)}m`
        : '–';

    slugsEl.replaceChildren();
    if (!data.slugs.length) {
        emptyEl.hidden = false;
        return;
    }
    emptyEl.hidden = true;
    for (const s of data.slugs) {
        slugsEl.appendChild(buildSlugCard(s));
    }
}

async function refresh() {
    try {
        const [slugsResp, modelsResp] = await Promise.all([
            fetch('/api/slugs'),
            fetch('/api/models'),
        ]);
        const data = await slugsResp.json();
        try {
            const mdata = await modelsResp.json();
            modelsCache = mdata;
        } catch {}
        render(data);
        lastRefresh.textContent = `refreshed ${new Date().toLocaleTimeString()}`;
    } catch (e) {
        healthEl.textContent = `error: ${e.message}`;
        healthEl.className = 'health err';
    }
}

slugsEl.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const slug = btn.dataset.slug;
    const method = act === 'delete' ? 'DELETE' : 'POST';
    doAction(slug, act, method);
});

refreshBtn.addEventListener('click', refresh);
refresh();
setInterval(refresh, 5000);
