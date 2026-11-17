/* Environment Trainer 前端
 * 状态全部来自后端 /api/state；前端只负责渲染 + 转发键盘输入到 WebSocket 终端。
 */

const $ = (id) => document.getElementById(id);

let STATE = null;
let term = null;
let fitAddon = null;
let resizeTimer = null;
let ws = null;
let hintShown = 0;
let busy = false;
let HOST = null;
let HOST_TAB = null;
let PLATFORM = null;
let VIEW = "term";
const autoAdvance = true;

/* ---------------- 基础请求 ---------------- */
async function api(path, method = "GET") {
  const res = await fetch(path, { method, headers: { "Content-Type": "application/json" } });
  let data;
  try {
    data = await res.json();
  } catch (e) {
    throw new Error(`HTTP ${res.status}`);
  }
  if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function setBtnLabel(id, text) {
  $(id).innerHTML = `${escapeHtml(text)}<span class="arrow">→</span>`;
}

function setStatus(text) {
  $("term-status").textContent = text;
}

/* ---------------- 终端 ---------------- */
function initTerm() {
  if (term) return term;
  const host = $("terminal");

  term = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    lineHeight: 1.28,
    fontFamily: '"SF Mono", "JetBrains Mono", Menlo, Consolas, monospace',
    scrollback: 8000,
    scrollSensitivity: 2,
    fastScrollSensitivity: 6,
    theme: {
      background: "#150c22",
      foreground: "#f0e8f8",
      cursor: "#7bf583",
      cursorAccent: "#150c22",
      selectionBackground: "rgba(180,142,218,0.34)",
      black: "#241634", red: "#ff8fb0", green: "#7bf583",
      yellow: "#ffcb83", blue: "#b48eda", magenta: "#e574ff",
      cyan: "#8ff0e0", white: "#f6e8ff",
      brightBlack: "#5c4a71", brightRed: "#fea6d0", brightGreen: "#a8ffb0",
      brightYellow: "#ffdda8", brightBlue: "#cbb0e8", brightMagenta: "#f1a6ff",
      brightCyan: "#b6fff2", brightWhite: "#ffffff",
    },
  });
  term.open(host);

  fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  fitTerm();

  term.onData((data) => sendInput(data));

  // Shift+PageUp / Shift+PageDown 翻看历史
  term.attachCustomKeyEventHandler((e) => {
    if (e.type === "keydown" && e.shiftKey && (e.key === "PageUp" || e.key === "PageDown")) {
      term.scrollPages(e.key === "PageUp" ? -1 : 1);
      return false;
    }
    return true;
  });

  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (!fitTerm()) return;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ t: "r", cols: term.cols, rows: term.rows }));
      }
    }, 180);
  });

  return term;
}

/* 按真实渲染尺寸重算行列；容器不可见时不动 */
function fitTerm() {
  const wrap = $("view-term");
  if (!wrap || wrap.hidden || wrap.clientHeight < 60) return false;
  try {
    fitAddon.fit();
    return true;
  } catch (e) {
    return false;
  }
}

function sendInput(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ t: "i", d: data }));
  }
}

function closeTerm() {
  if (ws) {
    try { ws.close(); } catch (e) { /* ignore */ }
    ws = null;
  }
}

