# Publication validation — 2026-09-10

- Full local suite with private prerequisites: 384 Python tests passed before adding the three release-entry tests; those three additional tests also passed independently.
- Clean source checkout, without firmware, owner captures or historical evidence: 384 Python tests discovered, 90 passed and 294 explicitly skipped. The local SH compiler was available for compiler-dependent checks.
- Clean JavaScript suite: 16 tests discovered, 13 passed and 3 optional fixture checks skipped.
- Fresh local release build from the official 1.44 UPD and source-only checkout: output SHA-256 `ce23b4f3d198f5066bc6861223d249d9c66d979b5f0af54a0d32e8e2cb0671f6`, matching the frozen release.
- Public file audit: no firmware, binary files, private paths, device serials or captured user exports staged. Only the curated release record is published from the evidence directory.
- Local documentation links checked. CI runs the source-only checks on Ubuntu and macOS; see the repository Actions page for current results. Runners without the SH compiler skip those additional checks explicitly.

These checks do not add hardware acceptance beyond the owner observations in [release evidence](../evidence/release-v1.json). The final label package still requires an observed installation; other units, long soak tests and guaranteed recovery remain unverified.
