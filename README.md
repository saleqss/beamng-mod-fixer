# 🚗 GBEAM FIX: Ultimate Global Mod Fixer, Auto-Installer & Graphics Optimizer for BeamNG.drive

[![CI](https://github.com/saleqss/beamng-mod-fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/saleqss/beamng-mod-fixer/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-288%20passed-brightgreen)](https://github.com/saleqss/beamng-mod-fixer)
[![BeamNG Compatibility](https://img.shields.io/badge/BeamNG.drive-0.30%20--%200.34%2B-orange)](https://beamng.com)

> **The all-in-one community standard toolkit for BeamNG.drive (0.30 - 0.34+).** Automatically resolves **all major mod breakages** after game updates: pitch-black headlights, rear white spotlight bug on headlights, blinding nuclear-red brake discs, weak highbeams, orange `"NO TEXTURE"` (including nested mod folder unwrapping), obsolete `materials.cs`, frozen vehicles & exploding differentials, tire blowouts (`pressurePSI`), silent engines & pre-FMOD audio crashes, and fatal vehicle Lua errors. Features a **background Downloads auto-installer**, 4 tailored graphics presets with **automatic ReShade preset deployment** (Medium 60FPS Optimal, Low Fast, Potato Boost, Ultra Photoreal), and a clean bilingual interface.

*Читать на русском языке: [README_RU.md](README_RU.md)*

---

```text
╔════════════════════════════════════════════════════════════════════════════════════════╗
║   ██████╗ ██████╗ ███████╗ █████╗ ███╗   ███╗   ███████╗██╗██╗  ██╗                    ║
║  ██╔════╝ ██╔══██╗██╔════╝██╔══██╗████╗ ████║   ██╔════╝██║╚██╗██╔╝                    ║
║  ██║  ███╗██████╔╝█████╗  ███████║██╔████╔██║   █████╗  ██║ ╚███╔╝                     ║
║  ██║   ██║██╔══██╗██╔══╝  ██╔══██║██║╚██╔╝██║   ██╔══╝  ██║ ██╔██╗                     ║
║  ╚██████╔╝██████╔╝███████╗██║  ██║██║ ╚═╝ ██║   ██║     ██║██╔╝ ██╗                    ║
║   ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝   ╚═╝     ╚═╝╚═╝  ╚═╝                    ║
║                                                                                        ║
║               ⚡ ULTIMATE GLOBAL MOD FIXER & GRAPHICS OPTIMIZER v1.3.0 ⚡               ║
║                 BeamNG.drive 0.30 - 0.34+ Adaptive Community Standard                  ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⚡ Instant Install & Quick Launch

### 1. Install via Git (One Command)
Install directly from GitHub via `pip`:

```bash
pip install git+https://github.com/saleqss/beamng-mod-fixer.git
```

*Alternatively, clone and install in editable mode:*
```bash
cd C:\path\to\workspace
git clone https://github.com/saleqss/beamng-mod-fixer.git
cd beamng-mod-fixer
pip install -e .
```

### 2. Launch Anywhere via Terminal
Open **PowerShell**, **Command Prompt**, or **Terminal** and enter:

```bash
agy-gbeam-fix
```

*(Registered quick aliases: `gbeam-fix` and `agy-beam`)*

---

## 🌐 Full Scope of Problems Solved by GBEAM FIX v1.3.0

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               GBEAM FIX REPAIR DOMAINS                                 │
├────────────────────────┬───────────────────────────────────────────────────────────────┤
│ 💡 Front Headlights    │ Pitch-black lowbeams (bumper self-shadowing), dim highbeams   │
│                        │ (boosted to 120m), inverted cone angles, 404 missing cookies   │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🚨 Rear Lights Balance │ Eliminates white rear light bug (template inheritance fix),   │
│                        │ eliminates blinding red discs with soft ambient road wash     │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🎨 Materials & Textures│ Orange "NO TEXTURE", unwraps nested archive wrapper folders,  │
│                        │ converts materials.cs to JSON 1.5 PBR, normalizes VFS paths   │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ ⚙️ Physics & Drivetrain│ Vehicle freeze on spawn, differential explosion, viscous      │
│                        │ coupling clamp (>10000), tire blowouts on spawn (PSI <= 0)    │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🔊 Audio & Sound       │ Modernizes legacy art/sound/* paths to official BeamNG FMOD   │
│                        │ sound events (fixes silent engines and FMOD engine errors)    │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🛡️ Lua Script Guard    │ Guards deprecated v.data & obj:queueGameEngineLua calls,      │
│                        │ preventing fatal UI and gauge script crashes on vehicle spawn │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🖥️ UI & Loading Fixer  │ Resolves "UI error while loading", neutralizes rogue loading.js│
│                        │ overrides, repairs malformed info.json, unpacks container zips│
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ ⚡ Auto-Installer      │ Background Downloads watcher: detects new mods, unwraps,      │
│                        │ moves to mods/, and executes 7-stage repair on the fly        │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🚀 Graphics & FPS      │ 4 presets: Ultra-Max-FPS (100% Ultra, no blur, smart 3-face), │
│                        │ Medium-60FPS, Low-Weak, Potato-Ultra-Weak for weak laptops    │
└────────────────────────┴───────────────────────────────────────────────────────────────┘
```

---

## 💡 Lighting Calibration & Balance: White Rear Lights & Nuclear Red Discs Solved

### 1. The White Rear Light Bug (Template Inheritance)
In BeamNG's JBeam parser, table rows inside `props` inherit any unassigned property from the preceding template dictionary. Mod authors frequently defined a reverse light template with white color:
```json
{"lightColor": {"r": 255, "g": 255, "b": 255, "a": 255}}
```
Followed by taillights or `lowhighbeam` rows that omitted `lightColor`. Consequently, turning on the car's headlights caused the rear to blast an intense **white spotlight onto the ground**!
> **GBEAM FIX Resolution**: Injects an explicit, calibrated `lightColor` into every rear lamp row:
> - Taillights & brake lights: rich red `{"r": 255, "g": 20, "b": 20, "a": 255}`
> - Reverse lights: warm white `{"r": 255, "g": 250, "b": 220, "a": 255}`
> - Turn signals: amber `{"r": 255, "g": 140, "b": 15, "a": 255}`

### 2. Eliminating Blinding Nuclear-Red Discs on the Road
Crude brightness values ($0.85 - 1.2$) combined with linear attenuation produced hard-edged, oversaturated glowing red discs on the pavement.
> **GBEAM FIX Resolution**:
> - Taillight brightness calibrated to natural `0.12`
> - Brake light brightness balanced at `0.35`
> - Quadratic attenuation injected: `lightAttenuation: {"x": 0, "y": 1, "z": 2}` for smooth road illumination without hard circular edges
> - Shadow casting disabled (`lightCastShadows: false`) to avoid rear bumper occlusion artifacts.

### 3. Penetrating Highbeam Boost (No More Weak Highbeams)
Mods often had highbeams that cut off at 3-5 meters like weak flashlights. GBEAM FIX automatically boosts underperforming highbeams:
- Distance: `lightRange: 120.0m`
- Brightness: `lightBrightness: 2.2`
- Outer angle: `lightOuterAngle: 55.0°`

---

## 🎨 Materials Doctor: Fixing Orange "NO TEXTURE"

1. **Unwrapping Nested Folders**: Many mod archives contain a root wrapper folder (e.g. `SuperCar_v1/vehicles/...`). The game's PhysFS virtual file system fails to find files at this depth and shows orange placeholder textures. GBEAM FIX automatically detects and strips this prefix, restructuring the archive cleanly to `vehicles/...`.
2. **TorqueScript `materials.cs` to JSON 1.5 Converter**: Migrates old materials to the modern PBR 1.5 format.
3. **VFS Path Normalization**: Converts Windows backslashes `\` to standard `/`.
4. **Texture Format Reconciler**: Automatically maps `.png` references to optimized `.dds` files if present.

---

## 🖥️ UI & Loading Screen Error Fixer: "UI error while loading" Cured

### 1. Root Cause Analysis
A widespread error dialog after game updates or installing older community mods:
> *"UI error while loading. Try launching the game in Safe Mode (mods disabled)."*

When inspecting the CEF boot log (`%LOCALAPPDATA%/BeamNG/BeamNG.drive/current/beamng.log`):
```text
69.34520|W|CEF.MainGEUI#local://local/ui/entrypoints/main/boot.js:326| Timed out while waiting for readiness checks on () => engineReady
69.34526|E|CEF.MainGEUI#local://local/ui/entrypoints/main/boot.js:280| Error: Timed out while waiting for readiness checks
```

**Why this occurs**:
1. **Rogue UI Overrides in Vehicle Mods**: Ancient vehicle mods (such as `hachiimpreza2.zip` and others created for BeamNG 0.5 - 0.14) bundled copies of the game's old loading screen: `ui/modules/loading/loading.js` (written in AngularJS 1.x). When mounted by PhysFS, this obsolete file overwrites BeamNG 0.30+'s modern Vue loading screen, preventing the game engine from receiving the modern `engineReady` event. After 60 seconds, CEF times out and halts the game.
2. **Malformed `info.json` Files**: Mod archives frequently contain syntax errors (trailing commas, unquoted keys, C++ comments `//`, single quotes), crashing the vehicle selector indexer in CEF.
3. **Container ZIP Packs**: Mods packaged as `*_UNZIP.zip` contain inner `.zip` archives that BeamNG cannot mount directly.
4. **Stale CEF Cache**: Corrupted Chromium cache files lingering in `temp/cef/` and `temp/ui/`.

### 2. GBEAM FIX Solution
- **Neutralizes Rogue UI**: Identifies and safely strips `ui/modules/loading/loading.js` and rogue `ui/entrypoints/*` files from mod archives without affecting custom vehicle dashboard displays or gauges.
- **Repairs `info.json`**: Strips comments, single quotes, unquoted keys, control characters, and trailing commas, restoring full RFC 8259 JSON compliance.
- **Unpacks Container Archives**: Automatically unpacks nested `.zip` bundles into valid single mod archives.
- **Purges CEF Cache**: Safely purges `temp/ui/`, `temp/cef/`, and `temp/cef_cache/` without touching vehicle configurations (`.pc`).

## ⚡ Background Mod Auto-Installer & Downloads Watcher

GBEAM FIX features the `ModWatcher` background service:
1. Continuously monitors your `~/Downloads` directory.
2. Waits for browser write completion (ignores `.crdownload`, `.tmp`, `.part`).
3. Inspects internal archive signatures to confirm genuine BeamNG content (`vehicles/`, `levels/`, `art/`, etc.).
4. Automatically unwraps nested wrapper folders and moves the `.zip` to `%LOCALAPPDATA%/BeamNG/BeamNG.drive/current/mods/`.
5. **Immediately runs the full 7-stage repair pipeline on the fly**!

Activate via Menu option **`W`** or run standalone from terminal with **`--watch`**.

---

## 🚀 4 Tailored Graphics Presets

| Preset | Description | Target Hardware |
|---|---|---|
| **`ultra-max-fps`** (Default) | 100% Max Ultra: 1024px cubemaps, 4x shadows, 16x AF, smart 3-face reflection boost | High-end PCs / RTX / 2K-4K / Maximum visuals |
| **`medium-60fps`** | Balanced 60 FPS sweet spot without microstutters | Mid-range gaming rigs |
| **`low-weak`** | Entry-level GPU optimizations with reduced particles and shadows | Budget GPUs / GTX |
| **`potato-ultra-weak`** | Extreme performance boost for integrated GPUs & weak laptops | iGPUs / Low-spec laptops |

Automatic `.bak` backups are created in `settings/` before any change and can be restored in 1 click.

---

## 🖥️ Interactive Terminal Menu

Run `agy-gbeam-fix`:

```text
MAIN CONTROL MENU (ГЛАВНОЕ МЕНЮ):
  1. 🚀 1-Click Global Fix (Optics + Textures + UI Errors + Physics + Audio + Lua + Graphics + Cache)
  2. 💡 Headlights & Optics Studio (Low/high beam balance, angle repair, cookie modernizer)
  3. 🎨 Materials & Texture Doctor (Fix NO TEXTURE, materials.cs -> 1.5 JSON, VFS paths)
  4. ⚙️ Drivetrain & Physics Repair (Fix frozen cars, differential explosion, tire PSI)
  5. 🔊 Sound & Lua Crash Guard (Modernize FMOD audio, guard deprecated lua APIs)
  6. 🚀 Graphics & FPS Optimizer (Ultra-Max-FPS, 60FPS-Balanced, Low, Potato presets)
  7. 🧹 Cache & Diagnostics Purge (DirectX/Vulkan shaders, vehicle binaries, temp files)
  8. 🖥️ UI & Loading Error Fix (Fix 'UI error while loading', clean CEF cache)
  9. 📋 Deep Mod Health Audit (Safe non-modifying dry-run scan with report)
  P. 📁 BeamNG Directory & Paths (Auto-detection & path validator across drives)
  W. ⚡ Mod Auto-Installer & Downloads Watcher
  L. 🌐 Change Language / Сменить язык (English / Русский)
  0. 🚪 Exit
```

- **1-Click Global Fix (Option 1)**: Runs all 7 repair stages, optimizes graphics, and clears cache. Opens the **Post-Fix Results Studio**, and option `1` or `Enter` returns cleanly to the Main Menu.
- **UI & Loading Screen Fixer (Option 8)**: Neutralizes rogue `loading.js` overrides, fixes `info.json` syntax, unpacks container archives, and clears CEF cache.
- **Language Toggle (Option L)**: Instantly toggles between English and Russian, persisted in `~/.beamng_mod_fixer/config.json`.
- **Clean Typography**: Bracket-free design without bracket spam.

---

## 🛠️ CLI Usage & Flags

```bash
# 1-Click Global Fix (All 7 repair stages + graphics + cache clean)
agy-gbeam-fix --all

# Fix UI loading screen errors and purge CEF cache
agy-gbeam-fix --fix-ui --clean-cef

# Unpack container ZIP archives (*_UNZIP.zip)
agy-gbeam-fix --unpack-containers

# Launch background Downloads watcher for automatic installation and repair
agy-gbeam-fix --watch

# Select interface language
agy-gbeam-fix --lang en
agy-gbeam-fix --lang ru

# Deploy graphics preset
agy-gbeam-fix --optimize-graphics --preset ultra-max-fps
agy-gbeam-fix --optimize-graphics --preset medium-60fps
agy-gbeam-fix --optimize-graphics --preset potato-ultra-weak

# Deploy custom ReShade presets (Medium Optimal, Low Fast, Potato Boost, Ultra Photoreal)
agy-gbeam-fix --deploy-reshade medium-optimal
agy-gbeam-fix --deploy-reshade ultra-photoreal

# Display detected paths and active status
agy-gbeam-fix --show-paths

# Purge shader caches (.d3dcsx, .db)
agy-gbeam-fix --clean-cache

# Safe non-modifying simulation (Dry Run)
agy-gbeam-fix --all --dry-run
```

---

## 🧪 288 Automated Quality Tests

Backed by a rigorous test suite of **288 automated tests** across 5 tiers:

```bash
python -m pytest -v
```

- Verification of rear light calibration, template inheritance isolation, and quadratic attenuation falloff.
- Verification of nested wrapper unwrapping and VFS separator normalization.
- Verification of background `ModWatcher` file stability and auto-repair.
- Verification of ReShade preset deployment, AMD FidelityFX CAS injection, and color balancing.
- Full adversarial robustness against corrupt, locked, password-protected, and 6MB+ JBeam files.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
Enjoy driving in BeamNG.drive!
