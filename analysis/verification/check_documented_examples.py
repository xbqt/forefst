#!/usr/bin/env python3
"""Run every runnable command example in the documentation and fail on a CLI-contract break.

Why this exists: v1.10 removed `-o` from `files`/`summary` for a defensible reason (the same flag meant
CSV, JSON or a bodyfile depending on other flags), and in doing so broke the README's first listing example
and four more in `tools/forefst.md` -- against a release note promising the old spellings kept working. No
gate noticed, because nothing ran what the documentation tells a reader to type.

What counts as a failure here is deliberately narrow: a **usage error** -- argparse rejecting the command
line, an unknown choice, or a `die()` about a flag. A data-dependent failure (a path that does not exist on
the sample image) is NOT a failure of the documentation and is reported separately, because the examples are
written against a reader's own volume.

Run from the repo root. Exit 0 when no documented example is rejected by the CLI.
"""
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES = ("README.md", "docs/tools/forefst.md", "docs/tools/refsanalysis.md")
IMAGE_TOKENS = ("disk.raw", "image.raw", "volume.raw", "refs.raw",
                # the walkthrough pages tell the reader to set a shell variable first; without
                # these the whole examples/ tree was silently skipped -- see BLOCK_SOURCES below.
                "$IMG", "${IMG}", "<image>", "win11refsmini.raw")
CMD = re.compile(r"\b((?:forefst|refsanalysis)\.py\s+[^\n`|]+)")
# stderr signatures that mean "the CLI rejected this COMMAND LINE" -- a contract break. Deliberately does
# NOT include a bare "error:", which also covers data-dependent failures ("file not found", "OID not found")
# that are correct behaviour when an example written for a reader's own volume is run against a sample.
USAGE = ("unrecognized argument", "invalid choice", "is not used by", "are only valid with",
         "is only valid with", "mutually exclusive", "expected one argument", "the following arguments are required",
         "unknown category", "not allowed with")


def shell_blocks(txt):
    """Yield the contents of ```sh / ```bash / ```console / ```shell fences only.

    Prose and tables are handled by the regex pass below. Blocks are handled separately because the
    walkthrough pages under docs/examples/ put their commands in fences and use a `$IMG` shell variable,
    which the regex pass discards as "not an image token" -- so every one of those pages was invisible to
    this gate. They are the pages a reader follows line by line.
    """
    out, cur = [], None
    for ln in txt.split("\n"):
        if ln.startswith("```"):
            lang = ln[3:].strip().lower()
            if cur is None:
                cur = [] if lang in ("sh", "bash", "console", "shell") else None
            else:
                out.append("\n".join(cur))
                cur = None
        elif cur is not None:
            cur.append(ln)
    return out


def block_sources(tree):
    """Every markdown page under docs/, plus the root README."""
    out = ["README.md"]
    docs = os.path.join(tree, "docs")
    for dp, _d, fs in os.walk(docs):
        if "website" in dp or "_templates" in dp:
            continue
        out += [os.path.relpath(os.path.join(dp, f), tree) for f in sorted(fs) if f.endswith(".md")]
    return out


def examples(tree):
    out = []
    # (a) fenced shell blocks on EVERY page
    for rel in block_sources(tree):
        p = os.path.join(tree, rel)
        if not os.path.exists(p):
            continue
        for blk in shell_blocks(open(p, encoding="utf-8").read()):
            blk = re.sub(r"\\\n\s*", " ", blk)                 # join line continuations
            for line in blk.split("\n"):
                line = re.sub(r"^\s*\$\s*", "", line.strip())    # drop a copy-paste prompt
                if not re.search(r"\b(?:forefst|refsanalysis)\.py\b", line):
                    continue
                line = re.sub(r"\s+#.*$", "", line)
                line = re.split(r"\s*[|>]\s*", line)[0].strip()
                line = re.sub(r"^python3?\s+", "", line).strip()
                if not line or not any(t in line for t in IMAGE_TOKENS):
                    continue
                if re.search(r"<(?!image>)[A-Za-z_]+>", line):     # a placeholder we cannot resolve
                    continue
                out.append((rel, line))
    # (b) the original prose/table regex pass -- it catches commands written inline in a table cell,
    #     which the block pass cannot see. Dropping it would have lost 7 commands.
    for rel in SOURCES:
        p = os.path.join(tree, rel)
        if not os.path.exists(p):
            continue
        for m in CMD.finditer(open(p, encoding="utf-8").read()):
            raw = m.group(1).strip().rstrip("\\").strip()
            raw = re.sub(r"\s+#.*$", "", raw)          # drop trailing comments
            raw = re.sub(r"\s*[>|].*$", "", raw)       # drop redirection / pipes
            if not raw or "<" in raw or ">" in raw:    # placeholders -- not runnable as written
                continue
            if not any(t in raw for t in IMAGE_TOKENS):
                continue
            out.append((rel, raw))
    seen = set()
    return [(r, c) for r, c in out if not (c in seen or seen.add(c))]


