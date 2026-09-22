"use strict";

/* Thin wrapper around the Python API that unwraps the {ok, data|error}
 * envelope and surfaces errors as a toast. */
async function call(method, ...args) {
  const res = await window.pywebview.api[method](...args);
  if (!res.ok) {
    toast(res.error, true);
    throw new Error(res.error);
  }
  return res.data;
}
