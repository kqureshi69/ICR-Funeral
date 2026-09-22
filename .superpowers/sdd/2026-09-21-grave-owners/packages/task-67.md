# Review package: task-67

No git in this project: this diff is snapshot-to-snapshot,
base `task-67-base` -> current working tree.

## Files changed

- graveyard/web/index.html
- graveyard/web/js/graves.js

## Stat

2 files, +24 / -11 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-base/graveyard/web/index.html C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-head/graveyard/web/index.html
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-base/graveyard/web/index.html	2026-09-21 08:55:39.380919100 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-head/graveyard/web/index.html	2026-09-21 09:01:57.455649500 -0400
@@ -48,7 +48,6 @@
             <th>Plot #</th>
             <th>Status</th>
             <th>Owner</th>
-            <th>Contact</th>
             <th class="actions-col">Actions</th>
           </tr>
         </thead>
@@ -77,11 +76,8 @@
             <option value="occupied">Occupied</option>
           </select>
         </label>
-        <label>Owner name
-          <input type="text" id="graveOwner" />
-        </label>
-        <label>Owner contact
-          <input type="text" id="graveContact" />
+        <label>Owner
+          <select id="graveOwnerSelect"></select>
         </label>
         <div class="field-row">
           <label>Grave id
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-base/graveyard/web/js/graves.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-head/graveyard/web/js/graves.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-base/graveyard/web/js/graves.js	2026-09-21 08:55:58.281714100 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-head/graveyard/web/js/graves.js	2026-09-21 09:02:08.788113600 -0400
@@ -10,7 +10,6 @@
       <td>${esc(g.plot_number)}</td>
       <td><span class="badge ${g.status}">${g.status}</span></td>
       <td>${esc(g.owner_name || "—")}</td>
-      <td>${esc(g.owner_contact || "—")}</td>
       <td class="actions-col">
         <button class="btn link" data-docs-grave="${g.id}">Docs${docBadge(g.doc_count)}</button>
         <button class="btn link" data-detail="${g.id}">Burials</button>
@@ -42,15 +41,34 @@
   el("graveId").value = grave ? grave.id : "";
   el("gravePlot").value = grave ? grave.plot_number : "";
   el("graveStatus").value = grave ? grave.status : "available";
-  el("graveOwner").value = grave ? grave.owner_name || "" : "";
-  el("graveContact").value = grave ? grave.owner_contact || "" : "";
   el("graveNotes").value = grave ? grave.notes || "" : "";
   el("graveRef").value = grave ? grave.grave_ref || "" : "";
   el("graveDeed").value = grave ? grave.deed_id || "" : "";
   el("gravePurchased").value = grave ? grave.date_purchased || "" : "";
+  await refreshOwners();             // never offer a stale or deleted owner
+  fillOwnerOptions(grave ? grave.owner_id : null);
   show("graveModal");
 }
 
+/* The trailing "+ New owner…" entry opens the owner modal and returns here
+ * with the new owner selected, so grave entry is never interrupted. */
+function fillOwnerOptions(selectedId) {
+  el("graveOwnerSelect").innerHTML =
+    `<option value="">— no owner —</option>` +
+    state.owners.map((o) =>
+      `<option value="${o.id}" ${o.id === selectedId ? "selected" : ""}>${esc(o.name)}</option>`
+    ).join("") +
+    `<option value="__new">+ New owner…</option>`;
+  el("graveOwnerSelect").value = selectedId ? String(selectedId) : "";
+}
+
+el("graveOwnerSelect").addEventListener("change", (e) => {
+  if (e.target.value !== "__new") return;
+  e.target.value = "";               // never leave the sentinel selected
+  state.ownerReturnsToGrave = true;
+  openOwnerModal(null);
+});
+
 el("graveForm").addEventListener("submit", async (e) => {
   e.preventDefault();
   const id = el("graveId").value;
@@ -60,8 +78,7 @@
   const common = [
     el("gravePlot").value,
     el("graveStatus").value,
-    el("graveOwner").value,
-    el("graveContact").value,
+    el("graveOwnerSelect").value,     // "" means unassigned -> NULL
     el("graveNotes").value,
     el("graveRef").value,
     el("graveDeed").value,

```