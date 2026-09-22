"use strict";

/* ---------- Global event delegation ---------- */

/* The owner modal can be dismissed (Cancel or backdrop click) instead of
 * saved. Without this, a flag set by "+ New owner..." on the grave form
 * would survive the cancel and get consumed by some later, unrelated owner
 * save elsewhere in the app. Not cleared inside openOwnerModal itself: the
 * grave-form path sets the flag and *then* calls openOwnerModal(null), so
 * clearing on open would wipe the flag it just set. */
function clearOwnerReturnOnDismiss(modal) {
  if (modal && modal.id === "ownerModal") state.ownerReturnsToGrave = false;
}

document.addEventListener("click", async (e) => {
  const t = e.target;

  // Close only the modal that was clicked: the documents modal can sit on top
  // of the grave detail modal, which should survive it.
  if (t.dataset.close !== undefined) {
    clearOwnerReturnOnDismiss(t.closest(".modal-backdrop"));
    closeModalAround(t);
    return;
  }
  if (t.classList.contains("modal-backdrop")) {
    clearOwnerReturnOnDismiss(t);
    t.hidden = true;
    return;
  }

  // Empty-state calls to action
  if (t.dataset.onboardSection !== undefined) { openSectionModal(null); return; }
  if (t.dataset.onboardGrave !== undefined) { await openGraveModal(null); return; }
  if (t.dataset.clearFilters !== undefined) {
    state.sectionId = null;
    state.status = "";
    state.search = "";
    el("statusFilter").value = "";
    el("searchInput").value = "";
    await refreshSections();
    await refreshGraves();
    return;
  }

  // Documents
  if (t.dataset.docsSection) {
    const s = state.sections.find((x) => x.id === Number(t.dataset.docsSection));
    await openDocuments("section", Number(t.dataset.docsSection),
      s ? `${s.code} · ${s.name}` : "Section");
    return;
  }
  if (t.dataset.docsGrave) {
    const g = await call("get_grave", Number(t.dataset.docsGrave));
    await openDocuments("grave", g.id, `${g.section_code} · Plot ${g.plot_number}`);
    return;
  }
  if (t.dataset.docsBurial) {
    await openDocuments("burial", Number(t.dataset.docsBurial), "Burial record");
    return;
  }
  if (t.dataset.docOpen) {
    await call("open_document", Number(t.dataset.docOpen));
    return;
  }
  if (t.dataset.docDel) {
    if (confirm("Remove this document? The file is deleted from the store.")) {
      await call("delete_document", Number(t.dataset.docDel));
      toast("Document removed");
      await refreshDocuments();
      await refreshAll();
    }
    return;
  }

  // Section row / edit
  if (t.dataset.editSection) {
    const s = state.sections.find((x) => x.id === Number(t.dataset.editSection));
    openSectionModal(s);
    return;
  }
  if (t.dataset.tab) { setTab(t.dataset.tab); return; }
  if (t.dataset.addOwner !== undefined) { openOwnerModal(null); return; }
  if (t.dataset.editOwner) {
    const o = await call("get_owner", Number(t.dataset.editOwner));
    openOwnerModal(o);
    return;
  }
  const ownerLi = t.closest("li[data-owner-id]");
  if (ownerLi) {
    state.ownerId = ownerLi.dataset.ownerId ? Number(ownerLi.dataset.ownerId) : null;
    state.sectionId = null;   // the two filters are mutually exclusive
    await refreshOwners();
    await refreshSections();
    await refreshGraves();
    return;
  }

  const li = t.closest("li[data-id]");
  if (li) {
    state.sectionId = li.dataset.id ? Number(li.dataset.id) : null;
    state.ownerId = null;
    await refreshSections();
    await refreshOwners();
    await refreshGraves();
    return;
  }

  // Grave actions
  if (t.dataset.detail) return void openDetail(Number(t.dataset.detail));
  if (t.dataset.edit) {
    const g = await call("get_grave", Number(t.dataset.edit));
    openGraveModal(g);
    return;
  }
  if (t.dataset.del) {
    if (await confirmDelete("grave", Number(t.dataset.del), "this plot")) {
      await call("delete_grave", Number(t.dataset.del));
      toast("Grave deleted");
      await refreshAll();
    }
    return;
  }
  if (t.dataset.delBurial) {
    if (await confirmDelete("burial", Number(t.dataset.delBurial), "this burial record")) {
      await call("delete_burial", Number(t.dataset.delBurial));
      await openDetail(Number(el("burialGraveId").value));
      await refreshAll();
    }
    return;
  }
});

el("addSectionBtn").addEventListener("click", () => openSectionModal(null));
el("addOwnerBtn").addEventListener("click", () => openOwnerModal(null));
el("addGraveBtn").addEventListener("click", () => {
  if (state.sections.length === 0) return promptForFirstSection();
  openGraveModal(null);
});

el("searchInput").addEventListener("input", debounce((e) => {
  state.search = e.target.value;
  refreshGraves();
}, 200));
el("statusFilter").addEventListener("change", (e) => {
  state.status = e.target.value;
  refreshGraves();
});

/* pywebview injects its API asynchronously. Load as soon as it is available —
 * handle the case where `pywebviewready` already fired before this script ran. */
function start() { refreshAll().catch((e) => console.error(e)); }
if (window.pywebview && window.pywebview.api) start();
else window.addEventListener("pywebviewready", start);
