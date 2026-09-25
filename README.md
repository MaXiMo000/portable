# portable

> **Deprecated: `portable` is now the [`export_contains`](https://github.com/MaXiMo000/invariant#readme)
> check type in [invariant](https://github.com/MaXiMo000/invariant)** (`pip install invariant-verify`),
> where it runs alongside SQL, backup-restore, security and GDPR-erasure checks
> and writes into the same proof bundle. `portable check` still works -- same
> arguments, output and exit codes -- and delegates to it. Everything below
> describes that behavior, and applies to `export_contains` too.

[![ci](https://github.com/MaXiMo000/portable/actions/workflows/ci.yml/badge.svg)](https://github.com/MaXiMo000/portable/actions/workflows/ci.yml)

**Does a data export actually contain what it promises? Checked category
by category, found or missing.**

A privacy policy or an export feature's own docs say "your export
includes your profile, your order history, and your uploaded photos."
Nobody automatically checks whether a real export actually contains all
three. `portable` reads a real export and a declared list of categories,
and reports which ones are actually there.

```
$ portable check export.json export-manifest.yaml
[OK] 'profile': user.email is present in the export
[OK] 'order_history': orders has 2 item(s)
[??] 'uploaded_photos' needs a directory export, but a JSON file was given

2/3 found, 1 unverified
```

(Real output.)

## Scope -- read this before anything else

**This is infrastructure for checking your own export against your own
declared promises.** It has no notion of any specific company, ships with
no data about any real service, and makes no claim about anyone's actual
compliance. Point it at an export *you* produced (your own app's export
feature, tested against your own account) and a manifest *you* wrote
(your own privacy policy's own claims) -- the same "sites I own" discipline
[witness](https://github.com/MaXiMo000/witness) already holds itself to
for a different kind of claim-checking. Automatically testing a live
third party's export feature and publishing findings about them is a
different, much riskier thing this repo deliberately does not do and was
not built to enable.

## Install

```
pip install portable-evidence   # the command it installs is `portable`
```

(`portable` was already taken on PyPI -- same story as every sibling in
this portfolio.)

## Use

Declare what your export is supposed to contain, in `export-manifest.yaml`:

```yaml
categories:
  - name: profile
    json_path: user.email        # a dot/bracket path into a JSON export
  - name: order_history
    json_path: orders
    min_count: 1                 # must be a list with at least this many items
  - name: uploaded_photos
    file_glob: "photos/*.jpg"    # for a directory-shaped export instead
  - name: order_history_csv
    file_glob: "Orders/*.csv"    # first non-empty match, if more than one
    csv_column: order_id         # + this column must have real values in it
    min_count: 1                 # applies to non-empty *rows* of that column
```

Then check a real export against it:

```
portable check export.json export-manifest.yaml        # a single JSON export
portable check export-directory/ export-manifest.yaml   # a directory export
portable check export.zip export-manifest.yaml          # a zip archive export
```

A `.zip` export (a Google-Takeout-style archive) is extracted to a scratch
directory and checked exactly like an already-unpacked directory export --
`file_glob` and `csv_column` categories never need to know which one they
got.

Each category needs exactly one of `json_path` (checked against a single
JSON file export) or `file_glob` (checked against a directory or zip
export, matched with `pathlib.Path.glob`, must resolve to at least one
non-empty file). Pointing a `json_path` category at a directory/zip
export, or a `file_glob` category at a JSON file, reports that one
category as `unverified` -- not a failure, just the wrong export shape
for what it needs, named clearly rather than silently skipped.

Adding `csv_column` to a `file_glob` category opens the first matching
file as CSV and additionally requires that column to have at least
`min_count` (default 1) non-empty values -- a category with the right
*filename* but an empty or header-only CSV inside it would otherwise read
as `found` from the filename match alone.

`--json` prints the full machine-readable report. Exit code is `1` only if
a category comes back `missing` -- `unverified` never fails it, same
convention every sibling tool in this portfolio shares.

## What counts as "missing"

Not just "the key doesn't exist" -- a field that exists but is empty
(`""`, `[]`, `{}`, `null`) counts as missing too. The whole point of a
category is proving real data landed in the export; a key that's
technically present but holds nothing satisfies that no better than the
key being absent.

## What this does NOT do

- **No semantic understanding of what a category "should" contain.**
  `portable` only checks presence and non-emptiness (and, for a list, a
  minimum count) -- it can't tell you whether the *content* at `user.email`
  is actually a real email address, or whether `order_history` contains
  every order that ever happened. That's a correctness question about the
  export's content, a different and harder problem than "is the category
  there at all."
- **No nested archives.** A `.zip` export is extracted one level; a ZIP
  containing another ZIP inside it isn't recursed into. Real Google-
  Takeout-style exports don't nest this way, so it wasn't worth the extra
  code. Extraction is capped at 2 GiB uncompressed; a bigger archive reads as
  `unverified` rather than filling the disk.
- **No wildcards, filters, or a real JSONPath grammar** in `json_path` --
  dot keys and `[N]` indices only. Every real manifest entry names one
  concrete field or list, not a query over the whole document.

## Tests

```
pip install -e .
python tests/test_manifest.py   # export-manifest.yaml validation
python tests/test_cli.py        # the real CLI entry point, real files, real argv
```


MIT licensed.
