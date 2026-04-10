const state = {
  elections: [],
  currentElectionId: null,
  currentElection: null,
  currentRecord: null,
  currentLogs: [],
  pendingBallot: null,
  tallyResult: null,
  verificationResult: null,
  activeRole: "admin",
};

const elements = {
  healthValue: document.getElementById("health-value"),
  activeRoleLabel: document.getElementById("active-role-label"),
  selectedElectionLabel: document.getElementById("selected-election-label"),
  contextElectionId: document.getElementById("context-election-id"),
  electionSelect: document.getElementById("election-select"),
  pendingCountLabel: document.getElementById("pending-count-label"),
  verificationFlagLabel: document.getElementById("verification-flag-label"),
  tallyFlagLabel: document.getElementById("tally-flag-label"),
  verifySuccessLabel: document.getElementById("verify-success-label"),
  recordSizeLabel: document.getElementById("record-size-label"),
  logSizeLabel: document.getElementById("log-size-label"),
  electionList: document.getElementById("election-list"),
  ballotBuilder: document.getElementById("ballot-builder"),
  pendingTicket: document.getElementById("pending-ticket"),
  summaryStatus: document.getElementById("summary-status"),
  summaryCast: document.getElementById("summary-cast"),
  summaryChallenge: document.getElementById("summary-challenge"),
  summaryPending: document.getElementById("summary-pending"),
  recordView: document.getElementById("record-view"),
  verificationView: document.getElementById("verification-view"),
  auditLogView: document.getElementById("audit-log-view"),
  prepareButton: document.getElementById("prepare-ballot"),
  castButton: document.getElementById("cast-ballot"),
  challengeButton: document.getElementById("challenge-ballot"),
  tallyButton: document.getElementById("tally-election"),
  verifyButton: document.getElementById("verify-election"),
  reloadRecordButton: document.getElementById("reload-record"),
  reloadLogsButton: document.getElementById("reload-logs"),
  exportRecordButton: document.getElementById("export-record"),
  exportVerificationButton: document.getElementById("export-verification"),
  exportLogsButton: document.getElementById("export-logs"),
  exportElectionButton: document.getElementById("export-election"),
  createElectionForm: document.getElementById("create-election-form"),
  refreshAll: document.getElementById("refresh-all"),
  valueModal: document.getElementById("value-modal"),
  valueModalTitle: document.getElementById("value-modal-title"),
  valueModalContent: document.getElementById("value-modal-content"),
  closeValueModal: document.getElementById("close-value-modal"),
  confirmValueModal: document.getElementById("confirm-value-modal"),
  copyValueModal: document.getElementById("copy-value-modal"),
  toast: document.getElementById("toast"),
  electionIdInput: document.getElementById("election-id"),
  electionTitleInput: document.getElementById("election-title"),
  roleTabs: [...document.querySelectorAll(".role-tab")],
  roleViews: [...document.querySelectorAll(".role-view")],
};

function apiHeaders(extra = {}) {
  return {
    "Content-Type": "application/json",
    ...extra,
  };
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: apiHeaders(options.headers),
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null ? payload.detail || JSON.stringify(payload) : String(payload);
    throw new Error(message);
  }
  return payload;
}

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function truncateValue(value, visible = 10) {
  const text = String(value ?? "");
  if (text.length <= visible) {
    return text;
  }
  return `${text.slice(0, visible)}...`;
}

function buildRevealButton(label, value) {
  const text = String(value ?? "");
  return `
    <button
      class="value-chip"
      type="button"
      data-reveal-title="${escapeHtml(label)}"
      data-reveal-value="${escapeHtml(text)}"
      title="单击查看完整内容"
    >
      ${escapeHtml(truncateValue(text))}
    </button>
  `;
}

function openValueModal(title, value) {
  elements.valueModalTitle.textContent = title;
  elements.valueModalContent.textContent = String(value ?? "");
  elements.valueModal.dataset.currentValue = String(value ?? "");
  elements.valueModal.classList.remove("hidden");
}

function closeValueModal() {
  elements.valueModal.classList.add("hidden");
  elements.valueModal.dataset.currentValue = "";
}

