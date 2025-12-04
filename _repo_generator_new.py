#!/usr/bin/env python3
"""
Modern Repo Generator for Kodi addons

Place this script in the root of your repo and run it. It will:
 - find addon folders (directories containing addon.xml)
 - remove compiled python artifacts
 - create zips in zips/<addon-id>/<addon-id>-<version>.zip
 - copy addon.xml and referenced artwork into zips/<addon-id>/
 - generate zips/addons.xml and zips/addons.xml.md5

Usage:
    python _repo_generator.py [--root PATH] [--dry-run] [--verbose]

Author: rewritten for Python 3
"""
from pathlib import Path
import shutil
import zipfile
import hashlib
import argparse
import sys
from xml.etree import ElementTree as ET

# Config
DEFAULT_RELEASES = ["repo", "matrix", "leia", "krypton"]
IGNORE_NAMES = {".git", ".github", ".gitignore", ".DS_Store", "thumbs.db", ".idea", "venv"}
IGNORED_FILE_PREFIXES = {"."}  # skip dotfiles when packaging
ZIP_COMPRESSION = zipfile.ZIP_DEFLATED


def supports_color():
    # Simple check for ANSI support
    return sys.stdout.isatty()


_USE_COLOR = supports_color()


def color_text(text, col):
    if not _USE_COLOR:
        return text
    COLORS = {
        "red": "\x1b[31m",
        "green": "\x1b[32m",
        "yellow": "\x1b[33m",
        "cyan": "\x1b[36m",
        "end": "\x1b[0m",
    }
    return f"{COLORS.get(col,'')}{text}{COLORS['end']}"


