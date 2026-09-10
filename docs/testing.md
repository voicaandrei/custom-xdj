# Testing

## Source-only checks

Use Node.js 22+, Python 3.9+ and a host C compiler:

```sh
npm test
python3 -m unittest discover -s tests -p 'test_*.py'
```

The public suite checks synthetic ANLZ parsing, resampling, rendering, bounded buffers, protocol state, INFO stride, scrolling gates and patch contracts that do not require firmware. Native tests compile original project C code on the host, with undefined-behavior checks where configured. They do not execute manufacturer firmware.

Tests that require official firmware, private device captures, historical build manifests or an unavailable SH cross compiler explicitly skip. A skipped test is not a passing hardware validation. Do not upload those fixtures to make CI run more checks. Optional analysis dependencies are listed in `requirements-analysis.txt`.

Before publication the full private suite passed 384 Python tests. The clean-checkout test results and fresh release rebuild are recorded in the publication validation file. These are local checks, not a performance benchmark or recovery proof.

## On-player acceptance

Only after reading [compatibility](compatibility.md) and [recovery](recovery.md), and choosing to install:

1. Confirm the empty deck shows `Custom XDJ v1` and the numeric version remains 1.44.
2. Browse analyzed tracks: verify the 80 px preview stays clear of the note/title, with INFO open and closed.
3. Check Blue and RGB preferences. Compare recognizable whole-track structures with the loaded-track overview.
4. Open INFO: the bottom band should be horizontal and free of comment text. Change selection and leave/re-enter the list.
5. With a LINK master available, compare the green row indication to the stock key compatibility display. Record whether it updates after a master/key change.
6. Play a track and progressively exercise scrolling, loading, source changes, sorting, search, loops and cues. Report missing rows, stuck previews, audio interruption or recovery steps separately. Stop if abnormal behavior persists.

A report should include exact model, installed version, custom build marker, USB/source type, approximate playlist size and reproducible actions. Remove serial numbers, network addresses and track metadata from shared images. Never attach firmware or exported databases.

Successful normal playback and update entry do not establish guaranteed recovery from a corrupted application.
