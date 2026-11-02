"""Owned-file SQLite development adapter. Not runner-durable or a live backend."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from wrap_brief.models import ContractError
from wrap_brief.state.snapshot import MAX_SNAPSHOT_BYTES, Snapshot

_APP_ID = 0x57524246
_DB_VERSION = 1
_MAGIC = "wrap-brief-local-state-v1"


class StateError(ValueError):
    pass


class StateConflict(StateError):
    def __init__(self):
        super().__init__("state: version conflict")


@dataclass(frozen=True, slots=True)
class Revision:
    version: int
    snapshot: Snapshot | None
    digest: str | None


class LocalState:
    def __init__(self, path: Path):
        if not isinstance(path, Path) or path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            raise StateError("state: private database path required")
        self.path = path.absolute()
        try:
            self._path_check()
            try:
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                initialize = self.path.stat().st_size == 0
            else:
                os.close(descriptor)
                initialize = True
            with closing(self._connect("rw")) as connection:
                connection.execute("BEGIN IMMEDIATE")
                app = connection.execute("PRAGMA application_id").fetchone()[0]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                objects = connection.execute(
                    "SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if initialize and app == 0 and version == 0 and not objects:
                    connection.execute(
                        "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                    )
                    connection.execute(
                        "CREATE TABLE head (singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL CHECK(revision>=0), payload BLOB, digest TEXT)"
                    )
                    connection.execute("INSERT INTO metadata VALUES (?,?)", ("format", _MAGIC))
                    connection.execute("INSERT INTO head VALUES (1,0,NULL,NULL)")
                    connection.execute(f"PRAGMA application_id={_APP_ID}")
                    connection.execute(f"PRAGMA user_version={_DB_VERSION}")
                self._owned(connection)
                self._read(connection)
                connection.commit()
        except (OSError, sqlite3.Error):
            raise StateError("state: cannot initialize local store") from None

    def _path_check(self) -> None:
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            raise StateError("state: regular private database required")
        if self.path.exists() and self.path.stat().st_mode & 0o077:
            raise StateError("state: private file permissions required")
        if (
            self.path.parent.is_symlink()
            or not self.path.parent.is_dir()
            or self.path.parent.stat().st_mode & 0o077
        ):
            raise StateError("state: private parent directory required")

    def _connect(self, mode: str) -> sqlite3.Connection:
        self._path_check()
        connection = sqlite3.connect(
            self.path.as_uri() + "?mode=" + mode, uri=True, timeout=5, isolation_level=None
        )
        try:
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA secure_delete=ON")
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    @staticmethod
    def _owned(connection: sqlite3.Connection) -> None:
        valid = (
            connection.execute("PRAGMA application_id").fetchone()[0] == _APP_ID
            and connection.execute("PRAGMA user_version").fetchone()[0] == _DB_VERSION
        )
        objects = set(
            connection.execute(
                "SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
        )
        if not valid or objects != {("metadata", "table"), ("head", "table")}:
            raise StateError("state: incompatible database")
        expected = {
            "metadata": [("key", "TEXT", 1), ("value", "TEXT", 0)],
            "head": [
                ("singleton", "INTEGER", 1),
                ("revision", "INTEGER", 0),
                ("payload", "BLOB", 0),
                ("digest", "TEXT", 0),
            ],
        }
        for table, columns in expected.items():
            actual = [
                (r[1], r[2], r[5]) for r in connection.execute("PRAGMA table_info(" + table + ")")
            ]
            if actual != columns:
                raise StateError("state: incompatible database schema")
        if connection.execute("SELECT key,value FROM metadata LIMIT 2").fetchall() != [
            ("format", _MAGIC)
        ]:
            raise StateError("state: incompatible database metadata")
        if connection.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            raise StateError("state: unsupported local journal mode")

    @staticmethod
    def _read(connection: sqlite3.Connection) -> Revision:
        rows = connection.execute(
            "SELECT singleton,revision,digest,length(payload),typeof(payload) FROM head LIMIT 2"
        ).fetchall()
        if len(rows) != 1:
            raise StateError("state: corrupt state head")
        singleton, version, digest, size, kind = rows[0]
        if singleton != 1 or type(version) is not int or version < 0:
            raise StateError("state: corrupt state version")
        if size is None:
            if digest is not None or kind != "null":
                raise StateError("state: corrupt empty state")
            return Revision(version, None, None)
        if (
            kind != "blob"
            or not 0 < size <= MAX_SNAPSHOT_BYTES
            or not isinstance(digest, str)
            or len(digest) != 64
        ):
            raise StateError("state: corrupt state payload")
        payload = connection.execute("SELECT payload FROM head WHERE singleton=1").fetchone()[0]
        if hashlib.sha256(payload).hexdigest() != digest:
            raise StateError("state: snapshot checksum mismatch")
        try:
            snapshot = Snapshot.from_json(payload)
        except ContractError:
            raise StateError("state: invalid snapshot") from None
        return Revision(version, snapshot, digest)

    def load(self) -> Revision:
        try:
            with closing(self._connect("ro")) as connection:
                connection.execute("BEGIN")
                self._owned(connection)
                return self._read(connection)
        except (OSError, sqlite3.Error):
            raise StateError("state: cannot read local store") from None

    def commit(self, snapshot: Snapshot, *, expected_revision: int) -> Revision:
        if type(snapshot) is not Snapshot:
            raise StateError("state: validated snapshot required")
        payload = snapshot.to_json()
        return self._write(payload, expected_revision)

    def clear(self, *, expected_revision: int) -> Revision:
        return self._write(None, expected_revision)

    def _write(self, payload: bytes | None, expected: int) -> Revision:
        if type(expected) is not int or expected < 0:
            raise StateError("state: nonnegative expected revision required")
        digest = hashlib.sha256(payload).hexdigest() if payload is not None else None
        try:
            with closing(self._connect("rw")) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._owned(connection)
                current = self._read(connection)
                if current.version != expected:
                    raise StateConflict()
                if current.digest == digest:
                    connection.rollback()
                    return current
                connection.execute(
                    "UPDATE head SET revision=?,payload=?,digest=? WHERE singleton=1 AND revision=?",
                    (expected + 1, payload, digest, expected),
                )
                connection.commit()
                return Revision(
                    expected + 1,
                    Snapshot.from_json(payload) if payload is not None else None,
                    digest,
                )
        except (OSError, sqlite3.Error):
            raise StateError("state: cannot commit local store") from None
