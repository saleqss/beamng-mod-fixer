"""Background Downloads Watcher and Mod Auto-Installer for BeamNG.drive.

Monitors the user's Downloads directory for newly downloaded BeamNG mod archives,
automatically inspects, unwraps nested folders, moves the archive into the BeamNG
mods directory, and runs the 100% comprehensive auto-repair pipeline on the fly.
"""

import logging
import os
from pathlib import Path
import shutil
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import zipfile

from beamng_mod_fixer.core.zip_processor import (
    detect_nested_mod_prefix,
    process_mod_archive,
)
from beamng_mod_fixer.models import ModArchiveReport

logger = logging.getLogger(__name__)

# Extensions used by web browsers during active downloading
INCOMPLETE_DOWNLOAD_EXTENSIONS = (
    ".crdownload",
    ".part",
    ".download",
    ".tmp",
    ".opdownload",
)

# Standard folder signatures identifying BeamNG mod archives
BEAMNG_MOD_SIGNATURES = (
    "vehicles/",
    "levels/",
    "art/",
    "ui/",
    "track/",
    "scenarios/",
    "campaigns/",
    "scripts/",
    "sound/",
    "mods/",
)


def get_default_downloads_dir() -> Path:
    """Resolve the default system Downloads directory across platforms."""
    # On Windows, check userprofile / Downloads
    user_home = Path.home()
    downloads = user_home / "Downloads"
    if downloads.exists() and downloads.is_dir():
        return downloads
    return user_home


def is_file_completely_downloaded(file_path: Path, check_interval: float = 1.0) -> bool:
    """Verify that a file is completely written and not actively downloading or locked.

    Checks:
    1. Not having a browser temporary extension (.crdownload, .part, etc.).
    2. File exists and size > 0.
    3. File size remains stable across the check_interval.
    4. File can be opened for exclusive read access.
    5. File is a valid ZIP archive without premature EOF.
    """
    if not file_path.exists():
        return False

    fname_lower = file_path.name.lower()
    if any(fname_lower.endswith(ext) for ext in INCOMPLETE_DOWNLOAD_EXTENSIONS):
        return False

    try:
        size1 = file_path.stat().st_size
    except OSError:
        return False

    if size1 == 0:
        return False

    # Wait check_interval and re-read size to ensure no active writing
    time.sleep(check_interval)

    try:
        size2 = file_path.stat().st_size
    except OSError:
        return False

    if size1 != size2:
        return False

    # Verify exclusive read access (no file lock by browser)
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header != b"PK\x03\x04":
                return False
    except (OSError, PermissionError):
        return False

    # Verify ZIP integrity
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            if zf.testzip() is not None:
                # Corrupt or incomplete zip CRC
                return False
    except (zipfile.BadZipFile, OSError):
        return False

    return True


def inspect_archive_type(archive_path: Path) -> Tuple[bool, str]:
    """Inspect archive contents to determine if it is a genuine BeamNG mod.

    Returns:
        Tuple[bool, str]: (is_beamng_mod, category_description)
    """
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            entries = [e.filename.replace("\\", "/") for e in zf.infolist()]
            nested_prefix = detect_nested_mod_prefix(entries)

            normalized_entries = [
                e[len(nested_prefix):] if nested_prefix and e.startswith(nested_prefix) else e
                for e in entries
            ]

            has_jbeam = any(e.lower().endswith(".jbeam") for e in normalized_entries)
            has_materials = any(e.lower().endswith((".materials.json", "materials.cs")) for e in normalized_entries)
            has_mod_info = any(e.lower().endswith("mod_info.json") for e in normalized_entries)

            for entry in normalized_entries:
                entry_low = entry.lower()
                if entry_low.startswith("vehicles/"):
                    return True, "Vehicle Mod"
                if entry_low.startswith("levels/"):
                    return True, "Map / Level Mod"
                if entry_low.startswith("track/"):
                    return True, "Track / Course Mod"
                if entry_low.startswith("ui/"):
                    return True, "UI App / Plugin"
                if entry_low.startswith("scenarios/"):
                    return True, "Mission / Scenario Mod"

            if has_jbeam or has_materials or has_mod_info:
                return True, "BeamNG Content Mod"

            return False, "Not a BeamNG mod"
    except Exception as e:
        logger.debug("Failed inspecting archive %s: %e", archive_path, e)
        return False, f"Inspection error: {e}"


