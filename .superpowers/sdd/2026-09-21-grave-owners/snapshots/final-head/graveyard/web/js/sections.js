"use strict";

async function refreshSections() {
  state.sections = await call("list_sections");
  const list = el("sectionList");
  const all = `<li class="${state.sectionId === null ? "active" : ""}" data-id="">
      <div class="sec-name">All sections</div>
      <div class="sec-meta"><span>Show every plot</span></div></li>`;
  list.innerHTML = all + state.sections.map((s) => `
    <li class="${state.sectionId === s.id ? "active" : ""}" data-id="${s.id}">
      <button class="btn link sec-edit" data-edit-section="${s.id}">edit</button>
      <button class="btn link sec-edit" data-docs-section="${s.id}">docs${docBadge(s.doc_count)}</button>
      <div class="sec-name">${esc(s.code)} · ${esc(s.name)}</div>
      <div class="sec-meta">
        <span>${s.total_plots} plots</span>
        <span>${s.available_plots || 0} free</span>
      </div>
    </li>`).join("");
}

/* ---------- Section modal ---------- */

function openSectionModal(section) {
  el("sectionModalTitle").textContent = section ? "Edit Section" : "Add Section";
  el("sectionId").value = section ? section.id : "";
  el("sectionCode").value = section ? section.code : "";
  el("sectionName").value = section ? section.name : "";
  el("sectionDesc").value = section ? section.description || "" : "";
  show("sectionModal");
}

el("sectionForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = el("sectionId").value;
  const args = [el("sectionCode").value, el("sectionName").value, el("sectionDesc").value];
  const wasFirstSection = !id && state.sections.length === 0;
  let newId = null;
  if (id) await call("update_section", Number(id), ...args);
  else newId = await call("create_section", ...args);
  hide("sectionModal");
  toast("Section saved");
  // The first section ever created is the start of the setup flow, not the end
  // of it: select it and go straight on to entering plots.
  if (wasFirstSection && newId) state.sectionId = newId;
  await refreshAll();
  if (wasFirstSection && newId) await openGraveModal(null);
});

/* A plot cannot exist without a section, so say why and open the form that
 * fixes it rather than leaving the user with a toast and no next step. */
function promptForFirstSection() {
  toast("Create a section first — every plot belongs to one", true);
  openSectionModal(null);
}