function connectTerm() {
  if (VIEW !== "term") switchView("term");
  const t = initTerm();
  $("term-placeholder").hidden = true;
  closeTerm();
  t.reset();
  fitTerm();

  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/term?cols=${t.cols}&rows=${t.rows}`;
  ws = new WebSocket(url);
  $("term-title").textContent = "sandbox · 连接中…";
  setStatus("正在建立终端会话…");

  ws.onopen = () => {
    $("term-title").textContent = STATE?.session ? `sandbox · ${STATE.session.name}` : "sandbox";
    setStatus("已连接，输入命令开始干活");
  };
  ws.onmessage = (ev) => {
    let m;
    try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (m.t === "hello") {
      const modeEl = $("term-mode");
      modeEl.textContent = m.mode === "pipe" ? "兼容模式" : m.mode;
      modeEl.className = "term-mode " + (m.mode === "pipe" ? "warn" : "ok");
      if (m.mode === "pipe") {
        t.write(
          "\r\n\x1b[33m[兼容模式] 这台机器上没有可用的伪终端（Windows 需要 10 1809+ 才有 ConPTY）。\r\n" +
          "命令可以正常执行，但 vim / top 这类交互式程序不可用。\r\n" +
          "提示符不会显示，你敲的命令会先回显再执行。\x1b[0m\r\n"
        );
      }
    } else if (m.t === "o") {
      t.write(m.d);
    } else if (m.t === "exit") {
      t.write("\r\n\x1b[33m[会话结束：容器已销毁或 shell 退出]\x1b[0m\r\n");
      setStatus("终端会话已结束");
      $("term-title").textContent = "sandbox · 已断开";
    }
  };
  ws.onclose = () => { if (ws) setStatus("终端连接已关闭"); };
  ws.onerror = () => setStatus("终端连接出错，试试「重连终端」");
}

/* 在容器里执行一条命令（点诊断清单时用） */
function runInTerm(cmd) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    setStatus("先点「开始本关」创建容器，再点这些命令");
    return;
  }
  sendInput(cmd + "\r");
  if (term) term.focus();
}

/* ---------------- 渲染 ---------------- */
function render() {
  if (!STATE) return;
  const { levels, cursor, current, completed, session, finished } = STATE;

  const total = levels.length;
  $("progress-label").textContent = finished ? `${total} / ${total} 关（已完成）` : `第 ${cursor + 1} / ${total} 关`;
  $("progress-points").textContent = `${completed.reduce((n, id) => n + (levels.find((l) => l.id === id)?.points || 100), 0)} 分`;
  $("bar-fill").style.width = total ? `${(completed.length / total) * 100}%` : "0%";

  if (finished || !current) {
    $("level-order").textContent = "✓";
    $("level-cat").textContent = "毕业";
    $("level-cat").className = "tag ok";
    $("level-tool").hidden = true;
    $("level-title").textContent = "全部关卡已完成";
    $("level-summary").textContent =
      "你走完了一整套环境排错流程：版本 / 系统 / 架构 / 编译器 / 环境变量。可以点右上角「重置进度」再来一遍。";
    $("objectives").innerHTML = "";
    $("hints").innerHTML = "";
    $("hint-count").textContent = "";
    $("symptom-block").hidden = true;
    $("diagnose-block").hidden = true;
    $("method-block").hidden = true;
  } else {
    $("level-order").textContent = String(current.order).padStart(2, "0");
    $("level-cat").textContent = current.category_label || "未分类";
    $("level-cat").className = "tag cat-" + (current.category || "unknown");
    const toolEl = $("level-tool");
    toolEl.textContent = current.tool_label || current.tool || "";
    toolEl.hidden = !current.tool;
    $("level-title").textContent = current.title;
    $("level-summary").innerHTML = mdInline(current.summary || "");

    const sym = current.symptom || "";
    $("symptom-block").hidden = !sym;
    $("level-symptom").textContent = sym;

    renderMethod(current.method || {});
    renderDiagnose(current.diagnose || []);
    renderPlatformNotes(current.platform_notes || {});

    $("objectives").innerHTML = (current.objectives || [])
      .map((o) => `<li><span>${mdInline(o)}</span></li>`)
      .join("");

    const hints = current.hints || [];
    if (hintShown === 0 && hints.length) {
      $("hints").innerHTML = `<div class="hint muted">卡住了就点下面「看下一条提示」，一共 ${hints.length} 条。</div>`;
      $("hint-count").textContent = `0 / ${hints.length}`;
    } else {
      $("hints").innerHTML = hints
        .slice(0, hintShown)
        .map((h, i) => `<div class="hint"><b>${i + 1}.</b> ${mdInline(h)}</div>`)
        .join("");
      $("hint-count").textContent = `${Math.min(hintShown, hints.length)} / ${hints.length}`;
    }
  }

  const hasSession = !!session;
  const hasLevel = !!(current && !finished);
  setBtnLabel("btn-start", hasSession ? "重开本关（重置环境）" : "开始本关（创建容器）");
  $("btn-start").disabled = busy || !hasLevel;
  $("btn-check").disabled = busy || !hasSession || !hasLevel;
  $("btn-stop").disabled = busy || !hasSession;
  $("btn-hint").disabled = busy || finished || hintShown >= (current?.hints?.length || 0);

  const canSkip = !!(current && current.skippable && !finished);
  $("btn-skip").hidden = !canSkip;
  $("btn-skip").disabled = busy;
  $("skip-note").hidden = !canSkip;
  if (canSkip) $("skip-note").textContent = current.skip_reason || "这一关可以跳过。";

  if (hasSession) $("term-title").textContent = `sandbox · ${session.name}`;
  else if (!finished) $("term-title").textContent = "sandbox · 未连接";

  syncVscode();

  renderLog(STATE.log || []);
}

const PLATFORM_LABEL = { macos: "macOS", windows: "Windows", linux: "Linux" };

function renderPlatformNotes(notes) {
  const box = $("platform-block");
  const keys = Object.keys(notes || {});
  const mine = PLATFORM ? notes[PLATFORM] : null;
  if (!keys.length || !mine) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  $("platform-name").textContent = PLATFORM_LABEL[PLATFORM] || PLATFORM;
  $("platform-note").textContent = mine;

  const others = keys.filter((k) => k !== PLATFORM);
  $("platform-other-list").innerHTML = others
    .map(
      (k) => `<div class="plat-other"><b>${PLATFORM_LABEL[k] || k}</b>${escapeHtml(notes[k])}</div>`
    )
    .join("");
  $("platform-others").hidden = !others.length;
}

function renderMethod(method) {
  const box = $("method-block");
  if (!method || !method.rule) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  $("method-rule").textContent = method.rule;
  $("method-steps").innerHTML = (method.steps || [])
    .map((step) => `<li>${mdInline(step)}</li>`)
    .join("");
}

function renderDiagnose(list) {
  const box = $("diagnose-list");
  if (!list.length) {
    $("diagnose-block").hidden = true;
    box.innerHTML = "";
    return;
  }
  $("diagnose-block").hidden = false;
  box.innerHTML = list
    .map((c) => `<button class="cmd" data-cmd="${escapeHtml(c)}"><code>${escapeHtml(c)}</code><span class="cmd-run">▸</span></button>`)
    .join("");
  box.querySelectorAll("button.cmd").forEach((b) => {
    b.onclick = () => runInTerm(b.dataset.cmd);
  });
}

function renderLog(items) {
  $("log-items").innerHTML = items
    .slice(-14)
    .map((e) => `<span class="log-item ${e.kind}">${e.t} ${escapeHtml(e.text)}</span>`)
    .join("");
  $("log-items").scrollLeft = $("log-items").scrollWidth;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function mdInline(s) {
  return escapeHtml(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
}

/* ---------------- 判题结果面板 ---------------- */
function showVerdict(pass, head, result) {
  result = result || {};
  const box = $("verdict");
  box.hidden = false;
  box.className = `verdict ${pass ? "pass" : "fail"}`;
  $("verdict-head").textContent = head;

  const checks = result.checks || [];
  $("verdict-checks").innerHTML = checks.length
    ? checks
        .map((c) => {
          const ok = c.status === "ok";
          return `<div class="check-item ${ok ? "ok" : "bad"}">
            <span class="check-ico">${ok ? "✓" : "✗"}</span>
            <span class="check-name">${escapeHtml(c.name)}</span>
            <span class="check-detail">${escapeHtml(c.detail || "")}</span>
          </div>`;
        })
        .join("")
    : "";

  $("verdict-body").textContent = result.output || "";
  const sol = result.solution || [];
  const showSol = pass && sol.length > 0;
  $("verdict-solution").hidden = !showSol;
  $("solution-body").textContent = showSol ? sol.join("\n") : "";
}

/* ---------------- 动作 ---------------- */
async function refresh() {
  STATE = await api("/api/state");
  render();
  return STATE;
}

async function withBusy(fn) {
  if (busy) return;
  busy = true;
  try {
    render();
    await fn();
  } catch (e) {
    showVerdict(false, "出错了", { output: String(e.message || e) });
  } finally {
    busy = false;
    render();
  }
}

async function startSession() {
  await withBusy(async () => {
    setStatus("正在准备容器（首次需要构建镜像，会久一点）…");
    $("verdict").hidden = true;
    hintShown = 0;
    await api("/api/session/start", "POST");
    await refresh();
    connectTerm();
  });
}

async function destroySession() {
  await withBusy(async () => {
    closeTerm();
    $("term-placeholder").hidden = false;
    await api("/api/session/stop", "POST");
    await refresh();
    setStatus("容器已销毁，需要时再点「开始本关」");
    $("verdict").hidden = true;
  });
}

async function runCheck() {
  await withBusy(async () => {
    setStatus("正在容器里跑判题脚本…");
    const res = await api("/api/check", "POST");
    const r = res.result || {};
    await refresh();

    if (r.pass) {
      if (r.finished) {
        showVerdict(true, "通关！整套课程已完成", r);
      } else {
        showVerdict(true, `已通关：${r.level_id} · 容器已销毁 · 下一关容器正在启动`, r);
        closeTerm();
        if (autoAdvance) setTimeout(() => startSession(), 1000);
      }
    } else {
      const failed = (r.checks || []).filter((c) => c.status !== "ok").length;
      showVerdict(false, failed ? `还没通过：${failed} 项未达标` : "还没通过，看下判题输出", r);
      setStatus("判题未通过，改完再提交");
    }
    hintShown = 0;
    render();
  });
}

async function skipLevel() {
  if (!confirm("跳过这一关？\n\n跳过的关不计分，之后可以用「重置进度」重新回来。")) return;
  await withBusy(async () => {
    closeTerm();
    $("term-placeholder").hidden = false;
    setStatus("正在跳过本关…");
    const res = await api("/api/skip", "POST");
    $("verdict").hidden = true;
    await refresh();
    if (res.finished) {
      setStatus("已跳过最后一关");
    } else {
      setStatus(`已跳过，进入下一关`);
      setTimeout(() => startSession(), 700);
    }
  });
}

async function resetProgress() {
  if (!confirm("清空进度并销毁当前容器？")) return;
  await withBusy(async () => {
    closeTerm();
    await api("/api/reset", "POST");
    hintShown = 0;
    $("verdict").hidden = true;
    await refresh();
    setStatus("进度已重置");
  });
}

/* ---------------- 内嵌编辑器 ---------------- */
function syncVscode() {
  const vs = STATE?.session?.vscode;
  const supported = !!(STATE?.current?.vscode && vs);
  $("tab-code").hidden = !supported;

  if (!supported) {
    if (VIEW === "code") switchView("term");
    return;
  }
  if (VIEW !== "code") return;

  const host = !location.hostname || location.hostname === "localhost" ? "127.0.0.1" : location.hostname;
  const url = `http://${host}:${vs.port}/`;
  const frame = $("code-frame");
  if (frame.dataset.url !== url) {
    frame.dataset.url = url;
    frame.src = url;
    $("code-loading").hidden = false;
    frame.onload = () => {
      $("code-loading").hidden = true;
    };
  }
  $("code-loading").textContent = vs.ready
    ? "编辑器正在启动…（首次需要几秒）"
    : "编辑器还在启动，稍等一下…";
}

