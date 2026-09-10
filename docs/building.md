# Building Custom XDJ v1

The supported entry point builds from your own official XDJ-1000MK2 **1.44** update and refuses any different hash. No firmware is downloaded automatically by this entry point, sent to a service or copied to USB.

## Prerequisites

- Python 3.9+ without `-O` (low-level assertions must remain active).
- A host C compiler available as `cc` and standard build tools.
- **GCC 14.2.0 targeting `sh-elf`**, with **GNU binutils 2.43**.
- Node.js 22+ for the optional demo and JavaScript tests.
- Several GB of free space if building the toolchain from source; considerably less for the project alone.

The release was built on macOS. The clean-source tests also run in Linux CI; the exact release build must match the published hash regardless of host. Windows native tooling is not validated. Do not force through a hash failure caused by a different compiler.

`build_sh.py` searches `$HOME/.local/sh-elf/bin` first and then PATH. It needs `sh-elf-gcc`, `sh-elf-nm`, `sh-elf-size`, and binutils tools including `ld`, `objcopy`, `readelf` and `objdump` in the same tool directory. The project uses `-m4a-nofpu -ml`: SH-4A, little endian, no floating-point code in its own extension.

### Toolchain reference configuration

Use official [GNU GCC](https://gcc.gnu.org/releases.html) and [GNU binutils](https://www.gnu.org/software/binutils/) sources and their published verification instructions. Do not run scripts extracted from player firmware or an unrelated device project.

The tested GCC configuration was:

```sh
../gcc-14.2.0/configure --target=sh-elf --prefix="$HOME/.local/sh-elf" \
  --disable-nls --enable-languages=c --without-headers --with-newlib \
  --disable-libssp --disable-libgomp --disable-libquadmath \
  --disable-libatomic --disable-threads --disable-shared --with-system-zlib
```

Build/install target binutils first, put its `bin` directory on PATH, then build `all-gcc` and install `install-gcc` from a separate GCC build directory. Follow GNU's prerequisite instructions for GMP, MPFR and MPC. This is a freestanding compiler setup; no player SDK or proprietary headers are required. The flags above record the tested configuration rather than promise a complete package-manager recipe for every host.

## Supply the official update

Obtain `XDJ1000MK2_v144.zip` or its `XDJ1KMK2.UPD` from an official manufacturer source you are entitled to use. The [manufacturer firmware download page](https://support.alphatheta.com/en-US/articles/4404821857945) may show a newer version; **1.45 is not supported by this patch**. If official 1.44 is unavailable, stop rather than substitute another version or a third-party binary.

Keep an untouched official update offline for stock return. Do not share it through GitHub issues or releases.

```sh
git clone https://github.com/voicaandrei/custom-xdj.git
cd custom-xdj
python3 scripts/build_release.py --firmware /path/to/XDJ1000MK2_v144.zip
```

The same command accepts the extracted `.UPD`. It will:

1. Verify the official 1.44 update hash and container.
2. Extract and checksum the MAIN/PANEL images into ignored `private/`.
3. Build the frozen FINAL16 base and verify its exact application/update hashes.
4. Apply only the `Custom XDJ v1` text change, preserving the accepted runtime code.
5. Repack and validate the update, with stock boot/updater/PANEL retained.
6. Refuse to announce success unless the output matches the published release hash.

No original or conflicting local candidate is silently overwritten. Existing exact outputs can be verified again. A partial or mismatched candidate directory must be moved aside manually before rebuilding; do not disable the guard.

## Output

```text
private/custom-xdj-v1-v144/XDJ1KMK2.UPD
private/custom-xdj-v1-v144/application.bin
private/custom-xdj-v1-v144/manifest.json
```

Expected update SHA-256:

```text
ce23b4f3d198f5066bc6861223d249d9c66d979b5f0af54a0d32e8e2cb0671f6
```

Use `shasum -a 256` on macOS or `sha256sum` on Linux. Keep the manifest locally. The public entry point does not need the original owner's exports, private acceptance records or earlier beta output folders.

`requirements-analysis.txt` contains optional static-analysis dependencies. They are not required merely to build the release. Old beta/audit scripts are retained for research and may require private artifacts; they are not the supported installation path.
