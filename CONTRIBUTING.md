# Contributing

Start with the README, compatibility matrix and research evidence boundaries. Write public documentation, issue reports and user-facing text in English.

Keep changes narrowly scoped. Preserve exact firmware hashes and expected-byte checks; never make an unknown image pass by weakening validation. Record every binary address with its image SHA-256 and address space. Keep original firmware, derived binaries and user exports under ignored `private/` paths.

Run both test commands in [Testing](docs/testing.md). Add meaningful synthetic regression coverage for parser, bounds or state-machine fixes. Explain unavailable private checks and separate local checks from owner-reported device results. Do not silently modify frozen release sources: a new implementation needs a new version and output hash.

Issues and pull requests must not contain firmware, keys, copyrighted tracks, databases, serial numbers or raw packet captures. Share a minimal synthetic reproducer and redacted observations. Never ask another user to intentionally corrupt firmware or test an unverified recovery route.

The supported builder is `scripts/build_release.py`. Historical probes are engineering artifacts, not installation instructions. No new model is supported until its own architecture, image, validation and recovery evidence are established.
