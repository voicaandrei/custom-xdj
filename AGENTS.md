# Custom XDJ contributor instructions

Read README.md, docs/compatibility.md and docs/research.md before firmware work.
Scope: full-track, one-sided browser previews for the XDJ-1000MK2, with the accepted INFO and key-match changes.
Keep [C] confirmed, [I] inferred and [U] unknown evidence distinct. Owner reports are not broad compatibility proof.
Bind every binary offset to SHA-256 and an explicit FILE/CODE/RAM address space.
Never import an ABI, offset, update format or recovery assumption from another player.
Firmware, manuals, exports, private observations and derived binaries stay in ignored private/ or evidence/ files.
Do not publish firmware, keys, user tracks, device identifiers or raw captures.
Static analysis must not execute stock firmware or downloaded reference-project scripts.
Player writes need the owner's explicit authorization. Never format media or change music as part of staging.
Describe recovery limits honestly; working updates on one unit do not prove recovery from an application hang.
All public documentation, issues, comments and user-facing tools must be in English.
Preserve the frozen runtime/build inputs: changing their bytes can invalidate historical source hashes.
Checks: npm test; python3 -m unittest discover -s tests -p 'test_*.py'.
Public tests must run without firmware or private exports; skip only explicitly unavailable dependencies.
Never add a remote or publish without an explicit user request.