def human_size(num):
    for unit in ["bytes", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


class Generator:
    def __init__(self, root: Path, dry_run=False, verbose=False):
        self.root = Path(root).resolve()
        self.zips_dir = self.root / "zips"
        self.dry_run = dry_run
        self.verbose = verbose

        if not self.root.exists():
            raise FileNotFoundError(f"Root path {self.root} does not exist")

        if not self.dry_run:
            self.zips_dir.mkdir(parents=True, exist_ok=True)

        self._clean_compiled()
        self.addons = self._find_addons()
        if self.verbose:
            print(f"Found {len(self.addons)} addon(s).")

        if not self.addons:
            print(color_text("No addons found - nothing to do.", "yellow"))
            return

        self._process_addons()
        self._build_addons_xml()

    def _log(self, msg, color=None):
        if self.verbose:
            print(color_text(msg, color) if color else msg)

    def _clean_compiled(self):
        """Remove .pyc/.pyo and __pycache__ directories under root."""
        removed_any = False
        for p in self.root.rglob("*"):
            # skip zips folder
            if self.zips_dir in p.parents:
                continue
            if p.is_file() and p.suffix.lower() in {".pyc", ".pyo"}:
                try:
                    if not self.dry_run:
                        p.unlink()
                    self._log(f"Removed compiled file: {p}", "green")
                    removed_any = True
                except Exception as e:
                    print(color_text(f"Failed to remove {p}: {e}", "red"))
            elif p.is_dir() and p.name == "__pycache__":
                try:
                    if not self.dry_run:
                        shutil.rmtree(p)
                    self._log(f"Removed __pycache__: {p}", "green")
                    removed_any = True
                except Exception as e:
                    print(color_text(f"Failed to remove {p}: {e}", "red"))
        if not removed_any:
            self._log("No compiled files or __pycache__ found.", "cyan")

    def _find_addons(self):
        """Return a list of addon folders (Path) that contain addon.xml"""
        addons = []
        # Only look at immediate children (typical repo structure)
        for p in self.root.iterdir():
            if not p.is_dir():
                continue
            if p.name in IGNORE_NAMES or any(p.name.startswith(pref) for pref in IGNORED_FILE_PREFIXES):
                continue
            addon_xml = p / "addon.xml"
            if addon_xml.exists():
                addons.append(p)
        return sorted(addons, key=lambda p: p.name.lower())

    def _read_addon_meta(self, addon_folder: Path):
        """Parse addon.xml and return (id, version, xml_element)"""
        addon_xml_path = addon_folder / "addon.xml"
        try:
            tree = ET.parse(addon_xml_path)
            root = tree.getroot()
            aid = root.get("id")
            ver = root.get("version")
            if not aid or not ver:
                raise ValueError("Missing id or version in addon.xml")
            return aid, ver, root
        except Exception as e:
            raise RuntimeError(f"Failed to parse {addon_xml_path}: {e}")

    def _create_zip(self, addon_folder: Path, addon_id: str, version: str):
        """Create a zip at zips/<addon_id>/<addon_id>-<version>.zip that contains the addon folder."""
        out_folder = self.zips_dir / addon_id
        out_folder.mkdir(parents=True, exist_ok=True)
        zip_name = out_folder / f"{addon_id}-{version}.zip"
        if zip_name.exists():
            self._log(f"Zip already exists, skipping: {zip_name}", "yellow")
            return zip_name

        if self.dry_run:
            self._log(f"(dry-run) Would create zip: {zip_name}", "cyan")
            return zip_name

        # Create zip with the addon folder as top-level
        with zipfile.ZipFile(zip_name, "w", compression=ZIP_COMPRESSION) as zf:
            for file in addon_folder.rglob("*"):
                # skip directories, skip ignored patterns
                if file.is_dir():
                    continue
                rel = file.relative_to(addon_folder.parent)  # include addon folder name in archive
                # Skip ignored names at file level
                if any(part in IGNORE_NAMES for part in rel.parts):
                    continue
                if any(file.name.startswith(pref) for pref in IGNORED_FILE_PREFIXES):
                    continue
                zf.write(file, arcname=str(rel))
        size = human_size(zip_name.stat().st_size)
        print(f"Zip created: {color_text(str(zip_name), 'cyan')} ({color_text(size, 'green')})")
        return zip_name

    def _copy_meta_files(self, addon_id: str, addon_folder: Path, addon_root_element: ET.Element):
        """
        Copy addon.xml and referenced asset files into zips/<addon_id>/ (for repo hosting).
        Asset detection: look for <extension point="xbmc.addon.metadata"> or "kodi.addon.metadata",
        then find <assets> child and copy any text content children.
        """
        dest_folder = self.zips_dir / addon_id
        if self.dry_run:
            self._log(f"(dry-run) Would copy meta files to {dest_folder}", "cyan")
            return

        dest_folder.mkdir(parents=True, exist_ok=True)
        # copy addon.xml
        src_addon_xml = addon_folder / "addon.xml"
        if src_addon_xml.exists():
            shutil.copy2(src_addon_xml, dest_folder / "addon.xml")

        # find assets
        for ext in addon_root_element.findall("extension"):
            if ext.get("point") in ("xbmc.addon.metadata", "kodi.addon.metadata"):
                assets = ext.find("assets")
                if assets is None:
                    continue
                for art in assets:
                    if art.text:
                        src = addon_folder / art.text
                        if src.exists():
                            dest = dest_folder / art.text
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            try:
                                shutil.copy2(src, dest)
                                self._log(f"Copied asset: {src} -> {dest}", "green")
                            except Exception as e:
                                print(color_text(f"Failed to copy asset {src}: {e}", "red"))
                        else:
                            self._log(f"Asset referenced but not found: {src}", "yellow")

    def _process_addons(self):
        """For each addon found: parse metadata, zip, copy meta files."""
        for addon_folder in self.addons:
            try:
                aid, ver, root_elem = self._read_addon_meta(addon_folder)
            except Exception as e:
                print(color_text(f"Skipping {addon_folder.name}: {e}", "red"))
                continue

            self._log(f"Processing addon {aid} (version {ver})", "cyan")
            self._create_zip(addon_folder, aid, ver)
            self._copy_meta_files(aid, addon_folder, root_elem)

    def _build_addons_xml(self):
        """Assemble addons.xml from zips/*/addon.xml files and write md5."""
        addons_root = ET.Element("addons")

        # collect addon.xml files inside zips/<addon-id>/addon.xml
        addon_xml_paths = sorted(self.zips_dir.glob("*/addon.xml"))
        if not addon_xml_paths:
            print(color_text("No meta addon.xml files found in zips/* - skipping addons.xml generation", "yellow"))
            return

        for p in addon_xml_paths:
            try:
                tree = ET.parse(p)
                root = tree.getroot()
                addons_root.append(root)
            except Exception as e:
                print(color_text(f"Failed to parse {p}: {e}", "red"))

        # sort by id attribute
        addons_root[:] = sorted(addons_root, key=lambda el: el.get("id", "").lower())

        addons_tree = ET.ElementTree(addons_root)
        addons_xml_path = self.zips_dir / "addons.xml"

        if self.dry_run:
            self._log(f"(dry-run) Would write addons.xml to {addons_xml_path}", "cyan")
            return

        try:
            # write with declaration and utf-8
            addons_tree.write(addons_xml_path, encoding="utf-8", xml_declaration=True)
            print(color_text(f"Wrote {addons_xml_path}", "green"))
        except Exception as e:
            print(color_text(f"Failed to write {addons_xml_path}: {e}", "red"))
            return

        # generate md5
        try:
            content = addons_xml_path.read_bytes()
            digest = hashlib.md5(content).hexdigest()
            md5_path = self.zips_dir / "addons.xml.md5"
            md5_path.write_text(digest)
            print(color_text(f"Wrote {md5_path}", "green"))
        except Exception as e:
            print(color_text(f"Failed to write md5: {e}", "red"))


def detect_root(provided_root: Path = None) -> Path:
    if provided_root:
        return provided_root.resolve()
    here = Path.cwd()
    for candidate in DEFAULT_RELEASES:
        cand_path = here / candidate
        if cand_path.exists() and cand_path.is_dir():
            return cand_path
    # fallback to current directory
    return here


def main():
    parser = argparse.ArgumentParser(description="Generate zips/addons.xml for Kodi repo")
    parser.add_argument("--root", "-r", help="Repo root (folder containing addons or named 'repo')", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    root = detect_root(args.root)
    print(f"Using root: {root}")
    try:
        Generator(root, dry_run=args.dry_run, verbose=args.verbose)
    except Exception as e:
        print(color_text(f"ERROR: {e}", "red"))
        sys.exit(2)


if __name__ == "__main__":
    main()
