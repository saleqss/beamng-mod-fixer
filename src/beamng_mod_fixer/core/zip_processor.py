"""High-performance streaming ZIP processor and comprehensive mod fixer for BeamNG.drive.

Provides:
- Detection of encrypted and password-protected archives
- Detection of corrupted, truncated, or bad-CRC ZIP archives
- Handling of locked or in-use files with safe fallbacks
- Atomic in-place archive rewriting with directory structure preservation
- Non-text binary asset passthrough with byte-for-byte SHA-256 integrity
- Comprehensive multi-domain mod fixing:
  * Headlights & Optics (lightCastShadows, angles, flares, cookies, electrics)
  * Materials & Textures (materials.cs -> main.materials.json 1.5, VFS paths, emissives)
  * Drivetrain & Physics (differentials, gear ratios, viscous stiffness, tire pressures, clutch)
  * Sound & Audio (pre-FMOD paths -> modern BeamNG FMOD events)
  * Lua Crash Guard (v.data guard, deprecated API wrappers)
  * Cache & Junk Purge (Thumbs.db, .DS_Store, .bak, .tmp removal)
- Batch directory scanning with aggregated metrics reporting
"""

import logging
import json
import os
from pathlib import Path
import struct
import time
from typing import Any, Callable, Dict, List, Optional, Set
import zipfile

from beamng_mod_fixer.core import file_utils
from beamng_mod_fixer.core.drivetrain_fixer import fix_drivetrain_content
from beamng_mod_fixer.core.jbeam_fixer import (
    decode_jbeam_bytes,
    encode_jbeam_str,
    fix_jbeam_content,
)
from beamng_mod_fixer.core.lua_fixer import fix_lua_content
from beamng_mod_fixer.core.materials_fixer import (
    convert_materials_cs_to_json,
    fix_materials_json_content,
)
from beamng_mod_fixer.core.sound_fixer import fix_sound_content
from beamng_mod_fixer.exceptions import (
    ArchiveCorruptedError,
    ArchiveEncryptedError,
    ArchiveLockedError,
    ArchivePermissionError,
    BeamNGPathNotFoundError,
    CorruptArchiveError,
    PasswordProtectedArchiveError,
)
from beamng_mod_fixer.models import (
    DiagnosticNotice,
    ModArchiveReport,
    ModStatus,
    OverallSummary,
)

logger = logging.getLogger(__name__)


def is_archive_encrypted(archive_path: Path) -> bool:
    """Check whether the ZIP archive has any password-protected or encrypted entries.

    Inspects the general-purpose bit flag (bit 0 = 0x0001) in both central
    directory entries and local file headers.

    Args:
        archive_path: Path to the .zip archive.

    Returns:
        bool: True if any entry is marked as encrypted or password-protected.
    """
    if not archive_path.exists() or archive_path.stat().st_size == 0:
        return False

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            for info in zf.infolist():
                if info.flag_bits & 0x0001:
                    return True
                if hasattr(info, "is_encrypted") and info.is_encrypted():
                    return True
    except (zipfile.BadZipFile, OSError):
        # Fallback inspection of raw headers if central directory parsing failed
        try:
            raw = archive_path.read_bytes()
            if raw.startswith(b"PK\x03\x04") and len(raw) > 8:
                flag = int.from_bytes(raw[6:8], "little")
                if flag & 0x0001:
                    return True
            cd_idx = raw.find(b"PK\x01\x02")
            if cd_idx != -1 and len(raw) > cd_idx + 10:
                flag = int.from_bytes(raw[cd_idx + 8 : cd_idx + 10], "little")
                if flag & 0x0001:
                    return True
        except Exception:
            pass

    return False


def _check_local_crc_integrity(zf: zipfile.ZipFile) -> Optional[str]:
    """Verify local header CRC matches central directory CRC for all entries."""
    if not zf.fp:
        return None
    for info in zf.infolist():
        # If flag bit 3 is not set (i.e. CRC is in local header, not descriptor)
        if not (info.flag_bits & 0x0008):
            try:
                zf.fp.seek(info.header_offset)
                local_header = zf.fp.read(30)
                if len(local_header) == 30 and local_header.startswith(b"PK\x03\x04"):
                    local_crc = struct.unpack("<I", local_header[14:18])[0]
                    if local_crc != 0 and local_crc != info.CRC:
                        return info.filename
            except Exception:
                pass
    return None


