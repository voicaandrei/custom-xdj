# Recovery: what is known and what is not

**There is no verified rescue from every bad application state in this project.** An unchanged boot/updater image and successful updates on a healthy player are useful evidence, but do not prove recovery from a checksum-valid application that hangs before update mode is available.

## Recorded observations

- The owner entered stock update mode on the test unit and returned to normal operation before firmware insertion.
- Subsequent experimental updates completed on that same unit and it continued to boot.
- The accepted FINAL16 functionality was reported to work correctly.
- Local audits show that boot, the standalone updater region and PANEL bytes are unchanged from official 1.44.

These statements do **not** establish a board-level restore procedure, a complete flash backup, downgrade compatibility or independence of update mode from every application failure.

## Before another unit is modified

Keep a verified official update and a clear service/restore plan for the exact unit. Understand that the modification is persistent and can require professional service if the stock updater is unavailable. Do not use an irreplaceable show-critical unit for an experiment.

Do not intentionally corrupt firmware to test rescue. Do not apply UART pinouts, voltage assumptions, loaders or update formats from a CDJ-2000, RX3 or CDJ-3000. The PCB revision of the original test unit was not established, and no enclosure opening was performed.

## If something goes wrong

- If the update is in progress: do not remove power or storage; follow the manufacturer's instructions.
- If normal boot and stock update mode still work: retain a clear record of the installed file and use the manufacturer-supported stock update procedure where accepted.
- If the updater is not reachable or the unit fails to boot: stop. This repository does not provide a verified external USB recovery exploit or hardware rescue recipe. Seek qualified service with the exact model and installed file information.
- If a USB drive will not mount on the computer: do not format it as part of this project. Preserve the data and diagnose storage separately.

For contributors, claims such as “unbrickable,” “RAM-only,” “power-cycle to stock” or “guaranteed recovery” are incorrect for this release.
