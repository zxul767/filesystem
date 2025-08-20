import contextlib
import hashlib
import io
import mmap
import os
import re
from pathlib import Path
from typing import Generator, Iterator, Optional

import structlog

log = structlog.get_logger(__name__)


# ==============================================================================
# File Signatures (Hashing)
# ==============================================================================
EMPTY_FILE_MD5_HASH = "d41d8cd98f00b204e9800998ecf8427e"
SMALL_CHUNK_SIZE = 4 * 1024  # 4 KB


def compute_md5_hash(filepath: Path, chunk_size=SMALL_CHUNK_SIZE) -> str:
    if filepath.stat().st_size == 0:
        return EMPTY_FILE_MD5_HASH

    log.debug(f"Computing md5 hash for: {filepath}")
    hash_md5 = hashlib.md5()
    with filepath.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def compute_md5_hash_ssd(filepath: Path) -> str:
    if filepath.stat().st_size == 0:
        # we need to handle this here because `mmap.mmap(...)` cannot map empty files
        return EMPTY_FILE_MD5_HASH

    log.debug(f"Computing md5 hash for: {filepath}")
    hash_md5 = hashlib.md5()
    with filepath.open("rb") as f:
        # Memory-map the file, size 0 means whole file
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            hash_md5.update(mm)
    return hash_md5.hexdigest()


def compute_weak_hash(
    filepath: Path, *, file_size: int, chunk_size: int = SMALL_CHUNK_SIZE
) -> str:
    with filepath.open("rb") as f:
        if file_size <= chunk_size:
            data = f.read()  # Read the entire file if it's smaller than chunk_size
        else:
            first_chunk = f.read(chunk_size)
            f.seek(-chunk_size, os.SEEK_END)
            last_chunk = f.read(chunk_size)
            data = first_chunk + last_chunk
    return hashlib.md5(data).hexdigest()


def looks_like_md5_hash(s: str) -> bool:
    return bool(re.fullmatch(r"[a-fA-F0-9]{32}", s))


# ==============================================================================
# File/Directory Search
# ==============================================================================
WILDCARD_EXTENSION = ".*"
DEFAULT_EXCLUDED_DIRS = (".git", ".pytest_cache", ".mypy_cache", "__pycache__")


def find_files(
    root: Path,
    *,
    extensions: tuple[str, ...] = (WILDCARD_EXTENSION,),
    excluded_dirs: tuple[str, ...] = DEFAULT_EXCLUDED_DIRS,
) -> Iterator[Path]:
    def _find_files(root: Path) -> Iterator[Path]:
        for path in root.iterdir():
            if path.is_dir():
                if path.name not in excluded_dirs:
                    yield from _find_files(path)
            elif matches_any_extension(path, extensions):
                yield path

    yield from _find_files(root)


def find_empty_directories(root: Path, recursively: bool = True) -> Iterator[Path]:
    """
    Yield all empty directories under `root`, including nested directories
    if `recursively=True`.

    The order of the yielded directories is not guaranteed, except for the
    fact that the most deeply nested folders will be yielded first
    (i.e., in a post-order traversal fashion)
    """
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")

    def _find(root: Path) -> Iterator[Path]:
        for path in root.iterdir():
            if path.is_dir() and recursively:
                yield from _find(path)

        if not any(root.iterdir()):
            yield root

    yield from _find(root)


def find_child_dir(path: Path, name: str) -> Optional[Path]:
    """Returns the first directory named `name` directly under `path`."""
    for dir in get_children_dirs(path):
        if dir.name == name:
            return dir
    return None


def matches_any_extension(filepath: Path, extensions: tuple[str, ...]) -> bool:
    for extension in extensions:
        if extension == WILDCARD_EXTENSION or filepath.suffix == extension:
            return True
    return False


# ==============================================================================
# Directory Operations
# ==============================================================================
def try_rmdir(folder: Path) -> bool:
    """
    Try to remove `folder` if empty.

    Returns `True` if successful, `False` otherwise. No exceptions are raised.
    """
    try:
        folder.rmdir()
        return True
    except Exception:
        return False


def count_dir_files(path: Path) -> int:
    """
    Returns the number of files and directories under the directory pointed
    by `path`.
    """
    return sum(1 for _ in path.iterdir())


def is_empty_dir(path: Path) -> bool:
    """Returns `True` if `path` points to an empty directory."""
    return path.is_dir() and not any(path.iterdir())


def ensure_dir(path: Path) -> Path:
    """
    Ensure that `path` is an existing directory, or create one if necesary.
    """
    path.mkdir(exist_ok=True, parents=True)
    return path


def get_children_dirs(dirpath: Path) -> Iterator[Path]:
    """Returns all direct children directories of `dirpath`."""
    for path in dirpath.iterdir():
        if path.is_dir():
            yield path


# ==============================================================================
# Path Manipulation
# ==============================================================================
def safely_to_relative(path: Path) -> Path:
    """
    Returns the relative version of `path` with respect to the working directory;
    if the working directory is not a parent of `path`, it simply returns `path`
    unchanged.
    """
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


# ==============================================================================
# Others
# ==============================================================================
@contextlib.contextmanager
def suppressed_output() -> Generator[None, None, None]:
    """Suppresses all stdout and stderr output for the enclosed code."""
    with (
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        yield
