# 🚗 GBEAM FIX: Ultimate Global Mod Fixer & Graphics Optimizer for BeamNG.drive

[![CI](https://github.com/saleqss/beamng-mod-fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/saleqss/beamng-mod-fixer/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-251%20passed-brightgreen)](https://github.com/saleqss/beamng-mod-fixer)
[![BeamNG Compatibility](https://img.shields.io/badge/BeamNG.drive-0.30%20--%200.34%2B-orange)](https://beamng.com)

> **The all-in-one community standard toolkit for BeamNG.drive.** Automatically resolves **all major mod breakages** after game updates (0.30 - 0.34+): pitch-black headlights, orange `"NO TEXTURE"`, broken `materials.cs`, frozen vehicles & exploding differentials, tire blowouts (`pressurePSI`), silent engines & pre-FMOD audio crashes, and fatal vehicle Lua errors. Deploys cinematic high-FPS graphics presets and cleans corrupt shader caches.

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
║               ⚡ ULTIMATE GLOBAL MOD FIXER & GRAPHICS OPTIMIZER v1.1.0 ⚡               ║
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
git clone https://github.com/saleqss/beamng-mod-fixer.git
cd beamng-mod-fixer
pip install -e .
```

### 2. Launch Anywhere via Terminal
Open **PowerShell**, **Command Prompt**, or **Terminal** and enter any of the registered quick commands:

```bash
agy-gbeam-fix
```

*(You can also use `gbeam-fix` or `agy-beam`)*

---

## 🌐 Full Spectrum of Problems Fixed by GBEAM FIX

BeamNG.drive updates (0.30 through 0.34+) overhauled graphics, lighting, materials, and powertrain architectures. Legacy mods authored for older versions suffer from fatal breaks across six major domains:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                GBEAM FIX REPAIR DOMAINS                                │
├────────────────────────┬───────────────────────────────────────────────────────────────┤
│ 💡 Optics & Lighting   │ Self-shadow bumper blackout, inverted cone angles, cookie     │
│                        │ path 404s, obsolete flare names, missing emissive glow         │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🎨 Materials & Textures│ Orange "NO TEXTURE", legacy materials.cs -> 1.5 JSON,         │
│                        │ Windows backslash '\' path fixes, VFS texture reconciliation  │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ ⚙️ Drivetrain & Physics│ Physics freeze & car explosion, differential division by 0,   │
│                        │ viscousCoupling clamp (>10000), flat tire blowout (PSI <= 0)  │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🔊 Sound & Audio       │ Obsolete pre-FMOD sound paths (art/sound/*) modernized to     │
│                        │ official BeamNG FMOD events (eliminates silent engine spawn)  │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🛡️ Vehicle Lua Guard   │ Deprecated obj:queueGameEngineLua, unguarded v.data accesses, │
│                        │ preventing fatal script crash on vehicle spawn                │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 🚀 Graphics & FPS      │ 60FPS fast dynamic reflections (facesPerUpdate: 2, 512px),     │
│                        │ soft shadows without CPU draw-call spikes, shader purge       │
└────────────────────────┴───────────────────────────────────────────────────────────────┘
```

---

## 💡 The Physics Behind Headlight Breakage

### 1. Why Did Headlights Go Black?
In modern BeamNG (Torque3D Clustered Forward+ PBR), headlights cast dynamic shadows if `"lightCastShadows": true`. 
However, in 90% of vehicle mods, the spotlight's origin node sits slightly behind or inside the headlight 3D lens or front bumper mesh. As a result, **the car's own body casts a pitch-black shadow directly in front of the vehicle**, blocking the beam completely!

### 2. Why Blunt Fixers Broke Highbeams & Cockpits
Older third-party scripts bluntly replaced `lightCastShadows: true` with `false` everywhere. This caused:
- **Cockpit Blinding / Light Bleed**: Highbeams without shadow casting shine directly through the firewall and dashboard, completely washing out the driver's interior camera at night.
- **Lost Environmental Depth**: Highbeams lost realistic shadow casting behind roadside trees and buildings.

### 3. GBEAM FIX Smart Selective Solution
GBEAM FIX implements **context-aware selective fixing**:
- **Lowbeams & Fog Lights**: Set `lightCastShadows: false` (eliminates bumper self-shadow occlusion).
- **Highbeams**: Strictly **retains `lightCastShadows: true`** (preserves distance shadows and cockpit integrity).
- **Inverted Angles**: If `lightInnerAngle >= lightOuterAngle`, the Torque3D falloff equation divides by zero or evaluates negative, turning off the light. GBEAM FIX repairs the angle ratio to standard geometry.
- **Modern Cookies**: Replaces dead pre-PBR cookies (`art/shapes/lights/*`) with official `art/special/BNG_light_cookie_headlight.dds`.
- **Flare Modernization**: Updates legacy `headlightFlare` to official `vehicleHeadLightFlare`.

---

## 🎨 Materials & Texture Doctor: Eliminating Orange "NO TEXTURE"

In BeamNG 0.30+, the old TorqueScript `materials.cs` file is obsolete and often ignored by the engine. Unconverted mods spawn with the infamous orange-and-black grid "NO TEXTURE".

GBEAM FIX features a full **TorqueScript Parser & Modern PBR 1.5 Converter**:
1. **Automated Conversion**: Reads all `materials.cs` blocks (`diffuseMap`, `normalMap`, `specularMap`, `specularPower`, `translucent`) and creates modern `main.materials.json` with version `1.5`.
2. **VFS Path Normalization**: Replaces Windows backslashes `\` with forward slashes `/` and strips illegal leading slashes.
3. **Texture Reconciliation**: If a JSON file asks for `.png` but only `.dds` exists in the archive (or vice versa), GBEAM FIX automatically updates the path.
4. **Light Emissive Glow**: Ensures lighting materials (`headlight`, `taillight`, `brakelight`, `signal`, `glow`) have proper `emissiveFactor: [1, 1, 1]` so lights visibly illuminate when switched on!

---

## ⚙️ Drivetrain & Physics Repair: No More Frozen or Exploding Cars

1. **Differential Freeze**: Older mods defining `"gearRatio": 0` or missing ratios trigger a division by zero in the powertrain solver, causing the car to spawn frozen in place or fall through the map. GBEAM FIX restores standard ratios (e.g. 3.73).
2. **Viscous Coupling Explosion**: Several legacy mods have `viscousCoupling` stiffness set to $> 10000$. Under modern physics tick rates, this produces infinite acceleration (`inf` velocity) and tears the vehicle mesh apart instantly. GBEAM FIX clamps this safely to $250$.
3. **Flat Tires & Blowouts**: Missing or zero `pressurePSI` causes instant tire deflations or wheel explosion spikes. GBEAM FIX standardizes tire pressures to $30.0\text{ PSI}$ and normalizes extreme friction coefficients.
4. **Clutch Slip**: Zero or negative `clutchTorque` values are restored to standard $350\text{ N}\cdot\text{m}$.

---

## 🔊 Sound & Lua Crash Guard

- **Pre-FMOD Audio Modernizer**: Older mods pointing to raw `.wav` files in `art/sound/*` crash the sound engine with `Audio: event not found`. GBEAM FIX modernizes sound paths to official BeamNG FMOD events (`event:>Engine>default`).
- **Vehicle Lua Crash Guard**: Automatically guards legacy vehicle dashboard and gauge Lua scripts by injecting safety preambles for `v.data` and wrapping deprecated `obj:queueGameEngineLua` calls with defensive fallbacks.

---

## 🚀 Graphics & FPS Optimizer (Ultra Visuals + 60FPS Reflections)

Dynamic reflections in BeamNG update 6 cubemap faces every frame by default. On many systems, this drops frame rates by 30-50%!

GBEAM FIX provides tailored, balanced presets:

| Preset | Dynamic Reflections | Reflection TexSize | Dynamic Mirrors | Shadow Tuning | Target Hardware |
|---|---|---|---|---|---|
| **`cinematic-fast`** (Default) | 2 faces / update | 512 px | 512 px (1 face) | Soft High, balanced cascades | High-end / 60-144 FPS smooth |
| **`balanced`** | 2 faces / update | 512 px | 512 px (1 face) | High, standard decals | Mid-range PCs |
| **`performance`** | Off / 1 face | 256 px | 256 px | Normal shadows, optimized grass | Budget / Laptops |

- **Automatic Backup**: Creates timestamped `.bak` copies in your settings folder before touching anything.
- **Easy Restore**: Restore original settings with one keypress from the interactive menu.

---

## 📁 High-Performance Automatic Path Discovery & Caching

GBEAM FIX automatically and instantly finds your BeamNG.drive installation, even on customized multi-drive configurations, secondary game SSDs, or portable setups:

1. **AppData Version Topology**: Automatically scans `%LOCALAPPDATA%\BeamNG\BeamNG.drive\` across all version subdirectories (`current`, `latest`, `0.34`, `0.33`, `0.32`, `0.31`, `0.30`, etc.), intelligently scoring and picking the most active folder (favoring folders with active mod archives, recent game launch logs like `beamng.log`, and newest modification time).
2. **Windows Registry Steam Discovery**: Queries `HKCU\Software\Valve\Steam` and `HKLM\SOFTWARE\Valve\Steam` to locate Steam, parses `libraryfolders.vdf` across all installed library drives for Steam App ID `284160`, inspects `appmanifest_284160.acf` for exact `installdir`, and parses `startup.ini` for custom `UserPath` redirections.
3. **Multi-Drive Scanning**: Windows native sub-millisecond logical drive bitmask enumeration (`GetLogicalDrives`) with optical/CD-ROM filtering and error suppression, rapidly searching game paths on secondary drives (`D:\`, `E:\`, `F:\`... `BeamNG.drive`, `Games\BeamNG.drive`, `SteamLibrary`).
4. **0ms Instant Persistent Cache**: Saves verified paths to `%LOCALAPPDATA%\BeamNGModFixer\config.json` (or `~/.beamng_fixer_paths.json`) with atomic `.tmp` swap. Subsequent runs resolve paths in **0ms** without re-scanning.
5. **Interactive Management & CLI Overrides**: View, customize, or validate directories via Menu Option `[9]` or via CLI flags (`-u`, `--user-dir`, `-m`, `--mods-dir`, `--show-paths`, `--save-paths`).

---

## 🖥️ Interactive Hierarchical Menu

Run `agy-gbeam-fix` without arguments in an interactive terminal to enter the full control suite:

```text
MAIN CONTROL MENU (ГЛАВНОЕ МЕНЮ):
  [1] 🚀 ГЛОБАЛЬНЫЙ ФИКС В 1 КЛИК (1-Click Global Fix) (Оптика + Текстуры + Физика + Звук + Lua + Графика + Кэш)
  [2] 💡 Headlights & Optics Studio (Smart Fix, Angle repair, cookie modernizer)
  [3] 🎨 Materials & Texture Doctor (Fix NO TEXTURE, materials.cs -> 1.5 JSON, VFS paths)
  [4] ⚙️ Drivetrain & Physics Repair (Fix frozen cars, differential explosion, tire PSI)
  [5] 🔊 Sound & Lua Crash Guard (Modernize FMOD audio, patch obsolete lua APIs)
  [6] 🚀 Graphics & FPS Optimizer (Cinematic-Fast, Balanced, Maximum-FPS presets)
  [7] 🧹 Cache & Diagnostics Purge (DirectX/Vulkan shaders, vehicle binaries, temp files)
  [8] 📋 Deep Mod Health Audit (Safe non-modifying dry-run scan with report)
  [9] 📁 Change / View BeamNG Directory & Paths (Multi-drive auto-detection & path validator)
  [0] 🚪 Exit
```

- **Unified 1-Click Pipeline (Option [1])**: Executes all 7 repair and optimization stages in one seamless pipeline: Headlights & Optics, Materials Doctor, Drivetrain & JBeam Physics, Sound Modernizer, Lua Safety Guard, Cinematic-Fast Graphics Preset, and DirectX/Vulkan Shader Cache Purge. Complete status and freed disk space are reported in real time.
- **Two-Way Studio Navigation**: Executing any repair pass automatically transitions to the **Fix Results & Diagnostic Studio**, displaying live metric counters, detailed file-by-file notices, and instant 1-click return (`[1]` or Enter) to the Main Control Menu.
- **Adaptive Multi-Pass Engine**: Automatically applies fallback heuristics if non-standard mod configurations or conflicting definitions are detected, guaranteeing a 100% playable vehicle state.

---

## 🛠️ Command-Line Arguments & Automation

For headless execution, server scripts, or batch operations:

```bash
# 1-Click Global Fix (All 7 repairs + graphics + cache)
agy-gbeam-fix --all

# Display detected BeamNG paths, status, and mod count
agy-gbeam-fix --show-paths

# Save custom directory configuration permanently to 0ms persistent cache
agy-gbeam-fix --mods-dir "D:/BeamNG_Mods" --save-paths

# Specify custom BeamNG user data directory
agy-gbeam-fix --user-dir "%LOCALAPPDATA%/BeamNG/BeamNG.drive/0.34" --all

# Specify custom mods folder override
agy-gbeam-fix --mods-dir "D:/BeamNG_Mods" --all

# Fix mods only (Headlights, Materials, Drivetrain, Sounds, Lua)
agy-gbeam-fix --fix-mods

# Materials & Texture Doctor only
agy-gbeam-fix --fix-materials

# Drivetrain & Physics Repair only
agy-gbeam-fix --fix-drivetrain

# Deploy Cinematic-Fast graphics preset
agy-gbeam-fix --optimize-graphics --preset cinematic-fast

# Safely purge compiled shader cache (.d3dcsx, .db)
agy-gbeam-fix --clean-cache

# Non-destructive dry-run preview
agy-gbeam-fix --all --dry-run
```

---

## 🧪 Comprehensive Automated Test Suite

GBEAM FIX is rigorously verified by **251 hermetic automated tests** across five testing tiers:

```bash
python -m pytest -v
```

- **Tier 1 (Feature)**: Regex pattern testing, materials conversion, drivetrain clamps, sound modernizer, path resolver & persistent cache, UI menu transitions, shader cache cleaner, graphics optimizer.
- **Tier 2 (Boundary)**: Corrupted ZIP headers, 0-byte archives, UTF-8 BOM encoding, file lock handling, encrypted archive protection.
- **Tier 3 (Combination)**: Atomic in-place file rewrites, binary asset passthrough SHA-256 integrity, batch scanner aggregation.
- **Tier 4 (Workload)**: End-to-end CLI subprocess executions, path overrides, help/version flags, dry-run guarantees.
- **Tier 5 (Adversarial)**: Malformed JBeam brackets, escaped quotes, infinite loop resistance.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for full details.
Contributions and pull requests welcome!
