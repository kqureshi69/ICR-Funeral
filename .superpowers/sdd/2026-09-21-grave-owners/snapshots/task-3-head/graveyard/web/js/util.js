"use strict";

const $ = (sel) => document.querySelector(sel);
const el = (id) => document.getElementById(id);

function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }
function docBadge(n) { return n ? ` (${n})` : ""; }
function fileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function show(id) { el(id).hidden = false; }
function hide(id) { el(id).hidden = true; }
function closeModalAround(node) {
  const modal = node.closest(".modal-backdrop");
  if (modal) modal.hidden = true;
}
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function debounce(fn, ms) {
  let h;
  return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); };
}
let toastTimer;
function toast(msg, isError = false) {
  const t = el("toast");
  t.textContent = msg;
  t.className = "toast" + (isError ? " error" : "");
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 3000);
}