function switchView(view) {
  VIEW = view;
  $("view-term").hidden = view !== "term";
  $("view-code").hidden = view !== "code";
  $("tab-term").classList.toggle("active", view === "term");
  $("tab-code").classList.toggle("active", view === "code");
  if (view === "code") {
    syncVscode();
    if (term) term.blur();
  } else {
    if (term) {
      fitTerm();
      term.focus();
    }
  }
  $("term-title").textContent = view === "code" ? "VS Code · 容器内文件" : STATE?.session ? `sandbox · ${STATE.session.name}` : "sandbox · 未连接";
}

/* ---------------- 本机环境 ---------------- */
const PLATFORM_TABS = [
  ["macos", "macOS"],
  ["windows", "Windows"],
  ["linux", "Linux"],
];

async function loadHost() {
  const body = $("host-body");
  body.innerHTML = '<div class="host-hint">正在检测这台机器…</div>';
  try {
    HOST = await api("/api/host");
  } catch (e) {
    body.innerHTML = `<div class="host-hint">检测失败：${escapeHtml(e.message)}</div>`;
    return;
  }
  if (!HOST_TAB) HOST_TAB = HOST.platform;
  renderHost();
  updateHostBadge();
}

function updateHostBadge() {
  const btn = $("btn-host");
  if (!btn || !HOST) return;
  btn.textContent = HOST.ready ? "本机环境" : "本机环境 ⚠";
  btn.className = HOST.ready ? "ghost" : "ghost danger";
}