async function copyCurrentModalValue() {
  const value = elements.valueModal.dataset.currentValue || "";
  try {
    await navigator.clipboard.writeText(value);
    showToast("完整内容已复制");
  } catch (error) {
    showToast("复制失败，请手动复制", "error");
  }
}

function showToast(message, type = "info") {
  elements.toast.textContent = message;
  elements.toast.className = `toast ${type === "error" ? "error" : ""}`;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.className = "toast hidden";
  }, 2800);
}

function setActiveRole(role) {
  state.activeRole = role;
  const roleLabel = {
    admin: "管理员",
    device: "投票设备",
    verifier: "验证者",
  };
  elements.activeRoleLabel.textContent = roleLabel[role] || role;

  elements.roleTabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.role === role);
  });
  elements.roleViews.forEach((view) => {
    view.classList.toggle("active", view.dataset.roleView === role);
  });
}

function buildDemoManifest() {
  const now = new Date();
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
    String(now.getSeconds()).padStart(2, "0"),
  ].join("");
  return {
    election_id: elements.electionIdInput.value.trim() || `demo-${stamp}`,
    title: elements.electionTitleInput.value.trim() || `校园示范选举 ${stamp.slice(0, 8)}`,
    metadata: { template: "demo", source: "frontend" },
    contests: [
      {
        contest_id: "chair",
        title: "主席竞选",
        candidates: ["alice", "bob", "carol"],
        min_selections: 1,
        max_selections: 1,
        allowed_values: [0, 1],
      },
      {
        contest_id: "budget",
        title: "预算提案",
        candidates: ["approve", "reject"],
        min_selections: 1,
        max_selections: 1,
        allowed_values: [0, 1],
      },
    ],
  };
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function refreshHealth() {
  try {
    const data = await apiRequest("/health");
    elements.healthValue.textContent = data.status === "ok" ? "在线" : data.status;
  } catch (error) {
    elements.healthValue.textContent = "异常";
    showToast(`健康检查失败：${error.message}`, "error");
  }
}

async function refreshElectionList(selectElectionId = state.currentElectionId) {
  const elections = await apiRequest("/elections");
  state.elections = elections;
  renderElectionList();
  renderElectionSelect();
  if (selectElectionId) {
    const exists = elections.some((item) => item.election_id === selectElectionId);
    if (exists) {
      await loadElection(selectElectionId);
      return;
    }
  }
  if (!state.currentElectionId && elections.length > 0) {
    await loadElection(elections[0].election_id);
  } else {
    syncSummary();
    updateActionButtons();
  }
}

function renderElectionSelect() {
  const options = ['<option value="">请选择选举</option>'];
  for (const election of state.elections) {
    const selected = election.election_id === state.currentElectionId ? "selected" : "";
    options.push(
      `<option value="${escapeHtml(election.election_id)}" ${selected}>${escapeHtml(election.title)}</option>`
    );
  }
  elements.electionSelect.innerHTML = options.join("");
}

function renderElectionList() {
  if (state.elections.length === 0) {
    elements.electionList.className = "election-list empty-state";
    elements.electionList.textContent = "暂无选举，先创建一个演示选举。";
    return;
  }

  elements.electionList.className = "election-list";
  elements.electionList.innerHTML = state.elections
    .map((election) => {
      const active = election.election_id === state.currentElectionId ? "active" : "";
      return `
        <button class="election-card ${active}" type="button" data-election-id="${escapeHtml(election.election_id)}">
          <div class="election-card-head">
            <h3>${escapeHtml(election.title)}</h3>
            <span class="status-pill ${escapeHtml(election.status)}">${escapeHtml(election.status)}</span>
          </div>
          <p>${escapeHtml(election.election_id)}</p>
          <small>创建时间：${escapeHtml(election.created_at)}</small>
        </button>
      `;
    })
    .join("");

  elements.electionList.querySelectorAll("[data-election-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await loadElection(button.dataset.electionId);
    });
  });
}

