# FHD_Nanotech V26 + FHD_Nanogenesis v0.9 — recovered review sources

Пакет для GitHub и проверки модераторами: **72 файла**, оба модуля и вся присланная графика. Все **525 рабочих файлов** восстанавливаются побайтово точно. Исходники уже подготовлены; ручное восстановление ресурсов или RSON на вашем ПК не требуется.

## Included content

Recovered from `FHD_Nanotech_v0.3-V26 + FHD_Nanogenesis_v0.9(1).zip`, 113,827,325 bytes. Input SHA-256: `b80daeededff25f2d020acde9aaaab5485c5daba9ddd3e98572ed092aa97c2e5`. Both original metadata files credit **Prolog_D**.

| Supplied runtime type | Files | Editable source |
| --- | ---: | --- |
| DAT | 6 | `source/modules/*/CFG/*.json` and `CFG/Rus/Lang.json` |
| ModuleInfo | 2 | UTF-8 text in each source module |
| GI | 434 | PNG layer atlases and typed graphics catalogs |
| GAI | 51 | PNG layers, original frame/sequence data and typed catalogs |
| HAI | 32 | Indexed hull-frame sheets, palettes and typed headers |
| Total | 525 | Complete supplied runtime set |

No DLL, EXE or SCR was supplied; the game script text is embedded in the editable configuration JSON. There is no visual RScript project to recover for this release, so no RSON is needed. These are recovered editable sources, not a claim that the author's original working directory was supplied.

`FHD_Nanogenesis` depends on `FHD_Nanotech`, as declared in its unchanged metadata. The original priorities remain 5 and 6. The main metadata describes levels 0–20, twenty talents and selections at levels 5/10/15/20; Nanogenesis describes eight appearances unlocked at levels 2/5/8/10/12/15/18/20. These are retained release descriptions, not newly executed gameplay results.

## Source organization and file limit

The source repository contains **45 PNG atlases** and **six graphics JSON catalogs**, instead of 517 separate native graphics files. Together with the configs, metadata, tools and reports, this stays within the requested **100-file limit**. Every individual source file is smaller than 20 MiB. No runtime resource, variant or appearance was discarded to achieve the limit.

- `source/modules/`: lossless DAT JSON and metadata for both modules.
- `source/modules.json`: original module names and output encodings.
- `source/graphics/atlases/`: lossless RGBA PNG sample/layer sheets.
- `source/graphics/assets_01.json` … `assets_06.json`: original output paths, headers, dimensions, atlas rectangles, packet layout, animation and ship-frame data.
- `scripts/artwork.py`: pixel conversion, atlas access and GI/GAI/HAI reconstruction.
- `scripts/gi_codec.py`, `scripts/dat_codec.py`: typed binary serializers.
- `build.py`, `tests/verify.py`: full build and isolated verification.
- `original-file-sha256.json`, `build-verification.json`, `source-recovery.json`: original hashes, actual checks and recovery inventory.

The source ZIP contains no original upload, generated install ZIP, game DAT/GI/GAI/HAI files, caches or git history. PNGs hold actual pixel samples; no original binary resource, Base64 blob or compressed native image payload is used as a build input.

## Graphics recovery details

Standalone GI files use type 0 or type 2. RGB565 samples are expanded to reversible 8-bit RGB values in PNG. The JSON preserves bounds, masks and the original RLE packet commands, including skips and row endings. Type-2 opaque/color layers and the six-bit transparency layer are stored separately; the transparency layer uses a grayscale coverage representation. Raw ARGB8888 GI samples retain their channels losslessly.

All **3,156 GAI frames** are type-2 GI resources wrapped in `ZL01`/zlib. The builder reconstructs each frame, then regenerates its original level-9 compressed payload and the GAI frame directory, sequence references, timing and reserved values. All uploaded compressed bytes match after rebuilding in the recorded environment.

All **32 HAI files** contain 8-bit indexed frames with 1,024-byte palettes. Their **2,400 frames** are stored in source sheets with ten frame columns. Index samples are grayscale values; palette samples preserve the four original bytes per entry. Typed headers retain dimensions, pitch, frame count, stride and masks. The builder automatically restores the original per-frame index-plane/palette ordering.

The atlases are layer/index sources rather than flattened screenshots. Color and transparency samples can be edited in the PNGs; geometry, masks, packet layout, frame ordering and timing live in JSON. Adding/removing painted regions, resizing frames or changing layout requires corresponding source metadata changes. No such edit is needed to reconstruct the supplied version, and this recovery did not change its artwork or layout.

## Build and GitHub automation

Verified environment: Python **3.12.14**, numpy **2.3.5**, Pillow **12.3.0**, zlib **1.3.2**. No game installation, Windows, native compiler or external editor is required to build the original files.

```sh
python3 -m pip install -r requirements.txt
python3 tests/verify.py --report dist/verification.json
python3 build.py --verify-original
```

Output: `dist/FHD_Nanotech-Nanogenesis-install.zip`, containing the two original module trees below `Mods/FHD_MODS/`. It restores all 525 runtime files automatically. The 100-file limit applies to the GitHub source package; the generated game install ZIP must retain the original runtime paths and therefore contains the original 525 files.

GitHub Actions runs verification, builds both modules and publishes the install ZIP plus a fresh report as a downloadable artifact. For intentional source edits, omit `--verify-original`, which enforces the original uploaded hashes. PNG encoding itself does not affect runtime bytes, but a different zlib implementation can change compressed DAT/GAI output. The strict original-byte check detects such differences.

## Verification and limits

`build-verification.json` records **22 passing verification checks**. They include a rebuild from a temporary directory containing only the source inputs/scripts, SHA-256 equality for every one of the 525 original files, complete DAT/GI parsing, decompression and validation of all GAI frames, HAI header/frame validation, metadata encodings and dependency/priority preservation. All **479 literal local resource references** resolve, with no missing files found. Source PNG/catalog counts and the file/size limits are also checked.

Metadata remains UTF-16LE with its original BOM and line endings in the generated game files. Block order, repeated entries, sort metadata, encryption seeds and script strings are retained. Both metadata files advertise Russian/English; the upload contains only `CFG/Rus/Lang.dat`. No translation or English payload was invented.

No game interpreter, live UI, ship renderer, progression/talent system or save/load session was executed. Exact reconstruction proves fidelity to the supplied archive; it does not prove gameplay correctness. No specific Nexus moderator checklist was attached and moderation approval is not implied.

The DAT codec reimplements the format used by Sergei Osminin's MIT-licensed rangers-utils. GI/GAI/HAI layout was checked against the existing local game-structure research. This recovery does not claim authorship of the original mod or assign it a new license; no original mod license file was supplied.