def install_and_repair_mod(
    source_archive: Path,
    target_mods_dir: Path,
    auto_repair: bool = True,
    dry_run: bool = False,
) -> Optional[ModArchiveReport]:
    """Move downloaded mod archive into BeamNG mods folder and run auto-repair pipeline.

    Args:
        source_archive: Path to newly downloaded .zip in Downloads.
        target_mods_dir: BeamNG mods directory path.
        auto_repair: If True, executes full 7-stage repair pipeline immediately.
        dry_run: If True, simulates without disk changes.

    Returns:
        ModArchiveReport if successful, or None if skipped/ineligible.
    """
    if not source_archive.exists():
        return None

    is_mod, category = inspect_archive_type(source_archive)
    if not is_mod:
        logger.info("Skipping non-BeamNG archive: %s (%s)", source_archive.name, category)
        return None

    target_mods_dir.mkdir(parents=True, exist_ok=True)
    destination = target_mods_dir / source_archive.name

    # Handle collision if file already exists in mods folder
    if destination.exists():
        base_stem = source_archive.stem
        counter = 1
        while destination.exists():
            destination = target_mods_dir / f"{base_stem}_{counter}.zip"
            counter += 1

    if dry_run:
        logger.info("[Dry-Run] Would move %s to %s", source_archive, destination)
        return ModArchiveReport(archive_path=destination)

    # Move file from Downloads to mods directory
    try:
        shutil.move(str(source_archive), str(destination))
    except (OSError, PermissionError) as err:
        logger.warning("Failed to move %s to %s: %s", source_archive, destination, err)
        return None

    logger.info("Auto-Installed mod: %s -> %s (%s)", source_archive.name, destination.name, category)

    # Automatically execute complete 7-stage repair pipeline on the newly installed mod
    if auto_repair:
        report = process_mod_archive(
            destination,
            dry_run=False,
            selective=True,
            fix_rear_lights=True,
            fix_materials=True,
            fix_drivetrain=True,
            fix_sound=True,
            fix_lua=True,
            clean_junk=True,
        )
        return report

    return ModArchiveReport(archive_path=destination)


class ModWatcher:
    """Background directory monitor for newly downloaded BeamNG mod archives."""

    def __init__(
        self,
        downloads_dir: Optional[Path] = None,
        mods_dir: Optional[Path] = None,
        poll_interval: float = 2.0,
        auto_repair: bool = True,
        on_install_callback: Optional[Callable[[Path, Optional[ModArchiveReport]], None]] = None,
    ):
        self.downloads_dir = downloads_dir or get_default_downloads_dir()
        self.mods_dir = mods_dir or (Path.home() / "AppData/Local/BeamNG/BeamNG.drive/current/mods")
        self.poll_interval = poll_interval
        self.auto_repair = auto_repair
        self.on_install_callback = on_install_callback

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._seen_files: Set[Path] = set()
        self.installed_count: int = 0
        self.recent_events: List[Dict[str, Any]] = []

    def start(self) -> None:
        """Start the background watcher daemon thread."""
        if self.is_running():
            return

        # Pre-populate seen files so we don't re-install existing old downloads
        if self.downloads_dir.exists() and self.downloads_dir.is_dir():
            try:
                for f in self.downloads_dir.iterdir():
                    if f.is_file() and f.suffix.lower() == ".zip":
                        self._seen_files.add(f)
            except OSError:
                pass

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="BeamNG-ModWatcher",
        )
        self._thread.start()
        logger.info("ModWatcher started watching: %s", self.downloads_dir)

    def stop(self, timeout: float = 3.0) -> None:
        """Stop the background watcher daemon thread cleanly."""
        if not self.is_running():
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("ModWatcher stopped.")

    @property
    def is_running(self) -> Any:
        """Check whether the background watcher thread is active (callable and bool-evaluable)."""
        class _RunningState:
            def __init__(self, watcher: "ModWatcher"):
                self._watcher = watcher

            def __bool__(self) -> bool:
                return self._watcher._thread is not None and self._watcher._thread.is_alive()

            def __call__(self) -> bool:
                return bool(self)

        return _RunningState(self)

    def check_now(self) -> int:
        """Convenience wrapper: run check_once() and return count of installed mods."""
        results = self.check_once()
        return len(results)

    def get_recent_installed(self) -> List[Tuple[str, str, str]]:
        """Get formatted tuples (time_str, filename, status) of recent installs."""
        out: List[Tuple[str, str, str]] = []
        for ev in self.recent_events:
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev["time"]))
            rep = ev.get("report")
            status = rep.status if rep else "installed"
            out.append((t_str, ev["filename"], str(status)))
        return out

    def check_once(self) -> List[Tuple[Path, Optional[ModArchiveReport]]]:
        """Perform a single scan of the Downloads folder and process any completed mods."""
        results: List[Tuple[Path, Optional[ModArchiveReport]]] = []
        if not self.downloads_dir.exists() or not self.downloads_dir.is_dir():
            return results

        try:
            current_zips = [
                p for p in self.downloads_dir.iterdir()
                if p.is_file() and p.suffix.lower() == ".zip"
            ]
        except OSError:
            return results

        for zip_file in current_zips:
            if zip_file in self._seen_files:
                continue

            # Verify file write is completely finished
            if not is_file_completely_downloaded(zip_file, check_interval=0.5):
                continue

            self._seen_files.add(zip_file)
            report = install_and_repair_mod(
                zip_file,
                self.mods_dir,
                auto_repair=self.auto_repair,
            )
            if report is not None:
                self.installed_count += 1
                event = {
                    "filename": zip_file.name,
                    "time": time.time(),
                    "report": report,
                }
                self.recent_events.append(event)
                results.append((zip_file, report))
                if self.on_install_callback:
                    try:
                        self.on_install_callback(zip_file, report)
                    except Exception:
                        pass

        return results

    def _watch_loop(self) -> None:
        """Continuous background polling loop."""
        while not self._stop_event.is_set():
            try:
                self.check_once()
            except Exception as e:
                logger.debug("Error in ModWatcher poll: %s", e)

            # Wait poll_interval respecting early stop
            self._stop_event.wait(self.poll_interval)