async function loadElection(electionId, options = {}) {
  const { preservePending = false } = options;
  const [detail, record, logs] = await Promise.all([
    apiRequest(`/elections/${encodeURIComponent(electionId)}`),
    apiRequest(`/elections/${encodeURIComponent(electionId)}/record`),
    apiRequest(`/elections/${encodeURIComponent(electionId)}/audit-logs`),
  ]);

  state.currentElectionId = electionId;
  state.currentElection = detail;
  state.currentRecord = record;
  state.currentLogs = logs;
  state.tallyResult = detail.tally || null;
  state.verificationResult = detail.verification || null;

  if (!preservePending) {
    state.pendingBallot = null;
  }

  renderElectionList();
  renderElectionSelect();
  renderCurrentElection();
  showToast(`已载入选举：${detail.title}`);
}

function renderCurrentElection() {
  const election = state.currentElection;
  if (!election) {
    elements.selectedElectionLabel.textContent = "未选择";
    elements.contextElectionId.textContent = "暂无";
    elements.pendingCountLabel.textContent = "0";
    elements.verificationFlagLabel.textContent = "否";
    elements.tallyFlagLabel.textContent = "否";
    elements.verifySuccessLabel.textContent = "未执行";
    elements.recordSizeLabel.textContent = "0";
    elements.logSizeLabel.textContent = "0";

    elements.ballotBuilder.className = "ballot-builder empty-state";
    elements.ballotBuilder.textContent = "请先在管理员视图中创建或选择一场选举。";
    elements.pendingTicket.className = "pending-ticket empty-state";
    elements.pendingTicket.textContent = "尚未生成待处理选票。";
    elements.recordView.className = "data-pane empty-state";
    elements.recordView.textContent = "暂无公开记录。";
    elements.verificationView.className = "data-pane empty-state";
    elements.verificationView.textContent = "尚未生成 tally 或验证结果。";
    elements.auditLogView.className = "timeline empty-state";
    elements.auditLogView.textContent = "选择一个选举后查看审计日志。";

    syncSummary();
    updateActionButtons();
    return;
  }

  elements.selectedElectionLabel.textContent = election.title;
  elements.contextElectionId.textContent = election.election_id;
  elements.pendingCountLabel.textContent = String(election.pending_ballot_count);
  elements.verificationFlagLabel.textContent = election.has_verification ? "是" : "否";
  elements.tallyFlagLabel.textContent = election.has_tally ? "是" : "否";
  elements.verifySuccessLabel.textContent =
    election.verification == null ? "未执行" : election.verification.success ? "通过" : "未通过";
  elements.recordSizeLabel.textContent = String(state.currentRecord?.entries?.length || 0);
  elements.logSizeLabel.textContent = String(state.currentLogs?.length || 0);

  renderBallotBuilder(election.manifest);
  renderPendingBallot();
  renderRecord();
  renderVerification();
  renderAuditLogs();
  syncSummary();
  updateActionButtons();
}

function renderBallotBuilder(manifest) {
  const contests = manifest?.contests || [];
  if (contests.length === 0) {
    elements.ballotBuilder.className = "ballot-builder empty-state";
    elements.ballotBuilder.textContent = "当前选举没有可用竞赛项。";
    return;
  }

  elements.ballotBuilder.className = "ballot-builder";
  elements.ballotBuilder.innerHTML = `
    <div class="contest-grid">
      ${contests
        .map((contest) => {
          const inputType = contest.max_selections === 1 ? "radio" : "checkbox";
          return `
            <section class="contest-card" data-contest-id="${escapeHtml(contest.contest_id)}" data-max="${contest.max_selections}">
              <h3>${escapeHtml(contest.title)}</h3>
              <div class="contest-option-list">
                ${contest.candidates
                  .map(
                    (candidate) => `
                      <label class="contest-option">
                        <input type="${inputType}" name="contest-${escapeHtml(contest.contest_id)}" value="${escapeHtml(candidate)}" />
                        <span>${escapeHtml(candidate)}</span>
                      </label>
                    `
                  )
                  .join("")}
              </div>
              <p class="contest-meta">规则：最少 ${contest.min_selections} 项，最多 ${contest.max_selections} 项</p>
            </section>
          `;
        })
        .join("")}
    </div>
  `;

  elements.ballotBuilder.querySelectorAll('.contest-card input[type="checkbox"]').forEach((input) => {
    input.addEventListener("change", () => {
      const card = input.closest(".contest-card");
      const max = Number(card.dataset.max || "1");
      const checked = [...card.querySelectorAll('input[type="checkbox"]:checked')];
      if (checked.length > max) {
        input.checked = false;
        showToast(`该竞赛项最多只能选择 ${max} 项`, "error");
      }
    });
  });
}

