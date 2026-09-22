# Review package: task-5

No git in this project: this diff is snapshot-to-snapshot,
base `task-5-base` -> current working tree.

## Files changed

- graveyard/web/css/styles.css
- graveyard/web/index.html
- graveyard/web/js/app.js
- graveyard/web/js/graves.js
- graveyard/web/js/owners.js
- graveyard/web/js/state.js

## Stat

6 files, +148 / -4 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/css/styles.css C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/css/styles.css
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/css/styles.css	2026-09-20 18:43:18.709844300 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/css/styles.css	2026-09-21 08:55:40.801147600 -0400
@@ -53,6 +53,14 @@
 }
 .sidebar-head { display: flex; justify-content: space-between; align-items: center; }
 .sidebar-head h2 { font-size: 14px; text-transform: uppercase; color: var(--muted); margin: 0; }
+.tabs { display: flex; gap: 4px; }
+.tab {
+  font: inherit; font-size: 12px; text-transform: uppercase;
+  padding: 4px 8px; border: none; border-radius: 6px;
+  background: none; color: var(--muted); cursor: pointer;
+}
+.tab.active { background: #e7f0eb; color: var(--accent); font-weight: 600; }
+.modal-actions .spacer { flex: 1; }
 .section-list { list-style: none; margin: 14px 0 0; padding: 0; }
 .section-list li {
   padding: 10px 12px;
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/index.html C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/index.html
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/index.html	2026-09-21 08:22:19.311753100 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/index.html	2026-09-21 08:55:39.380919100 -0400
@@ -16,10 +16,15 @@
     <!-- Sidebar: sections -->
     <aside class="sidebar">
       <div class="sidebar-head">
-        <h2>Sections</h2>
+        <div class="tabs">
+          <button class="tab active" data-tab="sections">Sections</button>
+          <button class="tab" data-tab="owners">Owners</button>
+        </div>
         <button class="btn small" id="addSectionBtn">+ Add</button>
+        <button class="btn small" id="addOwnerBtn" hidden>+ Add</button>
       </div>
       <ul class="section-list" id="sectionList"></ul>
+      <ul class="section-list" id="ownerList" hidden></ul>
     </aside>
 
     <!-- Main: graves -->
@@ -172,12 +177,40 @@
     </div>
   </div>
 
+  <div class="modal-backdrop" id="ownerModal" hidden>
+    <div class="modal">
+      <h3 id="ownerModalTitle">Add Owner</h3>
+      <form id="ownerForm">
+        <input type="hidden" id="ownerId" />
+        <label>Name
+          <input type="text" id="ownerName" required placeholder="e.g. Aftab Dar" />
+        </label>
+        <label>Contact
+          <input type="text" id="ownerContact" placeholder="phone or email" />
+        </label>
+        <label>Address
+          <input type="text" id="ownerAddress" />
+        </label>
+        <label>Notes
+          <textarea id="ownerNotes" rows="4"></textarea>
+        </label>
+        <div class="modal-actions">
+          <button type="button" class="btn danger" id="deleteOwnerBtn" hidden>Delete</button>
+          <span class="spacer"></span>
+          <button type="button" class="btn" data-close>Cancel</button>
+          <button type="submit" class="btn primary">Save</button>
+        </div>
+      </form>
+    </div>
+  </div>
+
   <div class="toast" id="toast" hidden></div>
 
   <script src="js/util.js"></script>
   <script src="js/api.js"></script>
   <script src="js/state.js"></script>
   <script src="js/sections.js"></script>
+  <script src="js/owners.js"></script>
   <script src="js/graves.js"></script>
   <script src="js/documents.js"></script>
   <script src="js/app.js"></script>
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/app.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/app.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/app.js	2026-09-21 08:22:14.947231500 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/app.js	2026-09-21 08:56:05.876276900 -0400
@@ -60,10 +60,29 @@
     openSectionModal(s);
     return;
   }
+  if (t.dataset.tab) { setTab(t.dataset.tab); return; }
+  if (t.dataset.addOwner !== undefined) { openOwnerModal(null); return; }
+  if (t.dataset.editOwner) {
+    const o = await call("get_owner", Number(t.dataset.editOwner));
+    openOwnerModal(o);
+    return;
+  }
+  const ownerLi = t.closest("li[data-owner-id]");
+  if (ownerLi) {
+    state.ownerId = ownerLi.dataset.ownerId ? Number(ownerLi.dataset.ownerId) : null;
+    state.sectionId = null;   // the two filters are mutually exclusive
+    await refreshOwners();
+    await refreshSections();
+    await refreshGraves();
+    return;
+  }
+
   const li = t.closest("li[data-id]");
   if (li) {
     state.sectionId = li.dataset.id ? Number(li.dataset.id) : null;
+    state.ownerId = null;
     await refreshSections();
+    await refreshOwners();
     await refreshGraves();
     return;
   }
@@ -94,6 +113,7 @@
 });
 
 el("addSectionBtn").addEventListener("click", () => openSectionModal(null));
