"""Tests for backend.plugins.plugin_store"""
import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from backend.plugins.plugin_store import PluginStore, StorePluginInfo


class TestStorePluginInfo:
    def test_to_dict(self):
        info = StorePluginInfo(name="test", version="1.0", description="desc")
        d = info.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0"

    def test_from_manifest(self):
        from backend.plugins.plugin_manifest import PluginManifest
        manifest = PluginManifest(
            name="test_plugin", version="2.0", description="A test",
            plugin_type="tool", author="dev", license="MIT",
        )
        info = StorePluginInfo.from_manifest(manifest, source="builtin")
        assert info.name == "test_plugin"
        assert info.source == "builtin"


class TestPluginStore:
    @pytest.fixture
    def store(self, tmp_path):
        data_dir = str(tmp_path / "store")
        install_dir = str(tmp_path / "installed")
        s = PluginStore(data_dir=data_dir, plugin_install_dir=install_dir)
        return s

    # --- Database ---

    def test_init_db(self, store):
        assert os.path.exists(store._db_path)

    def test_add_remote(self, store):
        result = store.add_remote("https://example.com/api", name="test")
        assert result is True

    def test_add_remote_duplicate(self, store):
        store.add_remote("https://example.com/api")
        result = store.add_remote("https://example.com/api")
        assert result is False

    def test_remove_remote(self, store):
        store.add_remote("https://example.com/api")
        result = store.remove_remote("https://example.com/api")
        assert result is True
        assert "https://example.com/api" not in store._remotes

    def test_remove_remote_not_in_list(self, store):
        result = store.remove_remote("https://nonexistent.com")
        assert result is True

    def test_list_remotes(self, store):
        store.add_remote("https://example.com/api", name="test")
        remotes = store.list_remotes()
        assert len(remotes) >= 1

    # --- Search ---

    def test_search_empty(self, store):
        results = store.search()
        assert isinstance(results, list)

    def test_search_by_query(self, store):
        # Insert a plugin directly into DB
        info = StorePluginInfo(name="my_cool_plugin", version="1.0", description="Cool stuff")
        store._upsert_installed(info, install_path="test")
        results = store.search(query="cool")
        assert len(results) >= 1

    def test_search_by_category(self, store):
        info = StorePluginInfo(name="cat_plugin", version="1.0", description="desc", plugin_type="tool")
        store._upsert_installed(info, install_path="test")
        results = store.search(category="tool")
        assert len(results) >= 1

    def test_search_by_source(self, store):
        info = StorePluginInfo(name="src_plugin", version="1.0", description="desc", source="remote")
        store._upsert_installed(info, install_path="test")
        results = store.search(source="remote")
        assert len(results) >= 1

    def test_search_by_tags(self, store):
        info = StorePluginInfo(name="tag_plugin", version="1.0", description="desc", tags=["ai", "nlp"])
        store._upsert_installed(info, install_path="test")
        results = store.search(tags=["ai"])
        assert len(results) >= 1

    # --- Install/Uninstall/Update ---

    def test_install_builtin(self, store):
        # Add a fake builtin
        info = StorePluginInfo(name="fake_builtin", version="1.0", description="desc", source="builtin")
        store._builtin_cache["fake_builtin"] = info
        result = store.install("fake_builtin")
        assert result["success"] is True

    def test_install_already_installed(self, store):
        info = StorePluginInfo(name="already", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        result = store.install("already")
        assert result["success"] is False

    def test_install_not_found(self, store):
        result = store.install("nonexistent_plugin_xyz")
        assert result["success"] is False

    def test_install_remote_with_mock(self, store):
        plugin_data = {
            "name": "remote_plugin",
            "version": "1.0",
            "description": "A remote plugin",
            "download_url": "http://example.com/plugin.zip",
            "signature": "sig123",
        }
        with patch.object(store, "_fetch_remote_plugin", return_value=plugin_data):
            with patch.object(store, "_download_and_extract", return_value=os.path.join(os.sep, "tmp", "plugin")):
                # Create a fake plugin.json
                with patch("backend.plugins.plugin_store.PluginManifest") as MockManifest:
                    mock_manifest = MagicMock()
                    mock_manifest.name = "remote_plugin"
                    mock_manifest.version = "1.0"
                    mock_manifest.description = "desc"
                    mock_manifest.plugin_type = "general"
                    mock_manifest.author = ""
                    mock_manifest.license = "MIT"
                    mock_manifest.homepage = ""
                    mock_manifest.repository = ""
                    mock_manifest.tags = []
                    mock_manifest.icon = ""
                    mock_manifest.to_dict.return_value = {}
                    mock_manifest.dependencies = {}
                    MockManifest.from_file.return_value = mock_manifest
                    with patch("backend.plugins.plugin_store.os.path.exists", return_value=True):
                        with patch("backend.plugins.plugin_store.get_plugin_manager", return_value=MagicMock()):
                            result = store.install("remote_plugin")
                            assert result["success"] is True

    def test_uninstall_not_installed(self, store):
        result = store.uninstall("nonexistent")
        assert result["success"] is False

    def test_uninstall_builtin(self, store):
        info = StorePluginInfo(name="builtin_plug", version="1.0", description="desc", source="builtin")
        store._upsert_installed(info, install_path="builtin")
        result = store.uninstall("builtin_plug")
        assert result["success"] is False

    def test_uninstall_remote(self, store):
        info = StorePluginInfo(name="remote_plug", version="1.0", description="desc", source="remote")
        store._upsert_installed(info, install_path="/tmp/plugin")
        with patch("plugins.plugin_store.get_plugin_manager", return_value=MagicMock()):
            with patch("plugins.plugin_store.os.path.isdir", return_value=True):
                with patch("plugins.plugin_store.shutil.rmtree"):
                    result = store.uninstall("remote_plug")
                    assert result["success"] is True

    def test_update_not_installed(self, store):
        result = store.update("nonexistent")
        assert result["success"] is False

    def test_check_updates(self, store):
        info = StorePluginInfo(name="up_plugin", version="1.0", description="desc", source="remote", remote_url="http://example.com")
        store._upsert_installed(info, install_path="test")
        with patch.object(store, "_fetch_remote_plugin", return_value=None):
            updates = store.check_updates()
            assert isinstance(updates, list)

    # --- Enable/Disable ---

    def test_enable(self, store):
        info = StorePluginInfo(name="enable_test", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        # First disable it
        store._db_execute_commit("UPDATE installed_plugins SET enabled = 0 WHERE name = ?", ("enable_test",))
        result = store.enable("enable_test")
        assert result["success"] is True

    def test_enable_not_installed(self, store):
        result = store.enable("nonexistent")
        assert result["success"] is False

    def test_enable_already_enabled(self, store):
        info = StorePluginInfo(name="already_on", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        result = store.enable("already_on")
        assert result["success"] is False

    def test_disable(self, store):
        info = StorePluginInfo(name="disable_test", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        with patch("plugins.plugin_store.get_plugin_manager", return_value=MagicMock()):
            result = store.disable("disable_test")
            assert result["success"] is True

    def test_disable_not_installed(self, store):
        result = store.disable("nonexistent")
        assert result["success"] is False

    def test_disable_already_disabled(self, store):
        info = StorePluginInfo(name="already_off", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        store._db_execute_commit("UPDATE installed_plugins SET enabled = 0 WHERE name = ?", ("already_off",))
        result = store.disable("already_off")
        assert result["success"] is False

    # --- Plugin Info ---

    def test_get_plugin_info_from_builtin(self, store):
        info = StorePluginInfo(name="builtin_info", version="1.0", description="desc", source="builtin")
        store._builtin_cache["builtin_info"] = info
        result = store.get_plugin_info("builtin_info")
        assert result is not None
        assert result["name"] == "builtin_info"

    def test_get_plugin_info_from_db(self, store):
        info = StorePluginInfo(name="db_info", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        result = store.get_plugin_info("db_info")
        assert result is not None

    def test_get_plugin_info_missing(self, store):
        assert store.get_plugin_info("nonexistent") is None

    def test_list_installed(self, store):
        info = StorePluginInfo(name="listed", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        result = store.list_installed()
        assert len(result) >= 1

    def test_list_installed_enabled_only(self, store):
        info = StorePluginInfo(name="enabled_one", version="1.0", description="desc")
        store._upsert_installed(info, install_path="test")
        result = store.list_installed(enabled_only=True)
        assert all(r["enabled"] for r in result)

    # --- Security Audit ---

    def test_audit_pass(self, store):
        data = {"name": "p", "version": "1.0", "description": "desc"}
        result = store._audit_plugin(data, verify_signature=False)
        assert result["passed"] is True

    def test_audit_missing_field(self, store):
        data = {"name": "p"}
        result = store._audit_plugin(data)
        assert result["passed"] is False

    def test_audit_dangerous_permissions(self, store):
        data = {"name": "p", "version": "1.0", "description": "desc",
                "manifest": {"permissions": ["shell"]}}
        result = store._audit_plugin(data, verify_signature=False)
        assert len(result["warnings"]) > 0

    def test_audit_callback_blocks(self, store):
        data = {"name": "p", "version": "1.0", "description": "desc"}
        store.add_audit_callback(lambda d: {"passed": False, "reason": "blocked"})
        result = store._audit_plugin(data, verify_signature=False)
        assert result["passed"] is False

    def test_audit_callback_exception(self, store):
        data = {"name": "p", "version": "1.0", "description": "desc"}
        store.add_audit_callback(lambda d: (_ for _ in ()).throw(RuntimeError("fail")))
        result = store._audit_plugin(data, verify_signature=False)
        assert result["passed"] is True  # callback failure doesn't block

    def test_verify_signature_empty(self, store):
        assert store._verify_signature("", "sig") is False

    def test_verify_signature_present(self, store):
        assert store._verify_signature("hash123", "sig456") is True

    # --- Publish ---

    def test_publish_not_found(self, store):
        result = store.publish("nonexistent")
        assert result["success"] is False

    def test_publish_builtin(self, store):
        info = StorePluginInfo(name="pub_builtin", version="1.0", description="desc", source="builtin")
        store._builtin_cache["pub_builtin"] = info
        # The builtin dir may not exist, so mock
        with patch("plugins.plugin_store.os.path.isdir", return_value=False):
            result = store.publish("pub_builtin")
            assert result["success"] is False

    # --- Sync Remote ---

    def test_sync_remote_failure(self, store):
        results = store.sync_remote("https://nonexistent.invalid/api")
        assert results == []

    # --- _fetch_remote_plugin ---

    def test_fetch_remote_plugin_failure(self, store):
        result = store._fetch_remote_plugin("nonexistent")
        assert result is None

    # --- _download_and_extract ---

    def test_download_and_extract_no_url(self, store):
        with pytest.raises(ValueError):
            store._download_and_extract({"name": "p"})

    # --- Dependencies ---

    def test_install_dependencies_empty(self, store):
        manifest = MagicMock()
        manifest.dependencies = {}
        result = store._install_dependencies(manifest)
        assert result["success"] is True

    def test_install_dependencies_pip_fail(self, store):
        manifest = MagicMock()
        manifest.dependencies = {"pip:nonexistent_pkg_xyz": "*"}
        with patch("plugins.plugin_store.subprocess.run", side_effect=Exception("fail")):
            result = store._install_dependencies(manifest)
            assert result["success"] is False

    # --- Match search ---

    def test_match_search_no_filters(self, store):
        info = StorePluginInfo(name="test", version="1.0", description="desc")
        assert store._match_search(info, "", None, None, None) is True

    def test_match_search_wrong_source(self, store):
        info = StorePluginInfo(name="test", version="1.0", description="desc", source="builtin")
        assert store._match_search(info, "", None, None, "remote") is False

    def test_match_search_wrong_category(self, store):
        info = StorePluginInfo(name="test", version="1.0", description="desc", plugin_type="tool")
        assert store._match_search(info, "", "agent", None, None) is False

    def test_match_search_wrong_tags(self, store):
        info = StorePluginInfo(name="test", version="1.0", description="desc", tags=["ai"])
        assert store._match_search(info, "", None, ["nlp"], None) is False

    def test_match_search_query_not_found(self, store):
        info = StorePluginInfo(name="test", version="1.0", description="desc")
        assert store._match_search(info, "xyz", None, None, None) is False
