# Installation

Read [compatibility](compatibility.md) and [recovery limitations](recovery.md) first. This project changes internal MAIN firmware persistently. It is not a removable USB skin. It has one owner's acceptance, not manufacturer certification, and a failure may require service.

## Before updating

- Confirm **XDJ-1000MK2** on the player and **1.44** in MENU/UTILITY → VERSION No.
- Build from your own exact official 1.44 update using [Building](building.md). Verify the generated SHA-256.
- Keep an untouched official update offline. Do not put modified and official files with ambiguous names in the same USB root.
- Use a player and time slot where an interruption is acceptable. Stop playback before updating and use reliable power.
- Preserve your USB contents. This procedure does not require deleting music or formatting a working export.

## Prepare the USB

Copy the generated `XDJ1KMK2.UPD` to the USB root. If a previous project update is there, move it to a clearly named archive directory first. Do not overwrite an unknown existing file. Recompute the hash of the file **on the USB**, then eject the volume properly.

Custom XDJ v1 SHA-256:

```text
ce23b4f3d198f5066bc6861223d249d9c66d979b5f0af54a0d32e8e2cb0671f6
```

If the computer cannot mount the volume, stop copying. Do not format or automatically repair it as an installation shortcut. That is a separate storage problem.

## Run the update

Use the manufacturer's [XDJ-1000MK2 update guide](https://www.pioneerdj.com/-/media/pioneerdj/downloads/firmwares/players/xdj-1000mk2/xdj-1000mk2_updateguide-en.pdf) for the physical update sequence:

1. Power the player off. Remove USB storage and disconnect LINK and the USB computer connection.
2. Hold **IN** and **RELOOP/EXIT** while turning the power on.
3. When prompted for USB storage, insert the prepared drive into the top USB port.
4. Follow the on-screen update instructions. Do not interrupt an update in progress or remove power/storage.
5. Wait for the completion instruction, then restart as directed.

The custom container uses the exact MK2 same-version update marker identified during research; the numeric version remains **1.44**. Do not use a one-second completion message alone as proof that the desired application was installed.

## Check the result

Without a loaded track, look for **Custom XDJ v1**. Then run the short [on-player acceptance check](testing.md#on-player-acceptance): browser/INFO previews, no overlap, color preference, normal playback and navigation.

If the expected marker is absent, record what the screen actually shows and recheck the file hash. Do not keep cycling through unrelated beta files. If browsing becomes empty or unresponsive, stop the experiment and document it; do not use the player for a show until resolved.

## Returning to stock

If the stock update mode is still reachable, follow the manufacturer's procedure with your untouched official update. A refusal to update or a player that cannot reach the updater is not solved by this repository. See [Recovery](recovery.md); there is no proven software rescue for every application failure.