+el("addOwnerBtn").addEventListener("click", () => openOwnerModal(null));
 el("addGraveBtn").addEventListener("click", () => {
   if (state.sections.length === 0) return promptForFirstSection();
   openGraveModal(null);
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/graves.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/graves.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/graves.js	2026-09-21 08:22:01.540701100 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/graves.js	2026-09-21 08:55:58.281714100 -0400
@@ -1,7 +1,8 @@
 "use strict";
 
 async function refreshGraves() {
-  const graves = await call("list_graves", state.sectionId, state.status, state.search);
+  const graves = await call("list_graves", state.sectionId, state.status,
+                            state.search, state.ownerId);
   const body = el("graveBody");
   body.innerHTML = graves.map((g) => `
     <tr>
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/owners.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/owners.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/owners.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/owners.js	2026-09-21 08:55:51.805618300 -0400
@@ -0,0 +1,81 @@
+"use strict";
+
+async function refreshOwners() {
+  const owners = await call("list_owners");
+  state.owners = owners;
+  // No owners yet: say so and offer the action, matching the grave empty state.
+  if (owners.length === 0) {
+    el("ownerList").innerHTML = `
+      <li class="owner-empty">
+        <div class="sec-name">No owners recorded yet</div>
+        <div class="sec-meta"><span>Plots can be filed under an owner.</span></div>
+        <button class="btn small primary" data-add-owner>Add owner</button>
+      </li>`;
+    return;
+  }
+  el("ownerList").innerHTML = `<li class="${state.ownerId === null ? "active" : ""}" data-owner-id="">
+      <div class="sec-name">All owners</div>
+      <div class="sec-meta"><span>Show every plot</span></div></li>` +
+    owners.map((o) => `
+    <li class="${state.ownerId === o.id ? "active" : ""}" data-owner-id="${o.id}">
+      <button class="btn link sec-edit" data-edit-owner="${o.id}">edit</button>
+      <div class="sec-name">${esc(o.name)}</div>
+      <div class="sec-meta">
+        <span>${plural(o.grave_count, "plot")}</span>
+        <span>${esc(o.contact || "")}</span>
+      </div>
+    </li>`).join("");
+}
+
+function openOwnerModal(owner) {
+  el("ownerModalTitle").textContent = owner ? "Edit Owner" : "Add Owner";
+  el("ownerId").value = owner ? owner.id : "";
+  el("ownerName").value = owner ? owner.name : "";
+  el("ownerContact").value = owner ? owner.contact || "" : "";
+  el("ownerAddress").value = owner ? owner.address || "" : "";
+  el("ownerNotes").value = owner ? owner.notes || "" : "";
+  el("deleteOwnerBtn").hidden = !owner;
+  show("ownerModal");
+}
+
+el("ownerForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const id = el("ownerId").value;
+  const args = [el("ownerName").value, el("ownerContact").value,
+                el("ownerAddress").value, el("ownerNotes").value];
+  let newId = null;
+  if (id) await call("update_owner", Number(id), ...args);
+  else newId = await call("create_owner", ...args);
+  hide("ownerModal");
+  toast("Owner saved");
+  await refreshOwners();
+  // Opened from the grave form: hand the new owner straight back to it.
+  // `fillOwnerOptions` arrives in Task 6, so this is guarded — between Task 5
+  // and Task 6 the inline path simply does nothing rather than throwing.
+  if (newId && state.ownerReturnsToGrave) {
+    state.ownerReturnsToGrave = false;
+    if (typeof fillOwnerOptions === "function") fillOwnerOptions(newId);
+  }
+  await refreshAll();
+});
+
+el("deleteOwnerBtn").addEventListener("click", async () => {
+  const id = Number(el("ownerId").value);
+  if (!confirm("Delete this owner?")) return;
+  await call("delete_owner", id);   // refused by the API if they hold plots
+  hide("ownerModal");
+  toast("Owner deleted");
+  if (state.ownerId === id) state.ownerId = null;
+  await refreshOwners();
+  await refreshAll();
+});
+
+function setTab(name) {
+  state.tab = name;
+  document.querySelectorAll(".tab").forEach(
+    (t) => t.classList.toggle("active", t.dataset.tab === name));
+  el("sectionList").hidden = name !== "sections";
+  el("ownerList").hidden = name !== "owners";
+  el("addSectionBtn").hidden = name !== "sections";
+  el("addOwnerBtn").hidden = name !== "owners";
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/state.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/state.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-base/graveyard/web/js/state.js	2026-09-21 08:21:43.089041200 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-5-head/graveyard/web/js/state.js	2026-09-21 08:55:56.961935800 -0400
@@ -1,7 +1,8 @@
 "use strict";
 
 let state = { sectionId: null, status: "", search: "", sections: [], totalGraves: 0,
-              docOwner: { type: null, id: null, title: "" } };
+              docOwner: { type: null, id: null, title: "" },
+              tab: "sections", ownerId: null, owners: [], ownerReturnsToGrave: false };
 
 /* ---------- Rendering ---------- */
 
@@ -53,7 +54,7 @@
 async function refreshAll() {
   // Sections must land before graves: the empty state can only choose its
   // message once it knows whether any section exists.
-  await Promise.all([refreshStats(), refreshSections()]);
+  await Promise.all([refreshStats(), refreshSections(), refreshOwners()]);
   await refreshGraves();
 }
 

```