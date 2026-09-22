"use strict";

let state = { sectionId: null, status: "", search: "", sections: [], totalGraves: 0,
              docOwner: { type: null, id: null, title: "" },
              tab: "sections", ownerId: null, owners: [], ownerReturnsToGrave: false };

/* ---------- Rendering ---------- */

async function refreshStats() {
  const s = await call("stats");
  // Remembered so the empty state can tell "nothing recorded yet" apart from
  // "records exist but the filters hide them".
  state.totalGraves = s.total;
  el("stats").innerHTML = `
    <div><b>${s.total}</b>Total plots</div>
    <div><b>${s.available}</b>Available</div>
    <div><b>${s.reserved}</b>Reserved</div>
    <div><b>${s.occupied}</b>Occupied</div>
    <div><b>${s.sections}</b>Sections</div>`;
}

/* An empty table means one of three different things. Saying which one, and
 * offering the action that resolves it, is the difference between a dead end
 * and a next step. */
function renderEmptyState(graveCount) {
  const firstRun = state.sections.length === 0;
  const box = el("emptyState");

  // On first run there is nothing to search, filter or list yet.
  el("toolbar").hidden = firstRun;
  el("graveTable").hidden = firstRun || graveCount === 0;

  if (firstRun) {
    box.innerHTML = `
      <h2>Welcome to Grave Inventory</h2>
      <p>Plots belong to a section, so start by creating one &mdash; for example
         <b>A &middot; Garden of Peace</b>. You can add plots to it straight after.</p>
      <button class="btn primary" data-onboard-section>Create first section</button>`;
  } else if (graveCount > 0) {
    box.hidden = true;
    return;
  } else if (state.totalGraves > 0) {
    box.innerHTML = `
      <p>No graves match the current filters.</p>
      <button class="btn" data-clear-filters>Clear filters</button>`;
  } else {
    box.innerHTML = `
      <p>No plots recorded yet.</p>
      <button class="btn primary" data-onboard-grave>Add the first grave</button>`;
  }
  box.hidden = false;
}

async function refreshAll() {
  // Sections must land before graves: the empty state can only choose its
  // message once it knows whether any section exists.
  await Promise.all([refreshStats(), refreshSections(), refreshOwners()]);
  await refreshGraves();
}

/* Names what a delete takes with it, so attached paperwork is never a surprise. */
async function confirmDelete(ownerType, id, what) {
  const c = await call("describe_delete", ownerType, id);
  const parts = [];
  if (c.graves) parts.push(plural(c.graves, "plot"));
  if (c.burials) parts.push(plural(c.burials, "burial record"));
  if (c.documents) parts.push(plural(c.documents, "document"));
  const tail = parts.length ? `, along with ${parts.join(", ")}` : "";
  return confirm(`Delete ${what}${tail}? This cannot be undone.`);
}
