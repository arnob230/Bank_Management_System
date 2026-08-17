requireAuth();

const user = API.user();
document.getElementById("userName").textContent = user.full_name;
document.getElementById("userRole").textContent = user.role;
document.getElementById("userInitials").textContent = initials(user.full_name);
document.getElementById("greetName").textContent = user.full_name.split(" ")[0];

document.getElementById("logoutBtn").addEventListener("click", (e) => {
  e.preventDefault();
  API.clearSession();
  window.location.href = "/index.html";
});

let accounts = [];

async function loadAccounts() {
  accounts = await API.get("/accounts");
  renderLedgerCards();
  populateAccountSelects();
  loadRecentTransactions();
}

function renderLedgerCards() {
  const grid = document.getElementById("ledgerGrid");
  if (accounts.length === 0) {
    grid.innerHTML = `<div class="empty-state"><div class="seal lg">ASB</div><p>No accounts yet. Contact support to open one.</p></div>`;
    return;
  }
  grid.innerHTML = accounts.map(acc => `
    <div class="ledger-card">
      <div class="top-row">
        <div>
          <div class="acc-type">${acc.account_type.replace('_', ' ')}</div>
          <div class="acc-number">${acc.account_number}</div>
        </div>
        <div class="seal sm">ASB</div>
      </div>
      <div class="balance"><small>৳</small>${money(acc.balance)}</div>
      <span class="status-badge ${acc.status !== 'active' ? 'frozen' : ''}">${acc.status}</span>
    </div>
  `).join("");
}

function populateAccountSelects() {
  const options = accounts.map(a => `<option value="${a.id}">${a.account_number} — ${a.account_type} (৳${money(a.balance)})</option>`).join("");
  document.getElementById("txnAccount").innerHTML = options;
  document.getElementById("fromAccount").innerHTML = options;
}

async function loadRecentTransactions() {
  const body = document.getElementById("recentTxnBody");
  if (accounts.length === 0) {
    body.innerHTML = `<tr><td colspan="5" class="text-center text-muted" style="padding:30px;">No accounts yet.</td></tr>`;
    return;
  }
  try {
    const all = [];
    for (const acc of accounts) {
      const txns = await API.get(`/accounts/${acc.id}/transactions`);
      all.push(...txns);
    }
    all.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    const top = all.slice(0, 8);

    if (top.length === 0) {
      body.innerHTML = `<tr><td colspan="5" class="text-center text-muted" style="padding:30px;">No transactions yet — make your first deposit.</td></tr>`;
      return;
    }

    body.innerHTML = top.map(t => `
      <tr>
        <td class="text-muted">${formatDate(t.created_at)}</td>
        <td class="mono">${t.ref_id}</td>
        <td><span class="badge badge-${t.type}">${t.type.replace('_', ' ')}</span></td>
        <td class="text-muted">${t.note || '—'}</td>
        <td style="text-align:right;" class="${t.type === 'deposit' || t.type === 'transfer_in' ? 'amt-pos' : 'amt-neg'}">
          ${t.type === 'deposit' || t.type === 'transfer_in' ? '+' : '−'}৳${money(t.amount)}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="5" class="text-center text-muted" style="padding:30px;">Couldn't load transactions.</td></tr>`;
  }
}

// ---- Deposit / Withdraw modal ----
const txnModalOverlay = document.getElementById("txnModalOverlay");
const txnModalTitle = document.getElementById("txnModalTitle");
const txnForm = document.getElementById("txnForm");
const txnError = document.getElementById("txnError");
let txnMode = "deposit";

function openTxnModal(mode) {
  txnMode = mode;
  txnModalTitle.textContent = mode === "deposit" ? "Deposit funds" : "Withdraw funds";
  txnError.classList.remove("show");
  txnForm.reset();
  txnModalOverlay.classList.add("show");
}
document.getElementById("openDeposit").addEventListener("click", () => openTxnModal("deposit"));
document.getElementById("openWithdraw").addEventListener("click", () => openTxnModal("withdraw"));
document.getElementById("txnModalClose").addEventListener("click", () => txnModalOverlay.classList.remove("show"));
txnModalOverlay.addEventListener("click", (e) => { if (e.target === txnModalOverlay) txnModalOverlay.classList.remove("show"); });

txnForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  txnError.classList.remove("show");
  const btn = document.getElementById("txnSubmitBtn");
  btn.disabled = true;
  btn.textContent = "Processing…";

  try {
    const payload = {
      account_id: Number(document.getElementById("txnAccount").value),
      amount: Number(document.getElementById("txnAmount").value),
      note: document.getElementById("txnNote").value || undefined,
    };
    await API.post(`/accounts/${txnMode}`, payload);
    txnModalOverlay.classList.remove("show");
    await loadAccounts();
  } catch (err) {
    txnError.textContent = err.message;
    txnError.classList.add("show");
  } finally {
    btn.disabled = false;
    btn.textContent = "Confirm";
  }
});

// ---- Transfer modal ----
const transferModalOverlay = document.getElementById("transferModalOverlay");
const transferForm = document.getElementById("transferForm");
const transferError = document.getElementById("transferError");

document.getElementById("openTransfer").addEventListener("click", () => {
  transferError.classList.remove("show");
  transferForm.reset();
  transferModalOverlay.classList.add("show");
});
document.getElementById("transferModalClose").addEventListener("click", () => transferModalOverlay.classList.remove("show"));
transferModalOverlay.addEventListener("click", (e) => { if (e.target === transferModalOverlay) transferModalOverlay.classList.remove("show"); });

transferForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  transferError.classList.remove("show");
  const btn = document.getElementById("transferSubmitBtn");
  btn.disabled = true;
  btn.textContent = "Sending…";

  try {
    const payload = {
      from_account_id: Number(document.getElementById("fromAccount").value),
      to_account_number: document.getElementById("toAccountNumber").value.trim(),
      amount: Number(document.getElementById("transferAmount").value),
    };
    await API.post("/accounts/transfer", payload);
    transferModalOverlay.classList.remove("show");
    await loadAccounts();
  } catch (err) {
    transferError.textContent = err.message;
    transferError.classList.add("show");
  } finally {
    btn.disabled = false;
    btn.textContent = "Send transfer";
  }
});

loadAccounts();
