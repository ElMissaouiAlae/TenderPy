"""Extract DCE files from a tender's DCE archive."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class ExtractedFile:
    """A DCE file written to the working directory.

    Attributes:
        archive_path: Path of the file inside the DCE archive.
        local_path: Where the file was written on disk.
    """

    archive_path: str
    local_path: Path

    @property
    def file_type(self) -> str:
        """Lower-case extension of the archive path without the dot (e.g. "pdf")."""
        return PurePosixPath(self.archive_path).suffix.lstrip(".").lower()


def extract_archive(archive: bytes, work_dir: Path) -> list[ExtractedFile]:
    """Write every file in a DCE archive to work_dir.

    Files are written under generated names (keeping their extension) rather
    than their archive paths, so a malicious or odd path inside the archive
    can never escape work_dir or collide with another member.

    Args:
        archive: Bytes of the DCE archive (a zip).
        work_dir: Existing directory to extract into.

    Returns:
        The extracted DCE files, in archive order.

    Raises:
        zipfile.BadZipFile: if the archive is not a readable zip.
    """
    extracted = []
    with zipfile.ZipFile(BytesIO(archive)) as zip_file:
        for position, member in enumerate(zip_file.infolist()):
            if member.is_dir():
                continue
            suffix = PurePosixPath(member.filename).suffix.lower()
            local_path = work_dir / f"{position:05d}{suffix}"
            local_path.write_bytes(zip_file.read(member))
            extracted.append(ExtractedFile(archive_path=member.filename, local_path=local_path))
    return extracted