function collectSelections() {
  const selections = {};
  for (const contest of state.currentElection.manifest.contests) {
    const inputs = [...document.querySelectorAll(`[name="contest-${contest.contest_id}"]:checked`)];
    selections[contest.contest_id] = inputs.map((input) => input.value);
  }
  return selections;
}

function renderPendingBallot() {
  if (!state.pendingBallot) {
    elements.pendingTicket.className = "pending-ticket empty-state";
    elements.pendingTicket.textContent = "尚未生成待处理选票。";
    return;
  }
  const ballot = state.pendingBallot;
  elements.pendingTicket.className = "pending-ticket";
  elements.pendingTicket.innerHTML = `
    <div class="ticket-grid">
      <div class="ticket-card">
        <span>Ballot ID</span>
        <strong>${escapeHtml(ballot.ballot_id)}</strong>
      </div>
      <div class="ticket-card">
        <span>Sequence</span>
        <strong>${escapeHtml(ballot.sequence_no)}</strong>
      </div>
      <div class="ticket-card">
        <span>Confirmation Code</span>
        <strong>${buildRevealButton("Confirmation Code", ballot.confirmation_code)}</strong>
      </div>
      <div class="ticket-card">
        <span>Identifier Hash</span>
        <strong>${buildRevealButton("Identifier Hash", ballot.identifier_hash)}</strong>
      </div>
    </div>
    <div class="code-block" style="margin-top: 12px;">
      <pre>${escapeHtml(formatJson(ballot))}</pre>
    </div>
  `;

  elements.pendingTicket.querySelectorAll("[data-reveal-value]").forEach((button) => {
    button.addEventListener("click", () => {
      openValueModal(button.dataset.revealTitle || "完整内容", button.dataset.revealValue || "");
    });
  });
}

function renderRecord() {
  if (!state.currentRecord) {
    elements.recordView.className = "data-pane empty-state";
    elements.recordView.textContent = "暂无公开记录。";
    return;
  }
  elements.recordView.className = "data-pane";
  elements.recordView.innerHTML = `<pre>${escapeHtml(formatJson(state.currentRecord))}</pre>`;
}

function renderVerification() {
  if (!state.tallyResult && !state.verificationResult) {
    elements.verificationView.className = "data-pane empty-state";
    elements.verificationView.textContent = "尚未生成 tally 或验证结果。";
    return;
  }
  const payload = {
    tally: state.tallyResult,
    verification: state.verificationResult,
  };
  elements.verificationView.className = "data-pane";
  elements.verificationView.innerHTML = `<pre>${escapeHtml(formatJson(payload))}</pre>`;
}

function renderAuditLogs() {
  if (!state.currentLogs || state.currentLogs.length === 0) {
    elements.auditLogView.className = "timeline empty-state";
    elements.auditLogView.textContent = "当前选举暂无审计日志。";
    return;
  }
  elements.auditLogView.className = "timeline";
  elements.auditLogView.innerHTML = state.currentLogs
    .map(
      (entry) => `
        <article class="timeline-item">
          <strong>${escapeHtml(entry.event_type)}</strong>
          <div>${escapeHtml(entry.created_at)}</div>
          <p>${escapeHtml(formatJson(entry.payload))}</p>
        </article>
      `
    )
    .join("");
}

function syncSummary() {
  const election = state.currentElection;
  elements.summaryStatus.textContent = election ? election.status : "未选择";
  elements.summaryCast.textContent = election ? String(election.cast_ballot_count) : "0";
  elements.summaryChallenge.textContent = election ? String(election.challenged_ballot_count) : "0";
  elements.summaryPending.textContent = election ? String(election.pending_ballot_count) : "0";
}

