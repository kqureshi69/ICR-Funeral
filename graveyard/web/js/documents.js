"use strict";

/* ---------- Documents modal ---------- */

/* One modal serves sections, graves and burials; only the owner changes. */
async function openDocuments(ownerType, ownerId, title) {
  state.docOwner = { type: ownerType, id: ownerId, title };
  el("documentsTitle").textContent = `Documents — ${title}`;
  await refreshDocuments();
  show("documentsModal");
}

async function refreshDocuments() {
  const { type, id } = state.docOwner;
  renderDocuments(await call("list_documents", type, id));
}

function renderDocuments(docs) {
  el("documentBody").innerHTML = docs.length
    ? docs.map((d) => `
      <tr>
        <td><button class="doc-name" data-doc-open="${d.id}"
                    title="Open in the default application">${esc(d.original_name)}</button></td>
        <td>${fileSize(d.size_bytes)}</td>
        <td>${esc((d.created_at || "").slice(0, 10))}</td>
        <td class="actions-col">
          <button class="btn link danger" data-doc-del="${d.id}">remove</button>
        </td>
      </tr>`).join("")
    : `<tr><td colspan="4" class="empty">No documents attached yet.</td></tr>`;
}

el("uploadDocBtn").addEventListener("click", async () => {
  const { type, id } = state.docOwner;
  // The native picker runs in Python; no file bytes cross this bridge.
  const added = await call("add_documents", type, id);
  if (added.length) {
    toast(`${added.length} document${added.length === 1 ? "" : "s"} attached`);
    await refreshDocuments();
    await refreshAll();
  }
});