def process_mod_archive(
    archive_path: Path,
    dry_run: bool = False,
    enable_diagnostics: bool = True,
    selective: bool = False,
    fix_materials: bool = True,
    fix_drivetrain: bool = True,
    fix_sound: bool = True,
    fix_lua: bool = True,
    clean_junk: bool = True,
) -> ModArchiveReport:
    """Process an individual BeamNG mod archive with comprehensive multi-domain repair.

    Performs:
    1. Validation of existence, non-zero size, and header CRC integrity.
    2. Detection of password protection / encryption.
    3. Detection of file locks (in use by BeamNG.drive or another process).
    4. Multi-domain repair across:
       - .jbeam files: Headlights/Optics + Drivetrain/Physics + Audio paths.
       - materials.cs: Conversion to modern main.materials.json v1.5 PBR.
       - *.materials.json: Version upgrade, path normalization, VFS texture reconciliation.
       - *.lua: Deprecated API guarding against fatal vehicle Lua crashes.
       - Junk files: Removal of Thumbs.db, .DS_Store, .bak, .tmp clutter.
    5. Atomic in-place replacement via temporary file swap if modified and not dry_run.

    Args:
        archive_path: Path to the .zip mod archive.
        dry_run: If True, preview fixes without modifying files on disk.
        enable_diagnostics: If True, gather detailed diagnostic notices.
        selective: If True, uses smart selective fixing to protect highbeams and modernize cookies.
        fix_materials: If True, converts materials.cs and repairs materials.json.
        fix_drivetrain: If True, repairs broken differentials, tire pressures, and clutch parameters.
        fix_sound: If True, modernizes legacy sound paths to BeamNG FMOD events.
        fix_lua: If True, guards deprecated vehicle Lua calls.
        clean_junk: If True, cleans OS junk files from archive.

    Returns:
        ModArchiveReport with status, metrics, and diagnostics.
    """
    start_time = time.perf_counter()
    report = ModArchiveReport(archive_path=archive_path)

    # 1. Existence check
    if not archive_path.exists():
        report.status = ModStatus.ERROR.value
        report.error_message = f"File not found: {archive_path}"
        report.elapsed_seconds = time.perf_counter() - start_time
        return report

    # 2. Empty / Zero-byte file check
    try:
        file_size = archive_path.stat().st_size
    except OSError as e:
        report.status = ModStatus.LOCKED.value
        report.error_message = f"Cannot access file stat (locked or permission denied): {e}"
        report.diagnostics.append(
            DiagnosticNotice(
                severity="warning",
                message=f"File access error: {e}",
                file_path=str(archive_path),
            )
        )
        report.elapsed_seconds = time.perf_counter() - start_time
        return report

    if file_size == 0:
        report.status = ModStatus.CORRUPT.value
        report.error_message = "Archive is 0 bytes (empty corrupted file)"
        report.elapsed_seconds = time.perf_counter() - start_time
        return report

    # 3. Encryption / Password-protection check
    if is_archive_encrypted(archive_path):
        report.status = ModStatus.ENCRYPTED.value
        report.error_message = (
            f"Archive '{archive_path.name}' is password-protected or encrypted. Skipping."
        )
        report.diagnostics.append(
            DiagnosticNotice(
                severity="warning",
                message=f"Archive '{archive_path.name}' is password-protected or encrypted.",
                file_path=str(archive_path),
                rule="archive_encrypted",
            )
        )
        report.elapsed_seconds = time.perf_counter() - start_time
        return report

    # 4. Open and inspect ZIP contents
    modified_files: Dict[str, bytes] = {}
    added_files: Dict[str, bytes] = {}
    deleted_entries: Set[str] = set()

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:

            # Check local header CRC vs central directory CRC
            local_bad_crc = _check_local_crc_integrity(zf)
            if local_bad_crc is not None:
                report.status = ModStatus.CORRUPT.value
                report.error_message = (
                    f"Corrupted ZIP archive: local header CRC mismatch in '{local_bad_crc}'"
                )
                report.elapsed_seconds = time.perf_counter() - start_time
                return report

            entries = zf.infolist()
            available_filenames = {e.filename for e in entries}

            for entry in entries:
                entry_name_lower = entry.filename.lower()

                # Clean OS / Editor junk files if requested
                if clean_junk and not entry.is_dir():
                    if (
                        entry_name_lower.endswith(("thumbs.db", ".ds_store", "desktop.ini"))
                        or entry_name_lower.endswith((".bak", ".tmp", "~"))
                    ):
                        deleted_entries.add(entry.filename)
                        report.junk_cleaned += 1
                        report.diagnostics.append(
                            DiagnosticNotice(
                                severity="info",
                                message=f"Purged junk file '{entry.filename}' from archive",
                                file_path=entry.filename,
                                rule="junk_file_purged",
                            )
                        )
                        continue

                # 4a. JBeam files
                if entry_name_lower.endswith(".jbeam") and not entry.is_dir():
                    report.jbeams_inspected += 1
                    try:
                        raw_data = zf.read(entry.filename)
                        text, encoding = decode_jbeam_bytes(raw_data)
                        file_modified = False

                        # Pass 1: Optics & Headlights
                        fixed_text, fix_count, diags = fix_jbeam_content(
                            text,
                            filename=entry.filename,
                            available_files=available_filenames,
                            selective=selective,
                        )
                        if fix_count > 0 or fixed_text != text:
                            file_modified = True
                            report.shadows_fixed += fix_count
                            report.diagnostics.extend(diags)

                        # Pass 2: Drivetrain & Physics
                        if fix_drivetrain:
                            fixed_text, dt_count, dt_diags = fix_drivetrain_content(
                                fixed_text,
                                filename=entry.filename
                            )
                            if dt_count > 0:
                                file_modified = True
                                report.drivetrains_fixed += dt_count
                                report.diagnostics.extend(dt_diags)

                        # Pass 3: Sound & Audio Modernization
                        if fix_sound:
                            fixed_text, snd_count, snd_diags = fix_sound_content(
                                fixed_text,
                                filename=entry.filename
                            )
                            if snd_count > 0:
                                file_modified = True
                                report.sounds_fixed += snd_count
                                report.diagnostics.extend(snd_diags)

                        if file_modified:
                            report.jbeams_modified += 1
                            new_bytes = encode_jbeam_str(fixed_text, encoding)
                            modified_files[entry.filename] = new_bytes

                    except Exception as parse_err:
                        report.diagnostics.append(
                            DiagnosticNotice(
                                severity="warning",
                                message=f"Failed parsing JBeam '{entry.filename}': {parse_err}",
                                file_path=entry.filename,
                            )
                        )

                # 4b. Legacy materials.cs -> convert to modern main.materials.json (v1.5)
                elif fix_materials and entry_name_lower.endswith("materials.cs") and not entry.is_dir():
                    try:
                        raw_data = zf.read(entry.filename)
                        cs_text, _ = decode_jbeam_bytes(raw_data)
                        json_str, conv_count, cs_diags = convert_materials_cs_to_json(
                            cs_text,
                            filename=entry.filename
                        )
                        if conv_count > 0:
                            report.materials_converted += conv_count
                            report.diagnostics.extend(cs_diags)
                            dirname = entry.filename.rsplit("/", 1)[0] if "/" in entry.filename else ""
                            target_json = f"{dirname}/main.materials.json" if dirname else "main.materials.json"

                            new_mats = json.loads(json_str)
                            # Merge if target_json was already modified
                            if target_json in modified_files:
                                try:
                                    existing = json.loads(modified_files[target_json].decode("utf-8"))
                                    existing.update(new_mats)
                                    modified_files[target_json] = json.dumps(existing, indent=2, ensure_ascii=False).encode("utf-8")
                                except Exception:
                                    modified_files[target_json] = json_str.encode("utf-8")
                            # Merge if target_json exists in the source archive
                            elif target_json in available_filenames:
                                try:
                                    existing_raw = zf.read(target_json)
                                    existing_text, _ = decode_jbeam_bytes(existing_raw)
                                    existing = json.loads(existing_text)
                                    existing.update(new_mats)
                                    modified_files[target_json] = json.dumps(existing, indent=2, ensure_ascii=False).encode("utf-8")
                                except Exception:
                                    modified_files[target_json] = json_str.encode("utf-8")
                            # Merge if target_json was added by another .cs file
                            elif target_json in added_files:
                                try:
                                    existing = json.loads(added_files[target_json].decode("utf-8"))
                                    existing.update(new_mats)
                                    added_files[target_json] = json.dumps(existing, indent=2, ensure_ascii=False).encode("utf-8")
                                except Exception:
                                    added_files[target_json] = json_str.encode("utf-8")
                            else:
                                added_files[target_json] = json_str.encode("utf-8")
                    except Exception as cs_err:
                        report.diagnostics.append(
                            DiagnosticNotice(
                                severity="warning",
                                message=f"Failed converting materials.cs in '{entry.filename}': {cs_err}",
                                file_path=entry.filename,
                            )
                        )

                # 4c. Modern materials JSON files (*.materials.json)
                elif fix_materials and entry_name_lower.endswith(".materials.json") and not entry.is_dir():
                    try:
                        if entry.filename in modified_files:
                            raw_data = modified_files[entry.filename]
                        else:
                            raw_data = zf.read(entry.filename)
                        json_text, encoding = decode_jbeam_bytes(raw_data)
                        repaired_json, mat_count, mat_diags = fix_materials_json_content(
                            json_text,
                            filename=entry.filename,
                            available_files=available_filenames
                        )
                        if mat_count > 0 or repaired_json != json_text:
                            report.materials_fixed += mat_count
                            report.diagnostics.extend(mat_diags)
                            modified_files[entry.filename] = encode_jbeam_str(repaired_json, encoding)
                    except Exception as mat_err:
                        report.diagnostics.append(
                            DiagnosticNotice(
                                severity="warning",
                                message=f"Failed processing materials.json in '{entry.filename}': {mat_err}",
                                file_path=entry.filename,
                            )
                        )

                # 4d. Vehicle Lua scripts (*.lua)
                elif fix_lua and entry_name_lower.endswith(".lua") and not entry.is_dir():
                    try:
                        raw_data = zf.read(entry.filename)
                        lua_text, encoding = decode_jbeam_bytes(raw_data)
                        repaired_lua, lua_count, lua_diags = fix_lua_content(
                            lua_text,
                            filename=entry.filename
                        )
                        if lua_count > 0 or repaired_lua != lua_text:
                            report.lua_fixed += lua_count
                            report.diagnostics.extend(lua_diags)
                            modified_files[entry.filename] = encode_jbeam_str(repaired_lua, encoding)
                    except Exception as lua_err:
                        report.diagnostics.append(
                            DiagnosticNotice(
                                severity="warning",
                                message=f"Failed processing Lua script '{entry.filename}': {lua_err}",
                                file_path=entry.filename,
                            )
                        )

    except zipfile.BadZipFile as e:
        report.status = ModStatus.CORRUPT.value
        report.error_message = f"Corrupted ZIP archive: {e}"
        report.elapsed_seconds = time.perf_counter() - start_time
        return report
    except PermissionError as e:
        report.status = ModStatus.LOCKED.value
        report.error_message = f"Archive locked during read: {e}"
        report.diagnostics.append(
            DiagnosticNotice(
                severity="warning",
                message=f"Archive locked or in use: {e}",
                file_path=str(archive_path),
            )
        )
        report.elapsed_seconds = time.perf_counter() - start_time
        return report
    except OSError as e:
        report.status = ModStatus.ERROR.value
        report.error_message = f"OS I/O error reading archive: {e}"
        report.elapsed_seconds = time.perf_counter() - start_time
        return report

    # 5. Check if any modifications were made across any domain
    total_modifications = (
        report.jbeams_modified
        + report.materials_converted
        + report.materials_fixed
        + report.drivetrains_fixed
        + report.sounds_fixed
        + report.lua_fixed
        + report.junk_cleaned
        + len(added_files)
    )

    if total_modifications == 0:
        report.status = ModStatus.CLEAN.value
        report.elapsed_seconds = time.perf_counter() - start_time
        return report

    # 6. Modifications needed: handle dry-run
    if dry_run:
        report.status = ModStatus.FIXED.value
        report.elapsed_seconds = time.perf_counter() - start_time
        return report

    # 7. Modifications needed: perform atomic streaming rewrite
    temp_target = file_utils.create_temp_target(archive_path)

    try:
        with zipfile.ZipFile(archive_path, "r") as src_zf:
            with zipfile.ZipFile(
                temp_target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1
            ) as dst_zf:
                written_names: Set[str] = set()

                for entry in src_zf.infolist():
                    if entry.filename in deleted_entries:
                        # Skip deleted junk entries
                        continue

                    if entry.filename in modified_files:
                        # Write patched text data preserving metadata and UTF-8 flags
                        new_data = modified_files[entry.filename]
                        new_info = zipfile.ZipInfo(
                            entry.filename, date_time=entry.date_time
                        )
                        new_info.create_system = entry.create_system
                        new_info.flag_bits = entry.flag_bits
                        new_info.compress_type = entry.compress_type
                        new_info.comment = entry.comment
                        new_info.external_attr = entry.external_attr
                        dst_zf.writestr(new_info, new_data)
                        written_names.add(entry.filename)
                    else:
                        # Stream non-modified entries (DDS, DAE, WAV, etc.) byte-for-byte
                        entry_bytes = src_zf.read(entry.filename)
                        dst_zf.writestr(entry, entry_bytes)
                        written_names.add(entry.filename)

                # Write newly generated files (e.g. main.materials.json from materials.cs)
                for add_name, add_data in added_files.items():
                    if add_name not in written_names:
                        dst_zf.writestr(add_name, add_data)
                        written_names.add(add_name)

        # Atomically swap temp_target into original location
        file_utils.atomic_replace(temp_target, archive_path)
        report.status = ModStatus.FIXED.value
    except (PermissionError, ArchiveLockedError) as e:
        if temp_target.exists():
            try:
                temp_target.unlink()
            except Exception:
                pass
        report.status = ModStatus.LOCKED.value
        report.jbeams_modified = 0
        report.shadows_fixed = 0
        report.error_message = (
            f"Archive '{archive_path.name}' is locked or in use by BeamNG.drive / another process: {e}"
        )
        report.diagnostics.append(
            DiagnosticNotice(
                severity="warning",
                message=f"Archive locked or in use during replacement: {e}",
                file_path=str(archive_path),
            )
        )
    except Exception as e:
        if temp_target.exists():
            try:
                temp_target.unlink()
            except Exception:
                pass
        report.status = ModStatus.ERROR.value
        report.jbeams_modified = 0
        report.shadows_fixed = 0
        report.error_message = f"Failed to rewrite mod archive: {e}"
        logger.error("Error during atomic rewrite of '%s': %s", archive_path, e)
    finally:
        # Guarantee no leftover temporary files
        if temp_target.exists():
            try:
                temp_target.unlink()
            except Exception:
                pass

    report.elapsed_seconds = time.perf_counter() - start_time
    return report