function updateActionButtons() {
  const hasElection = Boolean(state.currentElectionId);
  const hasPending = Boolean(state.pendingBallot);
  const hasRecord = Boolean(state.currentRecord);
  const hasLogs = Boolean(state.currentLogs && state.currentLogs.length);
  const hasVerification = Boolean(state.verificationResult || state.tallyResult);

  elements.prepareButton.disabled = !hasElection;
  elements.castButton.disabled = !hasElection || !hasPending;
  elements.challengeButton.disabled = !hasElection || !hasPending;
  elements.tallyButton.disabled = !hasElection;
  elements.verifyButton.disabled = !hasElection;
  elements.reloadRecordButton.disabled = !hasElection;
  elements.reloadLogsButton.disabled = !hasElection;
  elements.exportRecordButton.disabled = !hasRecord;
  elements.exportVerificationButton.disabled = !hasVerification;
  elements.exportLogsButton.disabled = !hasLogs;
  elements.exportElectionButton.disabled = !hasElection;
}

async function handleCreateElection(event) {
  event.preventDefault();
  try {
    const election = await apiRequest("/elections", {
      method: "POST",
      body: JSON.stringify(buildDemoManifest()),
    });
    showToast(`选举 ${election.title} 创建成功`);
    await refreshElectionList(election.election_id);
  } catch (error) {
    showToast(`创建失败：${error.message}`, "error");
  }
}

async function handlePrepareBallot() {
  if (!state.currentElectionId) return;
  try {
    state.pendingBallot = await apiRequest(`/elections/${encodeURIComponent(state.currentElectionId)}/ballots/prepare`, {
      method: "POST",
      body: JSON.stringify({ selections: collectSelections() }),
    });
    await loadElection(state.currentElectionId, { preservePending: true });
    showToast("选票已准备，可以选择 cast 或 challenge");
  } catch (error) {
    showToast(`准备选票失败：${error.message}`, "error");
  }
}

async function handleCastBallot() {
  if (!state.currentElectionId || !state.pendingBallot) return;
  try {
    await apiRequest(
      `/elections/${encodeURIComponent(state.currentElectionId)}/ballots/${encodeURIComponent(state.pendingBallot.ballot_id)}/cast`,
      { method: "POST" }
    );
    state.pendingBallot = null;
    await loadElection(state.currentElectionId);
    showToast("选票已成功 cast");
  } catch (error) {
    showToast(`Cast 失败：${error.message}`, "error");
  }
}

async function handleChallengeBallot() {
  if (!state.currentElectionId || !state.pendingBallot) return;
  try {
    await apiRequest(
      `/elections/${encodeURIComponent(state.currentElectionId)}/ballots/${encodeURIComponent(state.pendingBallot.ballot_id)}/challenge`,
      { method: "POST" }
    );
    state.pendingBallot = null;
    await loadElection(state.currentElectionId);
    showToast("选票已进入 challenge 流程");
  } catch (error) {
    showToast(`Challenge 失败：${error.message}`, "error");
  }
}

async function handleTallyElection() {
  if (!state.currentElectionId) return;
  try {
    state.tallyResult = await apiRequest(`/elections/${encodeURIComponent(state.currentElectionId)}/tally`, {
      method: "POST",
    });
    await loadElection(state.currentElectionId);
    showToast("Tally 生成成功");
  } catch (error) {
    showToast(`Tally 失败：${error.message}`, "error");
  }
}

async function handleVerifyElection() {
  if (!state.currentElectionId) return;
  try {
    state.verificationResult = await apiRequest(`/elections/${encodeURIComponent(state.currentElectionId)}/verify`);
    await loadElection(state.currentElectionId);
    showToast(
      state.verificationResult.success ? "验证通过" : "验证未通过",
      state.verificationResult.success ? "info" : "error"
    );
  } catch (error) {
    showToast(`验证失败：${error.message}`, "error");
  }
}

