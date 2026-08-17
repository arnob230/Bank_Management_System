requireAdmin();

const user = API.user();
document.getElementById("userName").textContent = user.full_name;
document.getElementById("userRole").textContent = user.role;
document.getElementById("userInitials").textContent = initials(user.full_name);
document.getElementById("logoutBtn").addEventListener("click", (e) => {
  e.preventDefault();
  API.clearSession();
  window.location.href = "/index.html";
});

async function loadStats() {
  const s = await API.get("/admin/stats");
  document.getElementById("statCustomers").textContent = s.total_customers;
  document.getElementById("statAccounts").textContent = s.total_accounts;
  document.getElementById("statDeposits").textContent = "৳" + money(s.total_deposits);
  document.getElementById("statTxns").textContent = s.txns_today;
  document.getElementById("statLoans").textContent = s.pending_loans;
}

async function loadCustomers(q = "") {
  const body = document.getElementById("customerBody");
  const list = await API.get("/admin/customers" + (q ? `?q=${encodeURIComponent(q)}` : ""));
  if (list.length === 0) {
    body.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding:30px;">No customers found.</td></tr>`;
    return;
  }
  body.innerHTML = list.map(c => `
    <tr>
      <td style="font-weight:600;">${c.full_name}</td>
      <td class="text-muted">${c.email}</td>
      <td class="text-muted">${c.phone}</td>
      <td class="text-muted">${formatDate(c.created_at)}</td>
      <td><span class="badge badge-${c.status}">${c.status}</span></td>
      <td>
        ${c.status !== 'frozen' ? `<button class="btn btn-ghost btn-sm" onclick="setStatus(${c.id}, 'frozen')">Freeze</button>` : `<button class="btn btn-ghost btn-sm" onclick="setStatus(${c.id}, 'active')">Unfreeze</button>`}
      </td>
    </tr>
  `).join("");
}

async function setStatus(userId, status) {
  await API.post(`/admin/customers/${userId}/status`, { status });
  loadCustomers(document.getElementById("customerSearch").value);
}
window.setStatus = setStatus;

let searchTimer;
document.getElementById("customerSearch").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadCustomers(e.target.value), 300);
});

async function loadLoans() {
  const body = document.getElementById("loanBody");
  const loans = await API.get("/admin/loans");
  if (loans.length === 0) {
    body.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding:30px;">No loan applications yet.</td></tr>`;
    return;
  }
  body.innerHTML = loans.map(l => `
    <tr>
      <td>${l.full_name}<div class="text-muted" style="font-size:12px;">${l.email}</div></td>
      <td class="mono">৳${money(l.amount)}</td>
      <td>${l.term_months} mo</td>
      <td class="mono">৳${money(l.monthly_emi)}</td>
      <td><span class="badge badge-${l.status}">${l.status}</span></td>
      <td>
        ${l.status === 'pending' ? `
          <button class="btn btn-primary btn-sm" onclick="decideLoan(${l.id}, 'approved')">Approve</button>
          <button class="btn btn-danger btn-sm" onclick="decideLoan(${l.id}, 'rejected')">Reject</button>
        ` : ''}
      </td>
    </tr>
  `).join("");
}

async function decideLoan(loanId, decision) {
  await API.post(`/admin/loans/${loanId}/decision`, { decision });
  loadLoans();
  loadStats();
}
window.decideLoan = decideLoan;

loadStats();
loadCustomers();
loadLoans();