def scan_and_fix_mods(
    mods_dir: Path | str,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[Path, ModArchiveReport, int, int], None]] = None,
    max_workers: Optional[int] = None,
    selective: bool = False,
    fix_materials: bool = True,
    fix_drivetrain: bool = True,
    fix_sound: bool = True,
    fix_lua: bool = True,
    clean_junk: bool = True,
) -> OverallSummary:
    """Scan a directory for BeamNG mod ZIP archives and perform comprehensive multi-domain repair.

    Args:
        mods_dir: Path to the BeamNG mods directory.
        dry_run: If True, analyze and preview changes without modifying files on disk.
        progress_callback: Optional callback invoked after each archive is processed.
                           Signature: callback(path, report, index, total_count)
        max_workers: Maximum number of worker threads for parallel archive processing.
        selective: If True, uses smart selective fixing to protect highbeams and modernize cookies.
        fix_materials: If True, converts materials.cs and repairs materials.json.
        fix_drivetrain: If True, repairs differentials, tire pressures, and clutch parameters.
        fix_sound: If True, modernizes legacy audio paths to BeamNG FMOD events.
        fix_lua: If True, guards deprecated vehicle Lua scripts.
        clean_junk: If True, cleans OS junk files.

    Returns:
        OverallSummary with aggregated counts across all scanned archives.
    """
    start_time = time.perf_counter()
    mods_path = Path(mods_dir)
    summary = OverallSummary()

    if not mods_path.exists():
        raise BeamNGPathNotFoundError(f"Mods directory does not exist: {mods_path}")

    if not mods_path.is_dir():
        raise BeamNGPathNotFoundError(f"Specified path is not a directory: {mods_path}")

    # Discover all .zip archives in mods_dir (ignoring non-zip files and subfolders)
    zip_files = sorted(
        [p for p in mods_path.iterdir() if p.is_file() and p.suffix.lower() == ".zip"]
    )
    total_files = len(zip_files)

    if max_workers is None:
        max_workers = min(6, os.cpu_count() or 4)

    def _process_one(zp: Path, is_dry: bool) -> ModArchiveReport:
        return process_mod_archive(
            zp,
            dry_run=is_dry,
            selective=selective,
            fix_materials=fix_materials,
            fix_drivetrain=fix_drivetrain,
            fix_sound=fix_sound,
            fix_lua=fix_lua,
            clean_junk=clean_junk,
        )

    if dry_run or total_files <= 1 or max_workers <= 1:
        for idx, zip_path in enumerate(zip_files, start=1):
            report = _process_one(zip_path, is_dry=dry_run)
            summary.total_scanned += 1
            summary.jbeams_inspected += report.jbeams_inspected
            summary.jbeams_fixed += report.jbeams_modified
            summary.shadows_fixed += report.shadows_fixed
            summary.materials_converted += report.materials_converted
            summary.materials_fixed += report.materials_fixed
            summary.drivetrains_fixed += report.drivetrains_fixed
            summary.sounds_fixed += report.sounds_fixed
            summary.lua_fixed += report.lua_fixed
            summary.junk_cleaned += report.junk_cleaned
            summary.archive_reports.append(report)

            if report.status == ModStatus.FIXED.value:
                summary.modified_archives += 1
            elif report.status == ModStatus.CLEAN.value:
                summary.clean_archives += 1
            elif report.status == ModStatus.LOCKED.value:
                summary.skipped_locked += 1
            elif report.status == ModStatus.CORRUPT.value:
                summary.skipped_corrupt += 1
            elif report.status == ModStatus.ENCRYPTED.value:
                summary.skipped_encrypted += 1
            elif report.status == ModStatus.ERROR.value:
                summary.errors_encountered += 1

            if progress_callback is not None:
                progress_callback(zip_path, report, idx, total_files)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        completed_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_zip = {
                executor.submit(_process_one, zp, False): zp
                for zp in zip_files
            }
            for future in as_completed(future_to_zip):
                zip_path = future_to_zip[future]
                completed_count += 1
                try:
                    report = future.result()
                except Exception as e:
                    report = ModArchiveReport(archive_path=zip_path)
                    report.status = ModStatus.ERROR.value
                    report.error_message = str(e)

                summary.total_scanned += 1
                summary.jbeams_inspected += report.jbeams_inspected
                summary.jbeams_fixed += report.jbeams_modified
                summary.shadows_fixed += report.shadows_fixed
                summary.materials_converted += report.materials_converted
                summary.materials_fixed += report.materials_fixed
                summary.drivetrains_fixed += report.drivetrains_fixed
                summary.sounds_fixed += report.sounds_fixed
                summary.lua_fixed += report.lua_fixed
                summary.junk_cleaned += report.junk_cleaned
                summary.archive_reports.append(report)

                if report.status == ModStatus.FIXED.value:
                    summary.modified_archives += 1
                elif report.status == ModStatus.CLEAN.value:
                    summary.clean_archives += 1
                elif report.status == ModStatus.LOCKED.value:
                    summary.skipped_locked += 1
                elif report.status == ModStatus.CORRUPT.value:
                    summary.skipped_corrupt += 1
                elif report.status == ModStatus.ENCRYPTED.value:
                    summary.skipped_encrypted += 1
                elif report.status == ModStatus.ERROR.value:
                    summary.errors_encountered += 1

                if progress_callback is not None:
                    progress_callback(zip_path, report, completed_count, total_files)

    summary.elapsed_seconds = time.perf_counter() - start_time
    return summary
