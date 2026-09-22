"use strict";

async function refreshGraves() {
  const graves = await call("list_graves", state.sectionId, state.status,
                            state.search, state.ownerId);
  const body = el("graveBody");
  body.innerHTML = graves.map((g) => `
    <tr>
      <td>${esc(g.section_code)}</td>
      <td>${esc(g.plot_number)}</td>
      <td><span class="badge ${g.status}">${g.status}</span></td>
      <td>${esc(g.owner_name || "—")}</td>
      <td>${esc(g.owner_contact || "—")}</td>
      <td class="actions-col">
        <button class="btn link" data-docs-grave="${g.id}">Docs${docBadge(g.doc_count)}</button>
        <button class="btn link" data-detail="${g.id}">Burials</button>
        <button class="btn link" data-edit="${g.id}">Edit</button>
        <button class="btn link danger" data-del="${g.id}">Delete</button>
      </td>
    </tr>`).join("");
  renderEmptyState(graves.length);
}

/* ---------- Grave modal ---------- */

function sectionOptions(selectedId) {
  // With "All sections" active selectedId is null, so fall back explicitly to
  // the first section rather than letting the browser pick one silently.
  const target = selectedId ?? (state.sections[0] && state.sections[0].id);
  return state.sections.map((s) =>
    `<option value="${s.id}" ${s.id === target ? "selected" : ""}>${esc(s.code)} · ${esc(s.name)}</option>`
  ).join("");
}

async function openGraveModal(grave) {
  // Always reload sections first so the dropdown can never offer a stale /
  // deleted section id (which would fail the DB foreign-key constraint).
  await refreshSections();
  if (state.sections.length === 0) { promptForFirstSection(); return; }
  el("graveModalTitle").textContent = grave ? "Edit Grave" : "Add Grave";
  el("graveSection").innerHTML = sectionOptions(grave ? grave.section_id : state.sectionId);
  el("graveId").value = grave ? grave.id : "";
  el("gravePlot").value = grave ? grave.plot_number : "";
  el("graveStatus").value = grave ? grave.status : "available";
  el("graveOwner").value = grave ? grave.owner_name || "" : "";
  el("graveContact").value = grave ? grave.owner_contact || "" : "";
  el("graveNotes").value = grave ? grave.notes || "" : "";
  el("graveRef").value = grave ? grave.grave_ref || "" : "";
  el("graveDeed").value = grave ? grave.deed_id || "" : "";
  el("gravePurchased").value = grave ? grave.date_purchased || "" : "";
  show("graveModal");
}

el("graveForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = el("graveId").value;
  const section = Number(el("graveSection").value);
  if (!section) { toast("Please choose a section", true); return; }
  // Order must match create_grave / update_grave in api.py.
  const common = [
    el("gravePlot").value,
    el("graveStatus").value,
    el("graveOwner").value,
    el("graveContact").value,
    el("graveNotes").value,
    el("graveRef").value,
    el("graveDeed").value,
    el("gravePurchased").value,
  ];
  if (id) await call("update_grave", Number(id), section, ...common);
  else await call("create_grave", section, ...common);
  hide("graveModal");
  toast("Grave saved");
  await refreshAll();
});

/* ---------- Detail / burials modal ---------- */

async function openDetail(graveId) {
  const g = await call("get_grave", graveId);
  el("detailTitle").textContent = `${g.section_code} · Plot ${g.plot_number}`;
  el("detailMeta").innerHTML = `
    <div><span>Status:</span> <span class="badge ${g.status}">${g.status}</span></div>
    <div><span>Owner:</span> ${esc(g.owner_name || "—")} ${g.owner_contact ? "(" + esc(g.owner_contact) + ")" : ""}</div>
    <div><span>Grave id:</span> ${esc(g.grave_ref || "—")}</div>
    <div><span>Deed id:</span> ${esc(g.deed_id || "—")}</div>
    <div><span>Purchased:</span> ${esc(g.date_purchased || "—")}</div>
    <div><span>Notes:</span> ${esc(g.notes || "—")}</div>`;
  el("burialGraveId").value = g.id;
  renderBurials(g.burials);
  el("burialForm").reset();
  el("burialGraveId").value = g.id;
  show("detailModal");
}

function renderBurials(burials) {
  el("burialBody").innerHTML = burials.length
    ? burials.map((b) => `
      <tr>
        <td>${esc(b.deceased_name)}</td>
        <td>${esc(b.date_of_death || "—")}</td>
        <td>${esc(b.date_of_burial || "—")}</td>
        <td>${esc(b.notes || "")}</td>
        <td class="actions-col">
          <button class="btn link" data-docs-burial="${b.id}">docs${docBadge(b.doc_count)}</button>
          <button class="btn link danger" data-del-burial="${b.id}">remove</button>
        </td>
      </tr>`).join("")
    : `<tr><td colspan="5" class="empty">No burials recorded.</td></tr>`;
}

el("burialForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const graveId = Number(el("burialGraveId").value);
  await call("add_burial", graveId, el("burialName").value,
    el("burialDeath").value, el("burialBurial").value, el("burialNotes").value);
  toast("Burial recorded — grave marked occupied");
  await openDetail(graveId);
  await refreshAll();
});