def default_tree():
    """Dev keeps the pages under forefstdev/docs; a PUBLISHED tree has docs/ at its root.

    Resolving this wrong is how a gate passes only in the maintainer's checkout. Both layouts are probed.
    """
    if os.path.isdir(os.path.join(ROOT, "forefstdev", "docs")):
        return os.path.join(ROOT, "forefstdev")
    return ROOT


def main(tree=None):
    tree = tree or default_tree()
    img = os.environ.get("SMOKE_IMAGE",
                         os.path.join(ROOT, "analysis/rawdisk/disks/step1/win11refsmini.raw"))
    if not os.path.exists(img):
        print("documented examples: SKIP (no sample image at %s)" % img)
        return 0
    ex = examples(tree)
    if not ex:
        print("FAIL — no runnable examples found under %r; the extractor or the docs moved." % tree)
        return 1
    tmp = tempfile.mkdtemp(prefix="fe_examples_")
    usage_errs, data_errs, ok = [], 0, 0
    try:
        for rel, cmd in ex:
            # shlex, not split(): a quoted example (`details "/users/bat/passwords.txt"`) otherwise reaches
            # the tool with the quote characters still attached, and the argument no longer starts with "/".
            # That produced two "failures" that were the harness's own quoting, not the docs' or the tool's.
            try:
                parts = shlex.split(cmd)
            except ValueError:
                parts = cmd.split()
            # ABSOLUTE: the child runs with cwd=tmp, so a relative tool path would not resolve there and
            # every example would fail to start -- counted as a data failure, reporting "0 rejected" while
            # running nothing at all. That is the same shape as the zero-page doc gate this audit found.
            tool = os.path.abspath(os.path.join(tree, parts[0]))
            if not os.path.exists(tool):
                continue
            # Only the argument FOLLOWING an output flag is a destination; everything else is an input
            # path on the volume and must be passed through untouched (rewriting `details /dir/file.txt`
            # into a temp path turned a real example into a guaranteed "not found").
            OUTFLAGS = ("-o", "--output", "--csv", "--json", "--jsonl", "--body")
            args = []
            redirect_next = False
            for a in parts[1:]:
                if redirect_next and not a.startswith("-"):
                    args.append(os.path.join(tmp, os.path.basename(a)))
                    redirect_next = False
                    continue
                redirect_next = a in OUTFLAGS
                args.append(img if a in IMAGE_TOKENS else a)
            try:
                r = subprocess.run([sys.executable, tool] + args, capture_output=True, text=True,
                                   timeout=180, cwd=tmp)
            except subprocess.TimeoutExpired:
                data_errs += 1
                continue
            err = (r.stderr or "").lower()
            if r.returncode != 0 and any(u in err for u in USAGE):
                usage_errs.append((rel, cmd, (r.stderr or "").strip().split("\n")[-1][:120]))
            elif r.returncode != 0:
                data_errs += 1
            else:
                ok += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("documented examples: %d runnable; %d ran clean, %d failed on this image's data, "
          "%d REJECTED BY THE CLI" % (len(ex), ok, data_errs, len(usage_errs)))
    if ex and ok == 0:
        print("FAIL — %d example(s) were found but NONE ran clean. That is a harness fault (wrong tree, or "
              "the tool could not be launched), not a clean bill of health." % len(ex))
        return 1
    for rel, cmd, msg in usage_errs:
        print("   %s: %s" % (rel, cmd))
        print("      -> %s" % msg)
    return 1 if usage_errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