function renderHost() {
  const h = HOST;
  if (!h) return;
  $("host-sub").textContent = `${h.platform_label} · ${h.arch} · ${h.shell.name}`;

  const pm = (h.package_managers || []).map((p) => p.label).join(" / ") || "没检测到";
  const meta = `
    <div class="host-meta">
      <div><b>系统</b>${escapeHtml(h.platform_label)} (${escapeHtml(h.arch)})</div>
      <div><b>Shell</b>${escapeHtml(h.shell.name)} → ${escapeHtml(h.shell.config)}</div>
      <div><b>包管理器</b>${escapeHtml(pm)}</div>
      <div><b>状态</b>${h.ready ? "可以开始上课" : "还差 " + h.missing_required.length + " 项必需组件"}</div>
    </div>
    <div class="host-hint">${escapeHtml(h.shell.note || "")}</div>
  `;

  const items = (h.checks || [])
    .map((c) => {
      const cls = c.ok ? "ok" : "bad";
      const ico = c.ok ? "✓" : "✗";
      const ver = c.ok ? c.version || c.path : c.detail;
      let fix = "";
      if (!c.ok) {
        const cmds = (c.install && c.install[HOST_TAB]) || [];
        const tabs = PLATFORM_TABS.map(
          ([k, label]) =>
            `<span class="host-tab ${k === HOST_TAB ? "active" : ""}" data-tab="${k}">${label}</span>`
        ).join("");
        const cmdHtml = cmds
          .map((cmd) => `<button class="host-cmd" data-cmd="${escapeHtml(cmd)}"><span>${escapeHtml(cmd)}</span><span class="copy">复制</span></button>`)
          .join("");
        fix = `
          <div class="host-fix">
            <div class="host-fix-title">在 ${HOST_TAB === "macos" ? "macOS" : HOST_TAB === "windows" ? "Windows" : "Linux"} 上安装</div>
            <div class="host-platforms">${tabs}</div>
            ${cmdHtml || '<div class="host-hint">没有现成命令，请查官方文档</div>'}
          </div>`;
      }
      return `
        <div class="host-item ${cls}">
          <div class="host-line">
            <span class="host-ico">${ico}</span>
            <span class="host-name">${escapeHtml(c.name)}${c.required ? "" : "（可选）"}</span>
            <span class="host-ver">${escapeHtml(ver || "")}</span>
          </div>
          <div class="host-why">${escapeHtml(c.why || "")}</div>
          ${fix}
        </div>`;
    })
    .join("");

  $("host-body").innerHTML = meta + items;

  $("host-body").querySelectorAll(".host-tab").forEach((el) => {
    el.onclick = () => {
      HOST_TAB = el.dataset.tab;
      renderHost();
    };
  });
  $("host-body").querySelectorAll(".host-cmd").forEach((el) => {
    el.onclick = async () => {
      const cmd = el.dataset.cmd;
      try {
        await navigator.clipboard.writeText(cmd);
        const copy = el.querySelector(".copy");
        copy.textContent = "已复制";
        setTimeout(() => (copy.textContent = "复制"), 1200);
      } catch (e) {
        /* 剪贴板不可用时静默 */
      }
    };
  });
}

