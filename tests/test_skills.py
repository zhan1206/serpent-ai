# -*- coding: utf-8 -*-
"""Tests for skills module - skill.py, skill_installer.py, skill_store.py"""

import os
import json
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from skills.skill import Skill, SkillManifest
from skills.skill_installer import SkillInstaller
from skills.skill_store import SkillStore


# ---- SkillManifest ----

class TestSkillManifest:
    def test_init_defaults(self):
        m = SkillManifest(name="test")
        assert m.name == "test"
        assert m.version == "1.0.0"
        assert m.display_name == "test"
        assert m.description == ""
        assert m.tags == []
        assert m.tools == []
        assert m.required_plugins == []
        assert m.examples == []

    def test_init_full(self):
        m = SkillManifest(
            name="test", version="2.0.0", display_name="Test Skill",
            description="desc", author="dev", license="Apache",
            category="coding", tags=["a", "b"], icon="icon.png",
            tools=["t1"], required_plugins=["p1"],
            prompt_template="prompt", examples=[{"q": "hi", "a": "hey"}],
            config_schema={"key": "val"}, homepage="http://h", repository="http://r",
        )
        assert m.name == "test"
        assert m.version == "2.0.0"
        assert m.display_name == "Test Skill"
        assert m.tags == ["a", "b"]
        assert m.tools == ["t1"]
        assert len(m.examples) == 1

    def test_from_dict(self):
        data = {"name": "x", "version": "3.0.0", "author": "a"}
        m = SkillManifest.from_dict(data)
        assert m.name == "x"
        assert m.version == "3.0.0"
        assert m.author == "a"

    def test_from_dict_defaults(self):
        m = SkillManifest.from_dict({"name": "y"})
        assert m.version == "1.0.0"
        assert m.display_name == "y"
        assert m.category == "general"

    def test_from_dict_display_name_fallback(self):
        m = SkillManifest.from_dict({"name": "z", "display_name": "Z Skill"})
        assert m.display_name == "Z Skill"

    def test_to_dict(self):
        m = SkillManifest(name="t", version="1.0.0", author="a")
        d = m.to_dict()
        assert d["name"] == "t"
        assert d["version"] == "1.0.0"
        assert d["author"] == "a"

    def test_to_json(self):
        m = SkillManifest(name="t", version="1.0.0")
        j = m.to_json()
        parsed = json.loads(j)
        assert parsed["name"] == "t"

    def test_from_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            SkillManifest.from_file("/nonexistent/skill.json")

    def test_from_file_invalid_json(self, tmp_path):
        f = tmp_path / "skill.json"
        f.write_text("not json", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON"):
            SkillManifest.from_file(str(f))

    def test_from_file_success(self, tmp_path):
        data = {"name": "file_skill", "version": "1.0.0"}
        f = tmp_path / "skill.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        m = SkillManifest.from_file(str(f))
        assert m.name == "file_skill"


# ---- Skill ----

class TestSkill:
    def test_properties(self, tmp_path):
        m = SkillManifest(name="prop_test", version="1.0.0", display_name="Prop")
        s = Skill(m, str(tmp_path))
        assert s.name == "prop_test"
        assert s.version == "1.0.0"
        assert s.installed_at is None
        assert s.rating == 0.0
        assert s.rating_count == 0
        assert s.enabled is True

    def test_get_info(self, tmp_path):
        m = SkillManifest(
            name="info_test", version="2.0.0", display_name="Info",
            description="test desc", author="dev", category="coding",
            tags=["a"], tools=["t1"],
        )
        s = Skill(m, str(tmp_path))
        s.installed_at = "2026-01-01"
        s.rating = 4.5
        s.rating_count = 10
        info = s.get_info()
        assert info["name"] == "info_test"
        assert info["version"] == "2.0.0"
        assert info["display_name"] == "Info"
        assert info["description"] == "test desc"
        assert info["category"] == "coding"
        assert info["tags"] == ["a"]
        assert info["installed_at"] == "2026-01-01"
        assert info["rating"] == 4.5
        assert info["rating_count"] == 10
        assert info["enabled"] is True


# ---- SkillInstaller ----

class TestSkillInstaller:
    @pytest.fixture
    def installer(self, tmp_path):
        return SkillInstaller(str(tmp_path / "skills"))

    def test_init_creates_dir(self, tmp_path):
        d = str(tmp_path / "new_dir")
        SkillInstaller(d)
        assert os.path.isdir(d)

    def test_install_from_dict(self, installer, tmp_path):
        data = {"name": "dict_skill", "version": "1.0.0"}
        skill = installer.install_from_dict(data)
        assert skill.name == "dict_skill"
        skill_dir = os.path.join(installer.install_dir, "dict_skill")
        assert os.path.isfile(os.path.join(skill_dir, "skill.json"))

    def test_install_from_file_json(self, installer, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        data = {"name": "file_skill", "version": "1.0.0"}
        (src / "skill.json").write_text(json.dumps(data), encoding="utf-8")
        skill = installer.install_from_file(str(src / "skill.json"))
        assert skill.name == "file_skill"
        assert os.path.isdir(os.path.join(installer.install_dir, "file_skill"))

    def test_install_from_file_zip(self, installer, tmp_path):
        import zipfile
        zip_path = str(tmp_path / "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("myskill/skill.json", json.dumps({"name": "zip_skill", "version": "1.0.0"}))
        skill = installer.install_from_file(zip_path)
        assert skill.name == "zip_skill"

    def test_install_from_file_zip_no_manifest(self, installer, tmp_path):
        import zipfile
        zip_path = str(tmp_path / "bad.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "hello")
        with pytest.raises(ValueError, match="skill.json"):
            installer.install_from_file(zip_path)

    def test_uninstall_existing(self, installer):
        installer.install_from_dict({"name": "to_remove"})
        assert installer.uninstall("to_remove") is True
        assert not os.path.isdir(os.path.join(installer.install_dir, "to_remove"))

    def test_uninstall_missing(self, installer):
        assert installer.uninstall("nonexistent") is False

    def test_update_skill_installed(self, installer):
        installer.install_from_dict({"name": "updatable"})
        result = installer.update_skill("updatable")
        assert result is None  # no url provided

    def test_update_skill_not_installed(self, installer):
        with pytest.raises(ValueError):
            installer.update_skill("nonexistent")

    def test_install_from_url_json(self, installer):
        data = {"name": "url_skill", "version": "1.0.0"}
        with patch("skills.skill_installer.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(data).encode("utf-8")
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            skill = installer.install_from_url("http://example.com/skill.json")
        assert skill.name == "url_skill"

    def test_install_from_url_zip(self, installer, tmp_path):
        import zipfile, io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("s/skill.json", json.dumps({"name": "url_zip", "version": "1.0.0"}))
        with patch("skills.skill_installer.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = buf.getvalue()
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            skill = installer.install_from_url("http://example.com/skill.zip")
        assert skill.name == "url_zip"

    def test_install_from_url_github(self, installer):
        data = {"name": "gh_skill", "version": "1.0.0"}
        with patch("skills.skill_installer.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(data).encode("utf-8")
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            skill = installer.install_from_url("https://github.com/user/repo")
        assert skill.name == "gh_skill"

    def test_install_from_github_direct(self, installer):
        data = {"name": "gh_direct", "version": "1.0.0"}
        with patch("skills.skill_installer.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(data).encode("utf-8")
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            skill = installer.install_from_github("https://github.com/user/repo", branch="dev")
        assert skill.name == "gh_direct"

    def test_install_from_github_invalid_url(self, installer):
        with pytest.raises(ValueError, match="GitHub URL"):
            installer.install_from_github("https://github.com/onlyuser")

    def test_install_from_github_git_suffix(self, installer):
        data = {"name": "git_suffix", "version": "1.0.0"}
        with patch("skills.skill_installer.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(data).encode("utf-8")
            mock_resp.__enter__ = lambda s: mock_resp
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            skill = installer.install_from_github("https://github.com/user/repo.git")
        assert skill.name == "git_suffix"


# ---- SkillStore ----

class TestSkillStore:
    @pytest.fixture
    def store(self, tmp_path):
        install_dir = tmp_path / "installed"
        install_dir.mkdir()
        return SkillStore([str(install_dir)])

    def test_init(self, store):
        assert store.skill_dirs

    def test_discover_all(self, store, tmp_path):
        d = tmp_path / "installed"
        s1_dir = d / "skill_a"
        s1_dir.mkdir()
        (s1_dir / "skill.json").write_text(json.dumps({"name": "skill_a", "version": "1.0.0", "category": "coding"}), encoding="utf-8")
        s2_dir = d / "skill_b"
        s2_dir.mkdir()
        (s2_dir / "skill.json").write_text(json.dumps({"name": "skill_b", "version": "1.0.0", "category": "general"}), encoding="utf-8")
        discovered = store.discover_all()
        assert "skill_a" in discovered
        assert "skill_b" in discovered
        assert store.get_skill("skill_a") is not None

    def test_discover_empty(self, store):
        discovered = store.discover_all()
        assert discovered == []

    def test_get(self, store, tmp_path):
        d = tmp_path / "installed"
        s_dir = d / "get_test"
        s_dir.mkdir()
        (s_dir / "skill.json").write_text(json.dumps({"name": "get_test", "version": "1.0.0"}), encoding="utf-8")
        store.discover_all()
        s = store.get_skill("get_test")
        assert s is not None
        assert s.name == "get_test"
        assert store.get_skill("nonexistent") is None

    def test_remove(self, store, tmp_path):
        d = tmp_path / "installed"
        s_dir = d / "rm_test"
        s_dir.mkdir()
        (s_dir / "skill.json").write_text(json.dumps({"name": "rm_test", "version": "1.0.0"}), encoding="utf-8")
        store.discover_all()
        result = store.remove_skill("rm_test")
        assert result is True
        assert store.get_skill("rm_test") is None

    def test_remove_missing(self, store):
        assert store.remove_skill("nonexistent") is False

    def test_list_all(self, store, tmp_path):
        d = tmp_path / "installed"
        for name in ["a", "b"]:
            sd = d / name
            sd.mkdir()
            (sd / "skill.json").write_text(json.dumps({"name": name, "version": "1.0.0"}), encoding="utf-8")
        store.discover_all()
        skills = store.list_skills()
        assert len(skills) == 2

    def test_search(self, store, tmp_path):
        d = tmp_path / "installed"
        sd = d / "search_test"
        sd.mkdir()
        (sd / "skill.json").write_text(json.dumps({"name": "search_test", "version": "1.0.0", "description": "find me", "tags": ["search"]}), encoding="utf-8")
        store.discover_all()
        results = store.search("find")
        assert len(results) >= 1

    def test_get_stats(self, store, tmp_path):
        d = tmp_path / "installed"
        for name, cat in [("a", "coding"), ("b", "general")]:
            sd = d / name
            sd.mkdir()
            (sd / "skill.json").write_text(json.dumps({"name": name, "version": "1.0.0", "category": cat}), encoding="utf-8")
        store.discover_all()
        stats = store.get_stats()
        assert stats["total"] == 2

    def test_add_skill_dir(self, store, tmp_path):
        new_dir = tmp_path / "extra"
        new_dir.mkdir()
        store.add_skill_dir(str(new_dir))
        assert len(store.skill_dirs) >= 2

    def test_enable_disable(self, store, tmp_path):
        d = tmp_path / "installed"
        sd = d / "ed_test"
        sd.mkdir()
        (sd / "skill.json").write_text(json.dumps({"name": "ed_test", "version": "1.0.0"}), encoding="utf-8")
        store.discover_all()
        store.disable_skill("ed_test")
        s = store.get_skill("ed_test")
        assert s.enabled is False
        store.enable_skill("ed_test")
        assert store.get_skill("ed_test").enabled is True

    def test_rate_skill(self, store, tmp_path):
        d = tmp_path / "installed"
        sd = d / "rate_test"
        sd.mkdir()
        (sd / "skill.json").write_text(json.dumps({"name": "rate_test", "version": "1.0.0"}), encoding="utf-8")
        store.discover_all()
        store.rate_skill("rate_test", 5)
        s = store.get_skill("rate_test")
        assert s.rating > 0

    def test_get_categories(self, store, tmp_path):
        d = tmp_path / "installed"
        for name, cat in [("c1", "coding"), ("c2", "coding"), ("g1", "general")]:
            sd = d / name
            sd.mkdir()
            (sd / "skill.json").write_text(json.dumps({"name": name, "version": "1.0.0", "category": cat}), encoding="utf-8")
        store.discover_all()
        cats = store.get_categories()
        assert "coding" in cats
        assert "general" in cats

    def test_install_skill(self, store, tmp_path):
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        skill = store.install_skill({"name": "inst_test", "version": "1.0.0"}, str(target_dir))
        assert skill is not None
        assert store.get_skill("inst_test") is not None
