# Review package: task-1

No git in this project: this diff is snapshot-to-snapshot,
base `task-1-base` -> current working tree.

## Files changed

- graveyard/web/index.html
- graveyard/web/js/api.js
- graveyard/web/js/app.js
- graveyard/web/js/documents.js
- graveyard/web/js/graves.js
- graveyard/web/js/sections.js
- graveyard/web/js/state.js
- graveyard/web/js/util.js

## Stat

8 files, +453 / -442 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/index.html C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/index.html
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/index.html	2026-09-20 18:43:30.720909800 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/index.html	2026-09-21 08:22:19.311753100 -0400
@@ -174,6 +174,12 @@
 
   <div class="toast" id="toast" hidden></div>
 
+  <script src="js/util.js"></script>
+  <script src="js/api.js"></script>
+  <script src="js/state.js"></script>
+  <script src="js/sections.js"></script>
+  <script src="js/graves.js"></script>
+  <script src="js/documents.js"></script>
   <script src="js/app.js"></script>
 </body>
 </html>
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/api.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/api.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/api.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/api.js	2026-09-21 08:21:36.371682500 -0400
@@ -0,0 +1,12 @@
+"use strict";
+
+/* Thin wrapper around the Python API that unwraps the {ok, data|error}
+ * envelope and surfaces errors as a toast. */
+async function call(method, ...args) {
+  const res = await window.pywebview.api[method](...args);
+  if (!res.ok) {
+    toast(res.error, true);
+    throw new Error(res.error);
+  }
+  return res.data;
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/app.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/app.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/app.js	2026-09-20 18:43:30.603695000 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/app.js	2026-09-21 08:22:14.947231500 -0400
@@ -1,442 +1,115 @@
-"use strict";
-
-/* Thin wrapper around the Python API that unwraps the {ok, data|error}
- * envelope and surfaces errors as a toast. */
-async function call(method, ...args) {
-  const res = await window.pywebview.api[method](...args);
-  if (!res.ok) {
-    toast(res.error, true);
-    throw new Error(res.error);
-  }
-  return res.data;
-}
-
-const $ = (sel) => document.querySelector(sel);
-const el = (id) => document.getElementById(id);
-
-let state = { sectionId: null, status: "", search: "", sections: [], totalGraves: 0,
-              docOwner: { type: null, id: null, title: "" } };
-
-/* ---------- Rendering ---------- */
-
-async function refreshStats() {
-  const s = await call("stats");
-  // Remembered so the empty state can tell "nothing recorded yet" apart from
-  // "records exist but the filters hide them".
-  state.totalGraves = s.total;
-  el("stats").innerHTML = `
-    <div><b>${s.total}</b>Total plots</div>
-    <div><b>${s.available}</b>Available</div>
-    <div><b>${s.reserved}</b>Reserved</div>
-    <div><b>${s.occupied}</b>Occupied</div>
-    <div><b>${s.sections}</b>Sections</div>`;
-}
-
-async function refreshSections() {
-  state.sections = await call("list_sections");
-  const list = el("sectionList");
-  const all = `<li class="${state.sectionId === null ? "active" : ""}" data-id="">
-      <div class="sec-name">All sections</div>
-      <div class="sec-meta"><span>Show every plot</span></div></li>`;
-  list.innerHTML = all + state.sections.map((s) => `
-    <li class="${state.sectionId === s.id ? "active" : ""}" data-id="${s.id}">
-      <button class="btn link sec-edit" data-edit-section="${s.id}">edit</button>
-      <button class="btn link sec-edit" data-docs-section="${s.id}">docs${docBadge(s.doc_count)}</button>
-      <div class="sec-name">${esc(s.code)} Â· ${esc(s.name)}</div>
-      <div class="sec-meta">
-        <span>${s.total_plots} plots</span>
-        <span>${s.available_plots || 0} free</span>
-      </div>
-    </li>`).join("");
-}
-
-async function refreshGraves() {
-  const graves = await call("list_graves", state.sectionId, state.status, state.search);
-  const body = el("graveBody");
-  body.innerHTML = graves.map((g) => `
-    <tr>
-      <td>${esc(g.section_code)}</td>
-      <td>${esc(g.plot_number)}</td>
-      <td><span class="badge ${g.status}">${g.status}</span></td>
-      <td>${esc(g.owner_name || "â€”")}</td>
-      <td>${esc(g.owner_contact || "â€”")}</td>
-      <td class="actions-col">
-        <button class="btn link" data-docs-grave="${g.id}">Docs${docBadge(g.doc_count)}</button>
-        <button class="btn link" data-detail="${g.id}">Burials</button>
-        <button class="btn link" data-edit="${g.id}">Edit</button>
-        <button class="btn link danger" data-del="${g.id}">Delete</button>
-      </td>
-    </tr>`).join("");
-  renderEmptyState(graves.length);
-}
-
-/* An empty table means one of three different things. Saying which one, and
- * offering the action that resolves it, is the difference between a dead end
- * and a next step. */
-function renderEmptyState(graveCount) {
-  const firstRun = state.sections.length === 0;
-  const box = el("emptyState");
-
-  // On first run there is nothing to search, filter or list yet.
-  el("toolbar").hidden = firstRun;
-  el("graveTable").hidden = firstRun || graveCount === 0;
-
-  if (firstRun) {
-    box.innerHTML = `
-      <h2>Welcome to Grave Inventory</h2>
-      <p>Plots belong to a section, so start by creating one &mdash; for example
-         <b>A &middot; Garden of Peace</b>. You can add plots to it straight after.</p>
-      <button class="btn primary" data-onboard-section>Create first section</button>`;
-  } else if (graveCount > 0) {
-    box.hidden = true;
-    return;
-  } else if (state.totalGraves > 0) {
-    box.innerHTML = `
-      <p>No graves match the current filters.</p>
-      <button class="btn" data-clear-filters>Clear filters</button>`;
-  } else {
-    box.innerHTML = `
-      <p>No plots recorded yet.</p>
-      <button class="btn primary" data-onboard-grave>Add the first grave</button>`;
-  }
-  box.hidden = false;
-}
-
-async function refreshAll() {
-  // Sections must land before graves: the empty state can only choose its
-  // message once it knows whether any section exists.
-  await Promise.all([refreshStats(), refreshSections()]);
-  await refreshGraves();
-}
-
-/* ---------- Section modal ---------- */
-
-function openSectionModal(section) {
-  el("sectionModalTitle").textContent = section ? "Edit Section" : "Add Section";
-  el("sectionId").value = section ? section.id : "";
-  el("sectionCode").value = section ? section.code : "";
-  el("sectionName").value = section ? section.name : "";
-  el("sectionDesc").value = section ? section.description || "" : "";
-  show("sectionModal");
-}
-
-el("sectionForm").addEventListener("submit", async (e) => {
-  e.preventDefault();
-  const id = el("sectionId").value;
-  const args = [el("sectionCode").value, el("sectionName").value, el("sectionDesc").value];
-  const wasFirstSection = !id && state.sections.length === 0;
-  let newId = null;
-  if (id) await call("update_section", Number(id), ...args);
-  else newId = await call("create_section", ...args);
-  hide("sectionModal");
-  toast("Section saved");
-  // The first section ever created is the start of the setup flow, not the end
-  // of it: select it and go straight on to entering plots.
-  if (wasFirstSection && newId) state.sectionId = newId;
-  await refreshAll();
-  if (wasFirstSection && newId) await openGraveModal(null);
-});
-
-/* ---------- Grave modal ---------- */
-
-function sectionOptions(selectedId) {
-  // With "All sections" active selectedId is null, so fall back explicitly to
-  // the first section rather than letting the browser pick one silently.
-  const target = selectedId ?? (state.sections[0] && state.sections[0].id);
-  return state.sections.map((s) =>
-    `<option value="${s.id}" ${s.id === target ? "selected" : ""}>${esc(s.code)} Â· ${esc(s.name)}</option>`
-  ).join("");
-}
-
-async function openGraveModal(grave) {
-  // Always reload sections first so the dropdown can never offer a stale /
-  // deleted section id (which would fail the DB foreign-key constraint).
-  await refreshSections();
-  if (state.sections.length === 0) { promptForFirstSection(); return; }
-  el("graveModalTitle").textContent = grave ? "Edit Grave" : "Add Grave";
-  el("graveSection").innerHTML = sectionOptions(grave ? grave.section_id : state.sectionId);
-  el("graveId").value = grave ? grave.id : "";
-  el("gravePlot").value = grave ? grave.plot_number : "";
-  el("graveStatus").value = grave ? grave.status : "available";
-  el("graveOwner").value = grave ? grave.owner_name || "" : "";
-  el("graveContact").value = grave ? grave.owner_contact || "" : "";
-  el("graveNotes").value = grave ? grave.notes || "" : "";
-  el("graveRef").value = grave ? grave.grave_ref || "" : "";
-  el("graveDeed").value = grave ? grave.deed_id || "" : "";
-  el("gravePurchased").value = grave ? grave.date_purchased || "" : "";
-  show("graveModal");
-}
-
-el("graveForm").addEventListener("submit", async (e) => {
-  e.preventDefault();
-  const id = el("graveId").value;
-  const section = Number(el("graveSection").value);
-  if (!section) { toast("Please choose a section", true); return; }
-  // Order must match create_grave / update_grave in api.py.
-  const common = [
-    el("gravePlot").value,
-    el("graveStatus").value,
-    el("graveOwner").value,
-    el("graveContact").value,
-    el("graveNotes").value,
-    el("graveRef").value,
-    el("graveDeed").value,
-    el("gravePurchased").value,
-  ];
-  if (id) await call("update_grave", Number(id), section, ...common);
-  else await call("create_grave", section, ...common);
-  hide("graveModal");
-  toast("Grave saved");
-  await refreshAll();
-});
-
-/* ---------- Detail / burials modal ---------- */
-
-async function openDetail(graveId) {
-  const g = await call("get_grave", graveId);
-  el("detailTitle").textContent = `${g.section_code} Â· Plot ${g.plot_number}`;
-  el("detailMeta").innerHTML = `
-    <div><span>Status:</span> <span class="badge ${g.status}">${g.status}</span></div>
-    <div><span>Owner:</span> ${esc(g.owner_name || "â€”")} ${g.owner_contact ? "(" + esc(g.owner_contact) + ")" : ""}</div>
-    <div><span>Grave id:</span> ${esc(g.grave_ref || "â€”")}</div>
-    <div><span>Deed id:</span> ${esc(g.deed_id || "â€”")}</div>
-    <div><span>Purchased:</span> ${esc(g.date_purchased || "â€”")}</div>
-    <div><span>Notes:</span> ${esc(g.notes || "â€”")}</div>`;
-  el("burialGraveId").value = g.id;
-  renderBurials(g.burials);
-  el("burialForm").reset();
-  el("burialGraveId").value = g.id;
-  show("detailModal");
-}
-
-function renderBurials(burials) {
-  el("burialBody").innerHTML = burials.length
-    ? burials.map((b) => `
-      <tr>
-        <td>${esc(b.deceased_name)}</td>
-        <td>${esc(b.date_of_death || "â€”")}</td>
-        <td>${esc(b.date_of_burial || "â€”")}</td>
-        <td>${esc(b.notes || "")}</td>
-        <td class="actions-col">
-          <button class="btn link" data-docs-burial="${b.id}">docs${docBadge(b.doc_count)}</button>
-          <button class="btn link danger" data-del-burial="${b.id}">remove</button>
-        </td>
-      </tr>`).join("")
-    : `<tr><td colspan="5" class="empty">No burials recorded.</td></tr>`;
-}
-
-el("burialForm").addEventListener("submit", async (e) => {
-  e.preventDefault();
-  const graveId = Number(el("burialGraveId").value);
-  await call("add_burial", graveId, el("burialName").value,
-    el("burialDeath").value, el("burialBurial").value, el("burialNotes").value);
-  toast("Burial recorded â€” grave marked occupied");
-  await openDetail(graveId);
-  await refreshAll();
-});
-
-/* ---------- Documents modal ---------- */
-
-/* One modal serves sections, graves and burials; only the owner changes. */
-async function openDocuments(ownerType, ownerId, title) {
-  state.docOwner = { type: ownerType, id: ownerId, title };
-  el("documentsTitle").textContent = `Documents â€” ${title}`;
-  await refreshDocuments();
-  show("documentsModal");
-}
-
-async function refreshDocuments() {
-  const { type, id } = state.docOwner;
-  renderDocuments(await call("list_documents", type, id));
-}
-
-function renderDocuments(docs) {
-  el("documentBody").innerHTML = docs.length
-    ? docs.map((d) => `
-      <tr>
-        <td><button class="doc-name" data-doc-open="${d.id}"
-                    title="Open in the default application">${esc(d.original_name)}</button></td>
-        <td>${fileSize(d.size_bytes)}</td>
-        <td>${esc((d.created_at || "").slice(0, 10))}</td>
-        <td class="actions-col">
-          <button class="btn link danger" data-doc-del="${d.id}">remove</button>
-        </td>
-      </tr>`).join("")
-    : `<tr><td colspan="4" class="empty">No documents attached yet.</td></tr>`;
-}
-
-el("uploadDocBtn").addEventListener("click", async () => {
-  const { type, id } = state.docOwner;
-  // The native picker runs in Python; no file bytes cross this bridge.
-  const added = await call("add_documents", type, id);
-  if (added.length) {
-    toast(`${added.length} document${added.length === 1 ? "" : "s"} attached`);
-    await refreshDocuments();
-    await refreshAll();
-  }
-});
-
-/* ---------- Global event delegation ---------- */
-
-document.addEventListener("click", async (e) => {
-  const t = e.target;
-
-  // Close only the modal that was clicked: the documents modal can sit on top
-  // of the grave detail modal, which should survive it.
-  if (t.dataset.close !== undefined) { closeModalAround(t); return; }
-  if (t.classList.contains("modal-backdrop")) { t.hidden = true; return; }
-
-  // Empty-state calls to action
-  if (t.dataset.onboardSection !== undefined) { openSectionModal(null); return; }
-  if (t.dataset.onboardGrave !== undefined) { await openGraveModal(null); return; }
-  if (t.dataset.clearFilters !== undefined) {
-    state.sectionId = null;
-    state.status = "";
-    state.search = "";
-    el("statusFilter").value = "";
-    el("searchInput").value = "";
-    await refreshSections();
-    await refreshGraves();
-    return;
-  }
-
-  // Documents
-  if (t.dataset.docsSection) {
-    const s = state.sections.find((x) => x.id === Number(t.dataset.docsSection));
-    await openDocuments("section", Number(t.dataset.docsSection),
-      s ? `${s.code} Â· ${s.name}` : "Section");
-    return;
-  }
-  if (t.dataset.docsGrave) {
-    const g = await call("get_grave", Number(t.dataset.docsGrave));
-    await openDocuments("grave", g.id, `${g.section_code} Â· Plot ${g.plot_number}`);
-    return;
-  }
-  if (t.dataset.docsBurial) {
-    await openDocuments("burial", Number(t.dataset.docsBurial), "Burial record");
-    return;
-  }
-  if (t.dataset.docOpen) {
-    await call("open_document", Number(t.dataset.docOpen));
-    return;
-  }
-  if (t.dataset.docDel) {
-    if (confirm("Remove this document? The file is deleted from the store.")) {
-      await call("delete_document", Number(t.dataset.docDel));
-      toast("Document removed");
-      await refreshDocuments();
-      await refreshAll();
-    }
-    return;
-  }
-
-  // Section row / edit
-  if (t.dataset.editSection) {
-    const s = state.sections.find((x) => x.id === Number(t.dataset.editSection));
-    openSectionModal(s);
-    return;
-  }
-  const li = t.closest("li[data-id]");
-  if (li) {
-    state.sectionId = li.dataset.id ? Number(li.dataset.id) : null;
-    await refreshSections();
-    await refreshGraves();
-    return;
-  }
-
-  // Grave actions
-  if (t.dataset.detail) return void openDetail(Number(t.dataset.detail));
-  if (t.dataset.edit) {
-    const g = await call("get_grave", Number(t.dataset.edit));
-    openGraveModal(g);
-    return;
-  }
-  if (t.dataset.del) {
-    if (await confirmDelete("grave", Number(t.dataset.del), "this plot")) {
-      await call("delete_grave", Number(t.dataset.del));
-      toast("Grave deleted");
-      await refreshAll();
-    }
-    return;
-  }
-  if (t.dataset.delBurial) {
-    if (await confirmDelete("burial", Number(t.dataset.delBurial), "this burial record")) {
-      await call("delete_burial", Number(t.dataset.delBurial));
-      await openDetail(Number(el("burialGraveId").value));
-      await refreshAll();
-    }
-    return;
-  }
-});
-
-el("addSectionBtn").addEventListener("click", () => openSectionModal(null));
-el("addGraveBtn").addEventListener("click", () => {
-  if (state.sections.length === 0) return promptForFirstSection();
-  openGraveModal(null);
-});
-
-/* A plot cannot exist without a section, so say why and open the form that
- * fixes it rather than leaving the user with a toast and no next step. */
-function promptForFirstSection() {
-  toast("Create a section first â€” every plot belongs to one", true);
-  openSectionModal(null);
-}
-el("searchInput").addEventListener("input", debounce((e) => {
-  state.search = e.target.value;
-  refreshGraves();
-}, 200));
-el("statusFilter").addEventListener("change", (e) => {
-  state.status = e.target.value;
-  refreshGraves();
-});
-
-/* ---------- Helpers ---------- */
-
-/* Names what a delete takes with it, so attached paperwork is never a surprise. */
-async function confirmDelete(ownerType, id, what) {
-  const c = await call("describe_delete", ownerType, id);
-  const parts = [];
-  if (c.graves) parts.push(plural(c.graves, "plot"));
-  if (c.burials) parts.push(plural(c.burials, "burial record"));
-  if (c.documents) parts.push(plural(c.documents, "document"));
-  const tail = parts.length ? `, along with ${parts.join(", ")}` : "";
-  return confirm(`Delete ${what}${tail}? This cannot be undone.`);
-}
-
-function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }
-function docBadge(n) { return n ? ` (${n})` : ""; }
-function fileSize(bytes) {
-  if (bytes < 1024) return `${bytes} B`;
-  if (bytes < 1048576) return `${Math.round(bytes / 1024)} KB`;
-  return `${(bytes / 1048576).toFixed(1)} MB`;
-}
-
-function show(id) { el(id).hidden = false; }
-function hide(id) { el(id).hidden = true; }
-function closeModalAround(node) {
-  const modal = node.closest(".modal-backdrop");
-  if (modal) modal.hidden = true;
-}
-function esc(s) {
-  return String(s).replace(/[&<>"']/g, (c) =>
-    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
-}
-function debounce(fn, ms) {
-  let h;
-  return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); };
-}
-let toastTimer;
-function toast(msg, isError = false) {
-  const t = el("toast");
-  t.textContent = msg;
-  t.className = "toast" + (isError ? " error" : "");
-  t.hidden = false;
-  clearTimeout(toastTimer);
-  toastTimer = setTimeout(() => (t.hidden = true), 3000);
-}
-
-/* pywebview injects its API asynchronously. Load as soon as it is available â€”
- * handle the case where `pywebviewready` already fired before this script ran. */
-function start() { refreshAll().catch((e) => console.error(e)); }
-if (window.pywebview && window.pywebview.api) start();
-else window.addEventListener("pywebviewready", start);
+"use strict";
+
+/* ---------- Global event delegation ---------- */
+
+document.addEventListener("click", async (e) => {
+  const t = e.target;
+
+  // Close only the modal that was clicked: the documents modal can sit on top
+  // of the grave detail modal, which should survive it.
+  if (t.dataset.close !== undefined) { closeModalAround(t); return; }
+  if (t.classList.contains("modal-backdrop")) { t.hidden = true; return; }
+
+  // Empty-state calls to action
+  if (t.dataset.onboardSection !== undefined) { openSectionModal(null); return; }
+  if (t.dataset.onboardGrave !== undefined) { await openGraveModal(null); return; }
+  if (t.dataset.clearFilters !== undefined) {
+    state.sectionId = null;
+    state.status = "";
+    state.search = "";
+    el("statusFilter").value = "";
+    el("searchInput").value = "";
+    await refreshSections();
+    await refreshGraves();
+    return;
+  }
+
+  // Documents
+  if (t.dataset.docsSection) {
+    const s = state.sections.find((x) => x.id === Number(t.dataset.docsSection));
+    await openDocuments("section", Number(t.dataset.docsSection),
+      s ? `${s.code} Â· ${s.name}` : "Section");
+    return;
+  }
+  if (t.dataset.docsGrave) {
+    const g = await call("get_grave", Number(t.dataset.docsGrave));
+    await openDocuments("grave", g.id, `${g.section_code} Â· Plot ${g.plot_number}`);
+    return;
+  }
+  if (t.dataset.docsBurial) {
+    await openDocuments("burial", Number(t.dataset.docsBurial), "Burial record");
+    return;
+  }
+  if (t.dataset.docOpen) {
+    await call("open_document", Number(t.dataset.docOpen));
+    return;
+  }
+  if (t.dataset.docDel) {
+    if (confirm("Remove this document? The file is deleted from the store.")) {
+      await call("delete_document", Number(t.dataset.docDel));
+      toast("Document removed");
+      await refreshDocuments();
+      await refreshAll();
+    }
+    return;
+  }
+
+  // Section row / edit
+  if (t.dataset.editSection) {
+    const s = state.sections.find((x) => x.id === Number(t.dataset.editSection));
+    openSectionModal(s);
+    return;
+  }
+  const li = t.closest("li[data-id]");
+  if (li) {
+    state.sectionId = li.dataset.id ? Number(li.dataset.id) : null;
+    await refreshSections();
+    await refreshGraves();
+    return;
+  }
+
+  // Grave actions
+  if (t.dataset.detail) return void openDetail(Number(t.dataset.detail));
+  if (t.dataset.edit) {
+    const g = await call("get_grave", Number(t.dataset.edit));
+    openGraveModal(g);
+    return;
+  }
+  if (t.dataset.del) {
+    if (await confirmDelete("grave", Number(t.dataset.del), "this plot")) {
+      await call("delete_grave", Number(t.dataset.del));
+      toast("Grave deleted");
+      await refreshAll();
+    }
+    return;
+  }
+  if (t.dataset.delBurial) {
+    if (await confirmDelete("burial", Number(t.dataset.delBurial), "this burial record")) {
+      await call("delete_burial", Number(t.dataset.delBurial));
+      await openDetail(Number(el("burialGraveId").value));
+      await refreshAll();
+    }
+    return;
+  }
+});
+
+el("addSectionBtn").addEventListener("click", () => openSectionModal(null));
+el("addGraveBtn").addEventListener("click", () => {
+  if (state.sections.length === 0) return promptForFirstSection();
+  openGraveModal(null);
+});
+
+el("searchInput").addEventListener("input", debounce((e) => {
+  state.search = e.target.value;
+  refreshGraves();
+}, 200));
+el("statusFilter").addEventListener("change", (e) => {
+  state.status = e.target.value;
+  refreshGraves();
+});
+
+/* pywebview injects its API asynchronously. Load as soon as it is available â€”
+ * handle the case where `pywebviewready` already fired before this script ran. */
+function start() { refreshAll().catch((e) => console.error(e)); }
+if (window.pywebview && window.pywebview.api) start();
+else window.addEventListener("pywebviewready", start);
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/documents.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/documents.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/documents.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/documents.js	2026-09-21 08:22:05.634806400 -0400
@@ -0,0 +1,42 @@
+"use strict";
+
+/* ---------- Documents modal ---------- */
+
+/* One modal serves sections, graves and burials; only the owner changes. */
+async function openDocuments(ownerType, ownerId, title) {
+  state.docOwner = { type: ownerType, id: ownerId, title };
+  el("documentsTitle").textContent = `Documents â€” ${title}`;
+  await refreshDocuments();
+  show("documentsModal");
+}
+
+async function refreshDocuments() {
+  const { type, id } = state.docOwner;
+  renderDocuments(await call("list_documents", type, id));
+}
+
+function renderDocuments(docs) {
+  el("documentBody").innerHTML = docs.length
+    ? docs.map((d) => `
+      <tr>
+        <td><button class="doc-name" data-doc-open="${d.id}"
+                    title="Open in the default application">${esc(d.original_name)}</button></td>
+        <td>${fileSize(d.size_bytes)}</td>
+        <td>${esc((d.created_at || "").slice(0, 10))}</td>
+        <td class="actions-col">
+          <button class="btn link danger" data-doc-del="${d.id}">remove</button>
+        </td>
+      </tr>`).join("")
+    : `<tr><td colspan="4" class="empty">No documents attached yet.</td></tr>`;
+}
+
+el("uploadDocBtn").addEventListener("click", async () => {
+  const { type, id } = state.docOwner;
+  // The native picker runs in Python; no file bytes cross this bridge.
+  const added = await call("add_documents", type, id);
+  if (added.length) {
+    toast(`${added.length} document${added.length === 1 ? "" : "s"} attached`);
+    await refreshDocuments();
+    await refreshAll();
+  }
+});
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/graves.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/graves.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/graves.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/graves.js	2026-09-21 08:22:01.540701100 -0400
@@ -0,0 +1,119 @@
+"use strict";
+
+async function refreshGraves() {
+  const graves = await call("list_graves", state.sectionId, state.status, state.search);
+  const body = el("graveBody");
+  body.innerHTML = graves.map((g) => `
+    <tr>
+      <td>${esc(g.section_code)}</td>
+      <td>${esc(g.plot_number)}</td>
+      <td><span class="badge ${g.status}">${g.status}</span></td>
+      <td>${esc(g.owner_name || "â€”")}</td>
+      <td>${esc(g.owner_contact || "â€”")}</td>
+      <td class="actions-col">
+        <button class="btn link" data-docs-grave="${g.id}">Docs${docBadge(g.doc_count)}</button>
+        <button class="btn link" data-detail="${g.id}">Burials</button>
+        <button class="btn link" data-edit="${g.id}">Edit</button>
+        <button class="btn link danger" data-del="${g.id}">Delete</button>
+      </td>
+    </tr>`).join("");
+  renderEmptyState(graves.length);
+}
+
+/* ---------- Grave modal ---------- */
+
+function sectionOptions(selectedId) {
+  // With "All sections" active selectedId is null, so fall back explicitly to
+  // the first section rather than letting the browser pick one silently.
+  const target = selectedId ?? (state.sections[0] && state.sections[0].id);
+  return state.sections.map((s) =>
+    `<option value="${s.id}" ${s.id === target ? "selected" : ""}>${esc(s.code)} Â· ${esc(s.name)}</option>`
+  ).join("");
+}
+
+async function openGraveModal(grave) {
+  // Always reload sections first so the dropdown can never offer a stale /
+  // deleted section id (which would fail the DB foreign-key constraint).
+  await refreshSections();
+  if (state.sections.length === 0) { promptForFirstSection(); return; }
+  el("graveModalTitle").textContent = grave ? "Edit Grave" : "Add Grave";
+  el("graveSection").innerHTML = sectionOptions(grave ? grave.section_id : state.sectionId);
+  el("graveId").value = grave ? grave.id : "";
+  el("gravePlot").value = grave ? grave.plot_number : "";
+  el("graveStatus").value = grave ? grave.status : "available";
+  el("graveOwner").value = grave ? grave.owner_name || "" : "";
+  el("graveContact").value = grave ? grave.owner_contact || "" : "";
+  el("graveNotes").value = grave ? grave.notes || "" : "";
+  el("graveRef").value = grave ? grave.grave_ref || "" : "";
+  el("graveDeed").value = grave ? grave.deed_id || "" : "";
+  el("gravePurchased").value = grave ? grave.date_purchased || "" : "";
+  show("graveModal");
+}
+
+el("graveForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const id = el("graveId").value;
+  const section = Number(el("graveSection").value);
+  if (!section) { toast("Please choose a section", true); return; }
+  // Order must match create_grave / update_grave in api.py.
+  const common = [
+    el("gravePlot").value,
+    el("graveStatus").value,
+    el("graveOwner").value,
+    el("graveContact").value,
+    el("graveNotes").value,
+    el("graveRef").value,
+    el("graveDeed").value,
+    el("gravePurchased").value,
+  ];
+  if (id) await call("update_grave", Number(id), section, ...common);
+  else await call("create_grave", section, ...common);
+  hide("graveModal");
+  toast("Grave saved");
+  await refreshAll();
+});
+
+/* ---------- Detail / burials modal ---------- */
+
+async function openDetail(graveId) {
+  const g = await call("get_grave", graveId);
+  el("detailTitle").textContent = `${g.section_code} Â· Plot ${g.plot_number}`;
+  el("detailMeta").innerHTML = `
+    <div><span>Status:</span> <span class="badge ${g.status}">${g.status}</span></div>
+    <div><span>Owner:</span> ${esc(g.owner_name || "â€”")} ${g.owner_contact ? "(" + esc(g.owner_contact) + ")" : ""}</div>
+    <div><span>Grave id:</span> ${esc(g.grave_ref || "â€”")}</div>
+    <div><span>Deed id:</span> ${esc(g.deed_id || "â€”")}</div>
+    <div><span>Purchased:</span> ${esc(g.date_purchased || "â€”")}</div>
+    <div><span>Notes:</span> ${esc(g.notes || "â€”")}</div>`;
+  el("burialGraveId").value = g.id;
+  renderBurials(g.burials);
+  el("burialForm").reset();
+  el("burialGraveId").value = g.id;
+  show("detailModal");
+}
+
+function renderBurials(burials) {
+  el("burialBody").innerHTML = burials.length
+    ? burials.map((b) => `
+      <tr>
+        <td>${esc(b.deceased_name)}</td>
+        <td>${esc(b.date_of_death || "â€”")}</td>
+        <td>${esc(b.date_of_burial || "â€”")}</td>
+        <td>${esc(b.notes || "")}</td>
+        <td class="actions-col">
+          <button class="btn link" data-docs-burial="${b.id}">docs${docBadge(b.doc_count)}</button>
+          <button class="btn link danger" data-del-burial="${b.id}">remove</button>
+        </td>
+      </tr>`).join("")
+    : `<tr><td colspan="5" class="empty">No burials recorded.</td></tr>`;
+}
+
+el("burialForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const graveId = Number(el("burialGraveId").value);
+  await call("add_burial", graveId, el("burialName").value,
+    el("burialDeath").value, el("burialBurial").value, el("burialNotes").value);
+  toast("Burial recorded â€” grave marked occupied");
+  await openDetail(graveId);
+  await refreshAll();
+});
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/sections.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/sections.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/sections.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/sections.js	2026-09-21 08:21:48.859446100 -0400
@@ -0,0 +1,54 @@
+"use strict";
+
+async function refreshSections() {
+  state.sections = await call("list_sections");
+  const list = el("sectionList");
+  const all = `<li class="${state.sectionId === null ? "active" : ""}" data-id="">
+      <div class="sec-name">All sections</div>
+      <div class="sec-meta"><span>Show every plot</span></div></li>`;
+  list.innerHTML = all + state.sections.map((s) => `
+    <li class="${state.sectionId === s.id ? "active" : ""}" data-id="${s.id}">
+      <button class="btn link sec-edit" data-edit-section="${s.id}">edit</button>
+      <button class="btn link sec-edit" data-docs-section="${s.id}">docs${docBadge(s.doc_count)}</button>
+      <div class="sec-name">${esc(s.code)} Â· ${esc(s.name)}</div>
+      <div class="sec-meta">
+        <span>${s.total_plots} plots</span>
+        <span>${s.available_plots || 0} free</span>
+      </div>
+    </li>`).join("");
+}
+
+/* ---------- Section modal ---------- */
+
+function openSectionModal(section) {
+  el("sectionModalTitle").textContent = section ? "Edit Section" : "Add Section";
+  el("sectionId").value = section ? section.id : "";
+  el("sectionCode").value = section ? section.code : "";
+  el("sectionName").value = section ? section.name : "";
+  el("sectionDesc").value = section ? section.description || "" : "";
+  show("sectionModal");
+}
+
+el("sectionForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const id = el("sectionId").value;
+  const args = [el("sectionCode").value, el("sectionName").value, el("sectionDesc").value];
+  const wasFirstSection = !id && state.sections.length === 0;
+  let newId = null;
+  if (id) await call("update_section", Number(id), ...args);
+  else newId = await call("create_section", ...args);
+  hide("sectionModal");
+  toast("Section saved");
+  // The first section ever created is the start of the setup flow, not the end
+  // of it: select it and go straight on to entering plots.
+  if (wasFirstSection && newId) state.sectionId = newId;
+  await refreshAll();
+  if (wasFirstSection && newId) await openGraveModal(null);
+});
+
+/* A plot cannot exist without a section, so say why and open the form that
+ * fixes it rather than leaving the user with a toast and no next step. */
+function promptForFirstSection() {
+  toast("Create a section first â€” every plot belongs to one", true);
+  openSectionModal(null);
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/state.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/state.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/state.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/state.js	2026-09-21 08:21:43.089041200 -0400
@@ -0,0 +1,69 @@
+"use strict";
+
+let state = { sectionId: null, status: "", search: "", sections: [], totalGraves: 0,
+              docOwner: { type: null, id: null, title: "" } };
+
+/* ---------- Rendering ---------- */
+
+async function refreshStats() {
+  const s = await call("stats");
+  // Remembered so the empty state can tell "nothing recorded yet" apart from
+  // "records exist but the filters hide them".
+  state.totalGraves = s.total;
+  el("stats").innerHTML = `
+    <div><b>${s.total}</b>Total plots</div>
+    <div><b>${s.available}</b>Available</div>
+    <div><b>${s.reserved}</b>Reserved</div>
+    <div><b>${s.occupied}</b>Occupied</div>
+    <div><b>${s.sections}</b>Sections</div>`;
+}
+
+/* An empty table means one of three different things. Saying which one, and
+ * offering the action that resolves it, is the difference between a dead end
+ * and a next step. */
+function renderEmptyState(graveCount) {
+  const firstRun = state.sections.length === 0;
+  const box = el("emptyState");
+
+  // On first run there is nothing to search, filter or list yet.
+  el("toolbar").hidden = firstRun;
+  el("graveTable").hidden = firstRun || graveCount === 0;
+
+  if (firstRun) {
+    box.innerHTML = `
+      <h2>Welcome to Grave Inventory</h2>
+      <p>Plots belong to a section, so start by creating one &mdash; for example
+         <b>A &middot; Garden of Peace</b>. You can add plots to it straight after.</p>
+      <button class="btn primary" data-onboard-section>Create first section</button>`;
+  } else if (graveCount > 0) {
+    box.hidden = true;
+    return;
+  } else if (state.totalGraves > 0) {
+    box.innerHTML = `
+      <p>No graves match the current filters.</p>
+      <button class="btn" data-clear-filters>Clear filters</button>`;
+  } else {
+    box.innerHTML = `
+      <p>No plots recorded yet.</p>
+      <button class="btn primary" data-onboard-grave>Add the first grave</button>`;
+  }
+  box.hidden = false;
+}
+
+async function refreshAll() {
+  // Sections must land before graves: the empty state can only choose its
+  // message once it knows whether any section exists.
+  await Promise.all([refreshStats(), refreshSections()]);
+  await refreshGraves();
+}
+
+/* Names what a delete takes with it, so attached paperwork is never a surprise. */
+async function confirmDelete(ownerType, id, what) {
+  const c = await call("describe_delete", ownerType, id);
+  const parts = [];
+  if (c.graves) parts.push(plural(c.graves, "plot"));
+  if (c.burials) parts.push(plural(c.burials, "burial record"));
+  if (c.documents) parts.push(plural(c.documents, "document"));
+  const tail = parts.length ? `, along with ${parts.join(", ")}` : "";
+  return confirm(`Delete ${what}${tail}? This cannot be undone.`);
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/util.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/util.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/util.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-head/graveyard/web/js/util.js	2026-09-21 08:21:35.017199400 -0400
@@ -0,0 +1,36 @@
+"use strict";
+
+const $ = (sel) => document.querySelector(sel);
+const el = (id) => document.getElementById(id);
+
+function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }
+function docBadge(n) { return n ? ` (${n})` : ""; }
+function fileSize(bytes) {
+  if (bytes < 1024) return `${bytes} B`;
+  if (bytes < 1048576) return `${Math.round(bytes / 1024)} KB`;
+  return `${(bytes / 1048576).toFixed(1)} MB`;
+}
+
+function show(id) { el(id).hidden = false; }
+function hide(id) { el(id).hidden = true; }
+function closeModalAround(node) {
+  const modal = node.closest(".modal-backdrop");
+  if (modal) modal.hidden = true;
+}
+function esc(s) {
+  return String(s).replace(/[&<>"']/g, (c) =>
+    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
+}
+function debounce(fn, ms) {
+  let h;
+  return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); };
+}
+let toastTimer;
+function toast(msg, isError = false) {
+  const t = el("toast");
+  t.textContent = msg;
+  t.className = "toast" + (isError ? " error" : "");
+  t.hidden = false;
+  clearTimeout(toastTimer);
+  toastTimer = setTimeout(() => (t.hidden = true), 3000);
+}

```