function openHost() {
  $("host-mask").hidden = false;
  $("host-drawer").hidden = false;
  if (!HOST) loadHost();
  else renderHost();
}

function closeHost() {
  $("host-mask").hidden = true;
  $("host-drawer").hidden = true;
}

/* ---------------- 启动 ---------------- */
async function boot() {
  try {
    const h = await api("/api/health");
    const chip = $("docker-chip");
    chip.textContent = h.docker ? "docker: 就绪" : "docker: 不可用";
    chip.className = "chip " + (h.docker ? "ok" : "bad");
    if (h.platform) {
      PLATFORM = h.platform;
      const env = $("env-chip");
      env.textContent = `${h.platform} · ${h.terminal}`;
      env.className = "chip";
    }
  } catch (e) { /* ignore */ }

  await refresh();

  if (STATE.session) {
    connectTerm();
  } else {
    $("term-placeholder").hidden = false;
    setStatus("点左侧「开始本关」创建容器，这里会出现容器的 bash");
  }

  $("btn-start").onclick = startSession;
  $("btn-check").onclick = runCheck;
  $("btn-stop").onclick = destroySession;
  $("btn-skip").onclick = skipLevel;
  $("btn-reset").onclick = resetProgress;
  $("tab-term").onclick = () => switchView("term");
  $("tab-code").onclick = () => switchView("code");
  $("btn-host").onclick = openHost;
  $("host-close").onclick = closeHost;
  $("host-mask").onclick = closeHost;
  $("host-refresh").onclick = loadHost;
  loadHost();
  $("btn-reconnect").onclick = () => {
    if (!STATE.session) { setStatus("还没有容器，先点「开始本关」"); return; }
    connectTerm();
  };
  $("btn-hint").onclick = () => {
    const total = STATE.current?.hints?.length || 0;
    hintShown = Math.min(hintShown + 1, total);
    render();
  };
  $("btn-hint-all").onclick = () => {
    hintShown = STATE.current?.hints?.length || 0;
    render();
  };
}

document.addEventListener("DOMContentLoaded", boot);