async function handleReloadRecord() {
  if (!state.currentElectionId) return;
  try {
    state.currentRecord = await apiRequest(`/elections/${encodeURIComponent(state.currentElectionId)}/record`);
    renderRecord();
    updateActionButtons();
    showToast("公开记录已刷新");
  } catch (error) {
    showToast(`刷新公开记录失败：${error.message}`, "error");
  }
}

async function handleReloadLogs() {
  if (!state.currentElectionId) return;
  try {
    state.currentLogs = await apiRequest(`/elections/${encodeURIComponent(state.currentElectionId)}/audit-logs`);
    renderAuditLogs();
    updateActionButtons();
    showToast("审计日志已刷新");
  } catch (error) {
    showToast(`刷新审计日志失败：${error.message}`, "error");
  }
}

function handleExportRecord() {
  if (!state.currentElectionId || !state.currentRecord) return;
  downloadJson(`${state.currentElectionId}-record.json`, state.currentRecord);
  showToast("公开记录已导出");
}

function handleExportVerification() {
  if (!state.currentElectionId || (!state.tallyResult && !state.verificationResult)) return;
  downloadJson(`${state.currentElectionId}-verification.json`, {
    tally: state.tallyResult,
    verification: state.verificationResult,
  });
  showToast("验证结果已导出");
}

function handleExportLogs() {
  if (!state.currentElectionId || !state.currentLogs) return;
  downloadJson(`${state.currentElectionId}-audit-logs.json`, state.currentLogs);
  showToast("审计日志已导出");
}

function handleExportElection() {
  if (!state.currentElectionId || !state.currentElection) return;
  downloadJson(`${state.currentElectionId}-snapshot.json`, {
    election: state.currentElection,
    record: state.currentRecord,
    logs: state.currentLogs,
    pendingBallot: state.pendingBallot,
    tally: state.tallyResult,
    verification: state.verificationResult,
  });
  showToast("选举快照已导出");
}

async function initialize() {
  const now = new Date();
  elements.electionIdInput.value = `demo-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
  elements.electionTitleInput.value = "校园理事会示范选举";

  elements.roleTabs.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveRole(button.dataset.role);
    });
  });

  elements.electionSelect.addEventListener("change", async (event) => {
    if (event.target.value) {
      await loadElection(event.target.value);
    }
  });

  elements.createElectionForm.addEventListener("submit", handleCreateElection);
  elements.prepareButton.addEventListener("click", handlePrepareBallot);
  elements.castButton.addEventListener("click", handleCastBallot);
  elements.challengeButton.addEventListener("click", handleChallengeBallot);
  elements.tallyButton.addEventListener("click", handleTallyElection);
  elements.verifyButton.addEventListener("click", handleVerifyElection);
  elements.reloadRecordButton.addEventListener("click", handleReloadRecord);
  elements.reloadLogsButton.addEventListener("click", handleReloadLogs);
  elements.exportRecordButton.addEventListener("click", handleExportRecord);
  elements.exportVerificationButton.addEventListener("click", handleExportVerification);
  elements.exportLogsButton.addEventListener("click", handleExportLogs);
  elements.exportElectionButton.addEventListener("click", handleExportElection);
  elements.closeValueModal.addEventListener("click", closeValueModal);
  elements.confirmValueModal.addEventListener("click", closeValueModal);
  elements.copyValueModal.addEventListener("click", copyCurrentModalValue);
  elements.valueModal.addEventListener("click", (event) => {
    if (event.target instanceof HTMLElement && event.target.dataset.closeModal === "true") {
      closeValueModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.valueModal.classList.contains("hidden")) {
      closeValueModal();
    }
  });

  elements.refreshAll.addEventListener("click", async () => {
    try {
      await refreshHealth();
      await refreshElectionList(state.currentElectionId);
      showToast("系统状态已刷新");
    } catch (error) {
      showToast(`刷新失败：${error.message}`, "error");
    }
  });

  setActiveRole("admin");
  await refreshHealth();
  await refreshElectionList();
}

window.addEventListener("DOMContentLoaded", () => {
  initialize().catch((error) => {
    showToast(`初始化失败：${error.message}`, "error");
  });
});
