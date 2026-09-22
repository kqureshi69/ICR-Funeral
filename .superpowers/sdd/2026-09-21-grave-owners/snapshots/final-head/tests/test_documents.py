"""Tests for document attachments. Run: python tests/test_documents.py

Dependency-free on purpose: plain asserts, no pytest, matching the project's
zero-dev-dependency setup.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The DB location must be chosen before graveyard.database is imported.
TMP = Path(tempfile.mkdtemp(prefix="graveyard-test-"))
os.environ["GRAVEYARD_DB"] = str(TMP / "test.db")

from graveyard import documents                      # noqa: E402
from graveyard.api import Api                        # noqa: E402
from graveyard.database import get_connection, init_db  # noqa: E402

PASS, FAIL = [], []


def check(name, fn):
    try:
        fn()
    except Exception as exc:
        FAIL.append(f"{name}: {type(exc).__name__}: {exc}")
    else:
        PASS.append(name)


def ok(res):
    """Unwrap an API envelope, asserting success."""
    assert res["ok"], f"expected ok, got error: {res.get('error')}"
    return res["data"]


def err(res):
    assert not res["ok"], f"expected failure, got: {res.get('data')}"
    return res["error"]


def sample(name="deed.pdf", size=1024):
    p = TMP / "incoming" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * size)
    return str(p)


def fresh():
    """Reset to an empty DB plus one section / grave / burial."""
    for t in ("documents", "burials", "graves", "sections"):
        with get_connection() as conn:
            conn.execute(f"DELETE FROM {t}")
    if documents.docs_dir().exists():
        shutil.rmtree(documents.docs_dir())
    a = Api()
    sid = ok(a.create_section("A", "Garden"))
    gid = ok(a.create_grave(sid, "1"))
    bid = ok(a.add_burial(gid, "Jane Doe"))
    return a, sid, gid, bid


# --- tests ------------------------------------------------------------------

def t_docs_dir_follows_db():
    assert documents.docs_dir() == Path(os.environ["GRAVEYARD_DB"]).parent / "documents", \
        documents.docs_dir()


def t_attach_and_list():
    a, sid, gid, bid = fresh()
    added = ok(a.attach_files("grave", gid, [sample()]))
    assert len(added) == 1, added
    rows = ok(a.list_documents("grave", gid))
    assert len(rows) == 1, rows
    assert rows[0]["original_name"] == "deed.pdf", rows[0]
    assert (documents.docs_dir() / rows[0]["stored_name"]).exists(), "file not stored"
    assert rows[0]["stored_name"] != "deed.pdf", "stored name must not be the original"


def t_attach_all_three_owner_types():
    a, sid, gid, bid = fresh()
    ok(a.attach_files("section", sid, [sample("plan.pdf")]))
    ok(a.attach_files("grave", gid, [sample("deed.pdf")]))
    ok(a.attach_files("burial", bid, [sample("cert.pdf")]))
    assert len(ok(a.list_documents("section", sid))) == 1
    assert len(ok(a.list_documents("grave", gid))) == 1
    assert len(ok(a.list_documents("burial", bid))) == 1


def t_delete_document_removes_file():
    a, sid, gid, bid = fresh()
    doc = ok(a.attach_files("grave", gid, [sample()]))[0]
    path = documents.docs_dir() / doc["stored_name"]
    assert path.exists()
    ok(a.delete_document(doc["id"]))
    assert not path.exists(), "file left on disk after delete_document"
    assert ok(a.list_documents("grave", gid)) == []


def t_delete_grave_removes_its_documents():
    a, sid, gid, bid = fresh()
    gdoc = ok(a.attach_files("grave", gid, [sample("deed.pdf")]))[0]
    bdoc = ok(a.attach_files("burial", bid, [sample("cert.pdf")]))[0]
    paths = [documents.docs_dir() / d["stored_name"] for d in (gdoc, bdoc)]
    ok(a.delete_grave(gid))
    for p in paths:
        assert not p.exists(), f"orphaned file after delete_grave: {p.name}"


def t_delete_section_removes_descendant_documents():
    a, sid, gid, bid = fresh()
    docs = [ok(a.attach_files("section", sid, [sample("plan.pdf")]))[0],
            ok(a.attach_files("grave", gid, [sample("deed.pdf")]))[0],
            ok(a.attach_files("burial", bid, [sample("cert.pdf")]))[0]]
    paths = [documents.docs_dir() / d["stored_name"] for d in docs]
    ok(a.delete_section(sid))
    for p in paths:
        assert not p.exists(), f"orphaned file after delete_section: {p.name}"
    with get_connection() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
    assert n == 0, f"{n} document rows survived the cascade"


def t_exactly_one_owner_enforced():
    a, sid, gid, bid = fresh()
    with get_connection() as conn:
        for cols, vals in ((("section_id", "grave_id"), (sid, gid)), ((), ())):
            names = ", ".join(cols)
            try:
                conn.execute(
                    f"INSERT INTO documents ({names + ',' if names else ''}"
                    f" original_name, stored_name, size_bytes) VALUES "
                    f"({'?,' * len(vals)} ?, ?, ?)",
                    (*vals, "x.pdf", "x", 1))
            except Exception:
                pass
            else:
                raise AssertionError(f"CHECK did not reject owners={cols}")


def t_rejects_bad_extension():
    a, sid, gid, bid = fresh()
    msg = err(a.attach_files("grave", gid, [sample("payload.exe")]))
    assert "exe" in msg.lower() or "type" in msg.lower(), msg
    assert ok(a.list_documents("grave", gid)) == [], "row created for rejected file"


def t_rejects_oversize():
    a, sid, gid, bid = fresh()
    big = sample("huge.pdf", documents.MAX_BYTES + 1)
    msg = err(a.attach_files("grave", gid, [big]))
    assert "large" in msg.lower() or "size" in msg.lower(), msg
    assert ok(a.list_documents("grave", gid)) == []


def t_rejects_unknown_owner_type():
    a, sid, gid, bid = fresh()
    err(a.attach_files("coffin", 1, [sample()]))


def t_rejects_missing_owner():
    a, sid, gid, bid = fresh()
    err(a.attach_files("grave", 99999, [sample()]))


def t_delete_preview_counts():
    a, sid, gid, bid = fresh()
    ok(a.attach_files("section", sid, [sample("plan.pdf")]))
    ok(a.attach_files("burial", bid, [sample("cert.pdf")]))
    c = ok(a.describe_delete("section", sid))
    assert c["graves"] == 1 and c["burials"] == 1 and c["documents"] == 2, c


if __name__ == "__main__":
    init_db()
    for name, fn in sorted(globals().items()):
        if name.startswith("t_"):
            check(name[2:], fn)
    for n in PASS:
        print(f"  [PASS] {n}")
    for f in FAIL:
        print(f"  [FAIL] {f}")
    print(f"RESULT {len(PASS)}/{len(PASS) + len(FAIL)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if FAIL else 0)
