"use strict";

async function refreshOwners() {
  const owners = await call("list_owners");
  state.owners = owners;
  // No owners yet: say so and offer the action, matching the grave empty state.
  if (owners.length === 0) {
    el("ownerList").innerHTML = `
      <li class="owner-empty">
        <div class="sec-name">No owners recorded yet</div>
        <div class="sec-meta"><span>Plots can be filed under an owner.</span></div>
        <button class="btn small primary" data-add-owner>Add owner</button>
      </li>`;
    return;
  }
  el("ownerList").innerHTML = `<li class="${state.ownerId === null ? "active" : ""}" data-owner-id="">
      <div class="sec-name">All owners</div>
      <div class="sec-meta"><span>Show every plot</span></div></li>` +
    owners.map((o) => `
    <li class="${state.ownerId === o.id ? "active" : ""}" data-owner-id="${o.id}">
      <button class="btn link sec-edit" data-edit-owner="${o.id}">edit</button>
      <div class="sec-name">${esc(o.name)}</div>
      <div class="sec-meta">
        <span>${plural(o.grave_count, "plot")}</span>
        <span>${esc(o.contact || "")}</span>
      </div>
    </li>`).join("");
}

function openOwnerModal(owner) {
  el("ownerModalTitle").textContent = owner ? "Edit Owner" : "Add Owner";
  el("ownerId").value = owner ? owner.id : "";
  el("ownerName").value = owner ? owner.name : "";
  el("ownerContact").value = owner ? owner.contact || "" : "";
  el("ownerAddress").value = owner ? owner.address || "" : "";
  el("ownerNotes").value = owner ? owner.notes || "" : "";
  el("deleteOwnerBtn").hidden = !owner;
  show("ownerModal");
}

el("ownerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = el("ownerId").value;
  const args = [el("ownerName").value, el("ownerContact").value,
                el("ownerAddress").value, el("ownerNotes").value];
  let newId = null;
  if (id) await call("update_owner", Number(id), ...args);
  else newId = await call("create_owner", ...args);
  hide("ownerModal");
  toast("Owner saved");
  await refreshOwners();
  // Opened from the grave form: hand the new owner straight back to it.
  // `fillOwnerOptions` arrives in Task 6, so this is guarded — between Task 5
  // and Task 6 the inline path simply does nothing rather than throwing.
  if (newId && state.ownerReturnsToGrave) {
    state.ownerReturnsToGrave = false;
    if (typeof fillOwnerOptions === "function") fillOwnerOptions(newId);
  }
  await refreshAll();
});

el("deleteOwnerBtn").addEventListener("click", async () => {
  const id = Number(el("ownerId").value);
  if (!confirm("Delete this owner?")) return;
  await call("delete_owner", id);   // refused by the API if they hold plots
  hide("ownerModal");
  toast("Owner deleted");
  if (state.ownerId === id) state.ownerId = null;
  await refreshOwners();
  await refreshAll();
});

function setTab(name) {
  state.tab = name;
  document.querySelectorAll(".tab").forEach(
    (t) => t.classList.toggle("active", t.dataset.tab === name));
  el("sectionList").hidden = name !== "sections";
  el("ownerList").hidden = name !== "owners";
  el("addSectionBtn").hidden = name !== "sections";
  el("addOwnerBtn").hidden = name !== "owners";
}
