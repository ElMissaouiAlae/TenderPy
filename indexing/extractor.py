"""Extract DCE files from a tender's DCE archive."""

from __future__ import annotations

import itertools
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class ExtractedFile:
    """A DCE file written to the working directory.

    Attributes:
        archive_path: Path of the file inside the DCE archive; files from
            nested zips are prefixed with the nested zip's own path
            (e.g. "annexes.zip/RC.pdf").
        local_path: Where the file was written on disk; None when it could
            not be extracted.
        extraction_error: Why the file, or the nested zip it stands for,
            could not be extracted; None when extracted.
    """

    archive_path: str
    local_path: Path | None
    extraction_error: str | None = None

    @property
    def file_type(self) -> str:
        """Lower-case extension of the archive path without the dot (e.g. "pdf")."""
        return PurePosixPath(self.archive_path).suffix.lstrip(".").lower()


def extract_archive(archive: bytes, work_dir: Path) -> list[ExtractedFile]:
    """Write every file in a DCE archive to work_dir, recursing into nested zips.

    Files are written under generated names (keeping their extension) rather
    than their archive paths, so a malicious or odd path inside the archive
    can never escape work_dir or collide with another member.

    Nested zips are not returned themselves, only the files inside them.
    A member that cannot be read (corrupt, encrypted, unsupported
    compression), or a nested zip that cannot be opened, is returned with
    its extraction_error set, so one bad file never stops the rest.

    Args:
        archive: Bytes of the DCE archive (a zip).
        work_dir: Existing directory to extract into.

    Returns:
        The extracted DCE files, in archive order (depth first).

    Raises:
        zipfile.BadZipFile: if the top-level archive is not a readable zip.
    """
    with zipfile.ZipFile(BytesIO(archive)) as zip_file:
        return list(_Extraction(work_dir).extract(zip_file, prefix=""))


class _Extraction:
    """Writes the files of one DCE archive under unique names in work_dir."""

    def __init__(self, work_dir: Path) -> None:
        self._work_dir = work_dir
        self._positions = itertools.count()

    def extract(self, zip_file: zipfile.ZipFile, prefix: str) -> Iterator[ExtractedFile]:
        for member in zip_file.infolist():
            if member.is_dir():
                continue
            archive_path = prefix + member.filename
            try:
                content = zip_file.read(member)
            except Exception as exc:
                # zipfile raises several types (BadZipFile, RuntimeError,
                # NotImplementedError, zlib.error...) for one unreadable member.
                yield _unreadable(archive_path, exc)
                continue
            if PurePosixPath(archive_path).suffix.lower() == ".zip":
                yield from self._extract_nested(content, archive_path)
            else:
                local_path = self._write(archive_path, content)
                yield ExtractedFile(archive_path=archive_path, local_path=local_path)

    def _extract_nested(self, content: bytes, archive_path: str) -> Iterator[ExtractedFile]:
        try:
            nested = zipfile.ZipFile(BytesIO(content))
        except zipfile.BadZipFile as exc:
            yield _unreadable(archive_path, exc)
            return
        with nested:
            yield from self.extract(nested, prefix=f"{archive_path}/")

    def _write(self, archive_path: str, content: bytes) -> Path:
        suffix = PurePosixPath(archive_path).suffix.lower()
        local_path = self._work_dir / f"{next(self._positions):05d}{suffix}"
        local_path.write_bytes(content)
        return local_path


def _unreadable(archive_path: str, exc: Exception) -> ExtractedFile:
    return ExtractedFile(
        archive_path=archive_path,
        local_path=None,
        extraction_error=f"Could not extract: {type(exc).__name__}: {exc}",
    )
