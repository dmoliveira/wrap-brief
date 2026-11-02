from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from wrap_brief.state.local import LocalState, StateConflict, StateError

from .test_snapshot import snapshot


class LocalStateTests(unittest.TestCase):
    def test_parent_is_owner_only_and_file_is_private_before_sqlite_initialization(self):
        public_parent = Path(self.temporary.name) / "not-private"
        public_parent.mkdir(mode=0o755)
        with self.assertRaises(StateError):
            LocalState(public_parent / "private.db")
        self.assertFalse((public_parent / "private.db").exists())
        with patch.object(
            LocalState, "_connect", side_effect=sqlite3.OperationalError("synthetic interruption")
        ):
            with self.assertRaises(StateError):
                LocalState(self.path)
        self.assertTrue(self.path.exists())
        self.assertEqual(self.path.stat().st_size, 0)
        self.assertEqual(self.path.stat().st_mode & 0o077, 0)
        self.assertEqual(LocalState(self.path).load().version, 0)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "private-state.sqlite3"
        self.value = snapshot()

    def test_commit_reload_idempotence_and_stale_expected_revision(self):
        store = LocalState(self.path)
        self.assertEqual(store.load().version, 0)
        committed = store.commit(self.value, expected_revision=0)
        self.assertEqual(committed.version, 1)
        self.assertEqual(committed.snapshot, self.value)
        self.assertEqual(store.commit(self.value, expected_revision=1), committed)
        with self.assertRaises(StateConflict):
            store.commit(self.value, expected_revision=0)
        self.assertEqual(LocalState(self.path).load(), committed)
        self.assertEqual(self.path.stat().st_mode & 0o077, 0)

    def test_two_writers_one_expected_revision_one_wins(self):
        LocalState(self.path)
        barrier = Barrier(2)

        def write(label):
            store = LocalState(self.path)
            value = replace(self.value, kind=label)
            barrier.wait(timeout=5)
            try:
                return store.commit(value, expected_revision=0).version
            except StateConflict:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(write, ["synthetic", "live"]))
        self.assertCountEqual(results, [1, "conflict"])
        self.assertEqual(LocalState(self.path).load().version, 1)

    def test_clear_is_monotonic_and_stale_writer_cannot_restore(self):
        store = LocalState(self.path)
        store.commit(self.value, expected_revision=0)
        cleared = store.clear(expected_revision=1)
        self.assertEqual(cleared.version, 2)
        self.assertIsNone(cleared.snapshot)
        self.assertEqual(store.clear(expected_revision=2), cleared)
        with self.assertRaises(StateConflict):
            store.commit(self.value, expected_revision=1)

    def test_interrupted_transaction_rolls_back_complete_state(self):
        store = LocalState(self.path)
        before = store.commit(self.value, expected_revision=0)
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE head SET revision=99,payload=NULL,digest=NULL")
        connection.close()
        self.assertEqual(store.load(), before)

    def test_cache_loss_and_failed_render_do_not_consume_seen_records(self):
        store = LocalState(self.path)
        store.commit(self.value, expected_revision=0)
        (Path(self.temporary.name) / "expired-cache").write_text("synthetic-cache")
        (Path(self.temporary.name) / "expired-cache").unlink()
        rebuilt = LocalState(self.path).load().snapshot
        self.assertEqual(rebuilt.items, self.value.items)
        self.assertEqual(rebuilt.clusters, self.value.clusters)

    def test_corrupt_checksum_and_schema_fail_closed(self):
        store = LocalState(self.path)
        store.commit(self.value, expected_revision=0)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE head SET digest=?", ("0" * 64,))
        with self.assertRaises(StateError):
            store.load()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("PRAGMA user_version=99")
        with self.assertRaises(StateError):
            LocalState(self.path)

    def test_foreign_database_is_never_overwritten(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("CREATE TABLE unrelated (data TEXT)")
        self.path.chmod(0o600)
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(StateError):
            LocalState(self.path)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

    def test_lost_file_is_not_recreated_by_load_or_commit(self):
        store = LocalState(self.path)
        self.path.unlink()
        with self.assertRaises(StateError):
            store.load()
        with self.assertRaises(StateError):
            store.commit(self.value, expected_revision=0)
        self.assertFalse(self.path.exists())

    def test_path_permissions_symlinks_and_errors_are_private(self):
        for path in (Path(self.temporary.name) / "not-a-database.txt", Path(self.temporary.name)):
            with self.assertRaises(StateError) as caught:
                LocalState(path)
            self.assertNotIn(self.temporary.name, str(caught.exception))
        store = LocalState(self.path)
        alias = Path(self.temporary.name) / "alias.sqlite3"
        alias.symlink_to(self.path)
        with self.assertRaises(StateError):
            LocalState(alias)
        self.path.chmod(0o644)
        with self.assertRaises(StateError):
            store.load()

    def test_sql_like_metadata_is_data_not_commands(self):
        item = replace(self.value.items[0], title="Synthetic quote '); DROP TABLE head; --")
        value = replace(
            self.value, items=tuple(item if i.id == item.id else i for i in self.value.items)
        )
        store = LocalState(self.path)
        store.commit(value, expected_revision=0)
        self.assertEqual(store.load().snapshot, value)


if __name__ == "__main__":
    unittest.main()
