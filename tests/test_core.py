from pathlib import Path

from filesystem.core import find_empty_directories


# Support code for tests
# ------------------------------------------------------------------------------
def setup_test_folder(
    *, root: Path, empty_dirs: list[str], non_empty_dirs: dict[str, list[str]]
) -> None:
    """
    Creates empty directories and non-empty directories with files.

    - `empty_dirs`: List of empty directory names.
    - `non_empty_dirs`: Dictionary where keys are directory names, and values are
       lists of filenames inside them.
    """
    for dirname in empty_dirs:
        (root / dirname).mkdir(parents=True, exist_ok=True)

    for dirname, files in non_empty_dirs.items():
        folder = root / dirname
        folder.mkdir(parents=True, exist_ok=True)
        # create nonempty files
        for file in files:
            (folder / file).write_text("dummy content")


# Tests
# ------------------------------------------------------------------------------
def test_can_find_immediate_empty_folders(tmp_path: Path) -> None:
    setup_test_folder(
        root=tmp_path,
        empty_dirs=["folder-1", "folder-2"],
        non_empty_dirs={"folder-3": ["test.txt"]},
    )
    result = {p.name for p in find_empty_directories(tmp_path)}
    assert result == {"folder-1", "folder-2"}


def test_can_find_nested_empty_folder(tmp_path: Path) -> None:
    setup_test_folder(
        root=tmp_path,
        empty_dirs=["folder-1", "folder-2/subfolder"],
        non_empty_dirs={"folder-3": ["test.txt"], "folder-4/nested": ["file.txt"]},
    )
    result = {p.relative_to(tmp_path) for p in find_empty_directories(tmp_path)}
    assert result == {Path("folder-1"), Path("folder-2/subfolder")}


def test_can_find_nested_empty_folders_dynamically(tmp_path: Path) -> None:
    """
    Test that, being a generator, `find_empty_directories` can return folders
    which become empty after children empty folders are yielded and deleted.
    """
    setup_test_folder(
        root=tmp_path,
        empty_dirs=["empties-parent/empty-1", "empties-parent/empty-2"],
        non_empty_dirs={"folder-2": ["test.txt"], "folder-3/nested": ["file.txt"]},
    )
    folders = find_empty_directories(tmp_path)
    first = next(folders)
    first.rmdir()
    second = next(folders)
    second.rmdir()
    # after deleting the two nested folders, the parent should now be empty too
    assert next(folders) == (tmp_path / "empties-parent")
