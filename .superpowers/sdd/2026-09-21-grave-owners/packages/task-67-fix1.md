# Review package: task-67-fix1

No git in this project: this diff is snapshot-to-snapshot,
base `task-67-head` -> current working tree.

## Files changed

- graveyard/web/js/app.js

## Stat

1 files, +20 / -2 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-head/graveyard/web/js/app.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-fix1-head/graveyard/web/js/app.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-head/graveyard/web/js/app.js	2026-09-21 08:56:05.876276900 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-67-fix1-head/graveyard/web/js/app.js	2026-09-21 09:07:14.854268800 -0400
@@ -2,13 +2,31 @@
 
 /* ---------- Global event delegation ---------- */
 
+/* The owner modal can be dismissed (Cancel or backdrop click) instead of
+ * saved. Without this, a flag set by "+ New owner..." on the grave form
+ * would survive the cancel and get consumed by some later, unrelated owner
+ * save elsewhere in the app. Not cleared inside openOwnerModal itself: the
+ * grave-form path sets the flag and *then* calls openOwnerModal(null), so
+ * clearing on open would wipe the flag it just set. */
+function clearOwnerReturnOnDismiss(modal) {
+  if (modal && modal.id === "ownerModal") state.ownerReturnsToGrave = false;
+}
+
 document.addEventListener("click", async (e) => {
   const t = e.target;
 
   // Close only the modal that was clicked: the documents modal can sit on top
   // of the grave detail modal, which should survive it.
-  if (t.dataset.close !== undefined) { closeModalAround(t); return; }
-  if (t.classList.contains("modal-backdrop")) { t.hidden = true; return; }
+  if (t.dataset.close !== undefined) {
+    clearOwnerReturnOnDismiss(t.closest(".modal-backdrop"));
+    closeModalAround(t);
+    return;
+  }
+  if (t.classList.contains("modal-backdrop")) {
+    clearOwnerReturnOnDismiss(t);
+    t.hidden = true;
+    return;
+  }
 
   // Empty-state calls to action
   if (t.dataset.onboardSection !== undefined) { openSectionModal(null); return; }

```