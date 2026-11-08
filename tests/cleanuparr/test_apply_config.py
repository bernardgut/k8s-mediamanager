"""Tests for charts/k8s-mediamanager/files/cleanuparr/apply_config.py (stdlib only).

Run from the repository root: python3 -m unittest discover -s tests/cleanuparr -v
The Helm rendering tests run only when helm is on PATH.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
CHART = REPO / "charts" / "k8s-mediamanager"
SCRIPT = CHART / "files" / "cleanuparr" / "apply_config.py"
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("apply_config", SCRIPT)
ac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ac)
FIXTURE = Path(__file__).parent / "fixtures" / f"fresh-{ac.SUPPORTED_APP_VERSION}.sql"

SONARR_KEY = "fake-sonarr-api-key-5f1c2e"
RADARR_KEY = "fake-radarr-api-key-7a9d0b"
QBT_USER = "fake-qbt-user-31"
QBT_PASSWORD = "fake-qbt-password-8842"
API_KEY = "c0ffee" * 10 + "abcd"
PASSWORD_HASH = "$2b$12$" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0"
FAKE_SECRETS = (SONARR_KEY, RADARR_KEY, QBT_USER, QBT_PASSWORD, API_KEY, PASSWORD_HASH)
PATTERNS = ["No files found are eligible for import", "Caution: Found", "Found archive file",
            "Unable to parse file", "Unable to determine if file is a sample", "were unexpected considering",
            "Invalid season or episode"]


def sample_desired():
    """A typical rendered desired state (queue cleaner, two *arr instances, one client), fake secrets."""
    return {
        "schema": 1, "appVersion": ac.SUPPORTED_APP_VERSION, "mode": "apply",
        "auth": {"username": "", "passwordHash": "", "apiKey": ""},
        "general": {"dryRun": True, "statusCheckEnabled": False},
        "queueCleaner": {
            "enabled": True, "cronExpression": "0 0/10 * ? * * *", "downloadingMetadataMaxStrikes": 12,
            "failedImport": {"maxStrikes": 3, "ignorePrivate": True, "skipIfNotFoundInClient": True,
                             "patternMode": "include", "patterns": list(PATTERNS)},
            "stallRules": [{"name": "public-stalled", "enabled": True, "maxStrikes": 18, "privacyType": "public",
                            "minCompletionPercentage": 0, "maxCompletionPercentage": 100,
                            "resetStrikesOnProgress": True, "minimumProgress": "100MB",
                            "deletePrivateTorrentsFromClient": False, "changeCategory": False}],
        },
        "seeker": {"searchEnabled": False, "proactiveSearchEnabled": False},
        "arr": {
            "sonarr": {"instances": [{"name": "sonarr", "version": 4, "apiKey": SONARR_KEY,
                                      "url": "http://kmm-k8s-mediamanager-sonarr:8989/sonarr",
                                      "externalUrl": "https://k8s-mediamanager.example.test/sonarr"}]},
            "radarr": {"instances": [{"name": "radarr", "version": 6, "apiKey": RADARR_KEY,
                                      "url": "http://kmm-k8s-mediamanager-radarr:7878/radarr",
                                      "externalUrl": "https://k8s-mediamanager.example.test/radarr"}]},
        },
        "downloadClients": [{"name": "qBittorrent", "typeName": "qbittorrent",
                             "host": "http://kmm-k8s-mediamanager-qbittorrent:8080", "urlBase": "",
                             "username": QBT_USER, "password": QBT_PASSWORD,
                             "externalUrl": "https://k8s-mediamanager.example.test"}],
        "notifications": [],
    }


def make_config_dir(root):
    """Writes cleanuparr.db, events.db and users.db from the fixture into root."""
    sections, current = {}, None
    for line in FIXTURE.read_text().splitlines(keepends=True):
        if line.startswith("-- database: "):
            current = line.split(": ", 1)[1].strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    for name, lines in sections.items():
        con = sqlite3.connect(os.path.join(root, name))
        con.executescript("".join(lines))
        con.execute("PRAGMA journal_mode = WAL")
        con.close()
    return root


_OPEN = []


def db(root, name="cleanuparr.db"):
    """Autocommit connection, so injected drift lands even without commit(); closed in tearDown."""
    con = sqlite3.connect(os.path.join(root, name), isolation_level=None)
    _OPEN.append(con)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def write_json(root, data, name="desired.json"):
    path = os.path.join(root, name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return path


def run(*argv, env=None):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), mock.patch.dict(os.environ, env or {}):
        code = ac.main(list(argv))
    return code, out.getvalue()


def plan_lines(output):
    prefix = "cleanuparr-config: "
    keep = ("UPDATE ", "INSERT ", "DELETE ", "EVENTS.DB ")
    return [line[len(prefix):] for line in output.splitlines()
            if line.startswith(prefix) and line[len(prefix):].startswith(keep)]


def file_hashes(root):
    return {n: hashlib.sha256(Path(root, n).read_bytes()).hexdigest()
            for n in ("cleanuparr.db", "events.db", "users.db")}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cleanuparr-cfg-")
        self.config = os.path.join(self.tmp, "config")
        os.mkdir(self.config)
        make_config_dir(self.config)

    def tearDown(self):
        while _OPEN:
            _OPEN.pop().close()
        shutil.rmtree(self.tmp)

    def reconcile(self, desired, *extra):
        path = write_json(self.tmp, desired)
        return run("reconcile", "--desired", path, "--config-dir", self.config, *extra)

    def apply_ok(self, desired, *extra):
        code, out = self.reconcile(desired, *extra)
        self.assertEqual(code, 0, out)
        return out


# -- validation -------------------------------------------------------------------------------
def _set(data, path, value):
    node = data
    keys = path.split(".")
    for key in keys[:-1]:
        node = node[int(key)] if isinstance(node, list) else node.setdefault(key, {})
    if isinstance(node, list):
        node[int(keys[-1])] = value
    else:
        node[keys[-1]] = value


class ValidationTest(unittest.TestCase):
    def errors(self, desired, check_paths=False):
        errs = []
        ds = ac.normalize(ac.DESIRED, desired, ac.VALUES, errs)
        if not errs:
            ac.validate_semantics(ds, errs, check_paths, ac._unsupported_rule_fields(desired, ds))
        return errs

    def assertInvalid(self, desired, needle, check_paths=False):
        errs = self.errors(desired, check_paths)
        self.assertTrue(any(needle in e for e in errs), f"{needle!r} not in {errs}")
        for secret in FAKE_SECRETS:
            self.assertFalse(any(secret in e for e in errs), "a validation message leaks a secret")

    def test_sample_desired_is_valid(self):
        self.assertEqual(self.errors(sample_desired()), [])

    def test_null_means_default(self):
        d = sample_desired()
        d["queueCleaner"]["stallRules"][0]["minimumProgress"] = None
        d["general"]["log"] = None
        self.assertEqual(self.errors(d), [])

    def test_touching_rule_ranges_are_allowed(self):
        d = sample_desired()
        d["queueCleaner"]["stallRules"] = [
            {"name": "low", "maxCompletionPercentage": 50}, {"name": "high", "minCompletionPercentage": 50}]
        self.assertEqual(self.errors(d), [])

    CASES = [
        ("unknownKey", True, "unknown key"),
        ("general.unknown", 1, "general.unknown: unknown key"),
        ("general.dryRun", "true", "must be true or false"),
        ("general.http.timeout", 0, "below the minimum 1"),
        ("general.http.maxRetries", 70000, "above the maximum 65535"),
        ("general.strikeInactivityWindowHours", 169, "above the maximum 168"),
        ("general.historyRetentionDays", 0, "below the minimum 1"),
        ("general.connectivityCheckEnabled", True, "needs at least one URL"),
        ("general.connectivityCheckUrls", ["ftp://x"], "absolute http(s) URL"),
        ("general.auth.trustedNetworks", ["10.0.0.0/33"], "IP address or a CIDR"),
        ("general.auth.trustedNetworks", ["10.0.0.1,10.0.0.2"], "must not contain ','"),
        ("general.log.level", "infomation", "is not one of"),
        ("general.log.rollingSizeMB", 101, "above the maximum 100"),
        ("general.log.archiveTimeLimitHours", 1441, "above the maximum 1440"),
        ("queueCleaner.downloadingMetadataMaxStrikes", 2, "must be 0 or at least 3"),
        ("queueCleaner.failedImport.maxStrikes", 1, "must be 0 or at least 3"),
        ("queueCleaner.failedImport.patterns", [], "include mode needs at least one pattern"),
        ("queueCleaner.failedImport.patterns", ["ok", " "], "must not be blank"),
        ("queueCleaner.failedImport.patternMode", "regex", "is not one of"),
        ("queueCleaner.cronExpression", "0 0 12 * * ?", "at least every 5 hours"),
        ("queueCleaner.cronExpression", "0/10 * * ? * *", "more often than every 30 seconds"),
        ("queueCleaner.cronExpression", "", "required"),
        ("queueCleaner.cronExpression", "0 0/\u0665 * ? * * *", "unsupported minute field"),
        ("malwareBlocker.cronExpression", "   ", "required"),
        ("downloadCleaner.cronExpression", "0 0 0/6 ? * * *", "at least every 5 hours"),
        ("queueCleaner.stallRules.0.maxStrikes", 5001, "above the maximum 5000"),
        ("queueCleaner.stallRules.0.minimumProgress", "100\u00a0MB", "must be a size"),
        ("general.auth.trustedNetworks", ["10.0.0.0/\u0662\u0664"], "IP address or a CIDR"),
        ("seeker.searchInterval", 360, "must be one of"),
        ("queueCleaner.stallRules.0.maxStrikes", 2, "below the minimum 3"),
        ("queueCleaner.stallRules.0.minimumProgress", "100 MiB", "must be a size"),
        ("queueCleaner.stallRules.0.maxCompletionPercentage", 0, "below the minimum 1"),
        ("queueCleaner.stallRules.0.privacyType", "all", "is not one of"),
        ("queueCleaner.stallRules.0.name", "  ", "required"),
        ("seeker.searchInterval", 7, "must be one of"),
        ("seeker.postReleaseGraceHours", 73, "above the maximum 72"),
        ("seeker.selectionStrategy", "fifo", "is not one of"),
        ("arr.sonarr.instances.0.version", 3, "must be one of 4"),
        ("arr.sonarr.instances.0.url", "kmm-sonarr:8989", "absolute http(s) URL"),
        ("arr.sonarr.instances.0.apiKey", "", "required"),
        ("arr.sonarr.failedImportMaxStrikes", 2, "-1, 0 or at least 3"),
        ("arr.sonarr.instances.0.seeker", {"activeDownloadLimit": 101}, "above the maximum 100"),
        ("arr.lidarr.instances", [{"name": "l", "url": "http://l:8686", "apiKey": "k", "seeker": {}}],
         "seeker: unknown key"),
        ("arr.whisparr.instances", [{"name": "w", "url": "http://w:6969", "apiKey": "k", "version": 4}],
         "must be one of 2, 3"),
        ("downloadClients.0.typeName", "qbit", "is not one of"),
        ("downloadClients.0.host", "", "required"),
        ("downloadClients.0.password", "•" * 8, "placeholder"),
        ("downloadClients.0.downloadDirectorySource", "/downloads", "set downloadDirectorySource and"),
        ("downloadClients.0.fromChart", "qbittorrent", "fromChart: unknown key"),
        ("mode", "dry", "is not one of"),
        ("auth.apiKey", "XYZ", "64 lowercase hex"),
        ("auth.username", "ab", "3 to 50 characters"),
        ("auth.passwordHash", PASSWORD_HASH, "set username and passwordHash together"),
        ("auth.passwordHash", "plain-text", "must be a bcrypt hash"),
        ("auth.passwordHash", "$2b$\u0661\u0662$" + "a" * 53, "must be a bcrypt hash"),
    ]

    def test_invalid_values(self):
        for path, value, needle in self.CASES:
            with self.subTest(path=path, value=value):
                d = sample_desired()
                _set(d, path, value)
                self.assertInvalid(d, needle)

    def test_cross_field_rules(self):
        d = sample_desired()
        d["queueCleaner"]["failedImport"].update(changeCategory=True, deletePrivate=True)
        self.assertInvalid(d, "changeCategory and deletePrivate")
        d = sample_desired()
        d["queueCleaner"]["failedImport"].update(forceImport=True, forceImportMaxTries=0)
        self.assertInvalid(d, "1..5000")
        d = sample_desired()
        d["queueCleaner"]["stallRules"].append({"name": "PUBLIC-STALLED", "enabled": False})
        self.assertInvalid(d, "used twice")
        d = sample_desired()
        d["queueCleaner"]["stallRules"][0].update(minCompletionPercentage=60, maxCompletionPercentage=50)
        self.assertInvalid(d, "below minCompletionPercentage")
        d = sample_desired()
        d["queueCleaner"]["stallRules"][0].update(changeCategory=True, deletePrivateTorrentsFromClient=True)
        self.assertInvalid(d, "changeCategory and deletePrivateTorrentsFromClient")
        d = sample_desired()
        d["queueCleaner"]["stallRules"].append({"name": "both", "privacyType": "both",
                                                "minCompletionPercentage": 50})
        self.assertInvalid(d, "overlap for public")
        d = sample_desired()
        d["queueCleaner"]["slowRules"] = [{"name": "slow"}]
        self.assertInvalid(d, "set minSpeed or a maxTimeHours")
        d = sample_desired()
        d["malwareBlocker"] = {"enabled": True}
        self.assertInvalid(d, "at least one enabled blocklist")
        d = sample_desired()
        d["malwareBlocker"] = {"enabled": True, "sonarr": {"enabled": True}}
        self.assertInvalid(d, "required when the sonarr blocklist is enabled")
        d = sample_desired()
        d["malwareBlocker"] = {"enabled": True, "sonarr": {"enabled": True, "blocklistPath": "/config/none.txt"}}
        self.assertEqual(self.errors(d, check_paths=False), [])
        self.assertInvalid(d, "http(s) URL or an existing file", check_paths=True)
        d = sample_desired()
        d["blacklistSync"] = {"enabled": True}
        self.assertInvalid(d, "required when blacklistSync is enabled")
        d = sample_desired()
        d["seeker"]["proactiveSearchEnabled"] = True
        self.assertInvalid(d, "needs a sonarr or radarr instance with seeker.enabled")
        d["arr"]["sonarr"]["instances"][0]["seeker"] = {"enabled": True}
        self.assertEqual(self.errors(d), [])
        d["arr"]["sonarr"]["instances"][0]["enabled"] = False  # the app accepts a paused instance
        self.assertEqual(self.errors(d), [])
        d = sample_desired()
        d["arr"]["sonarr"]["instances"].append(dict(d["arr"]["sonarr"]["instances"][0], name="SONARR"))
        self.assertInvalid(d, "is used twice")

    def test_client_children_rules(self):
        base = sample_desired()["downloadClients"][0]
        cases = [
            (dict(base, typeName="deluge", seedingRules=[{"name": "r", "categories": ["c"], "maxRatio": 1,
                                                          "tagsAny": ["x"]}]), "not supported by deluge"),
            (dict(base, seedingRules=[{"name": "r", "categories": []}]), "needs at least one category"),
            (dict(base, seedingRules=[{"name": "r", "categories": ["c"]}]), "set maxRatio or maxSeedTime"),
            (dict(base, seedingRules=[{"name": "r", "categories": ["c"], "maxRatio": -2}]),
             "must be -1 (off) or at least 0"),
            (dict(base, seedingRules=[{"name": "r", "categories": ["c"], "maxRatio": 1, "action": "pause"}]),
             "is not one of"),
            (dict(base, typeName="rtorrent", deadTorrents={"enabled": True, "maxStrikes": 3, "categories": ["c"]}),
             "rtorrent reports no seeder count"),
            (dict(base, deadTorrents={"enabled": True, "categories": ["c"]}), "at least 3 when enabled"),
            (dict(base, unlinked={"enabled": True, "categories": ["cleanuparr-unlinked"]}),
             "must not contain targetCategory"),
            (dict(base, orphanedFiles={"enabled": True, "scanDirectories": ["/data/torrents"],
                                       "orphanedDirectory": "/data"}), "must not equal or contain"),
            (dict(base, orphanedFiles={"enabled": True, "scanDirectories": []}), "needs at least one directory"),
        ]
        for client, needle in cases:
            with self.subTest(needle=needle):
                d = sample_desired()
                d["downloadClients"] = [client]
                self.assertInvalid(d, needle)
        d = sample_desired()
        other = dict(base, name="other", downloadDirectorySource="/downloads", downloadDirectoryTarget="/data/dl")
        d["downloadClients"] = [dict(base, orphanedFiles={"enabled": True, "scanDirectories": ["/data/dl/x"],
                                                          "orphanedDirectory": "/orphans"}), other]
        self.assertInvalid(d, "overlaps '/data/dl' of client 'other'")
        d = sample_desired()
        d["downloadClients"] = [dict(base, unlinked={"enabled": True, "categories": ["c"],
                                                     "ignoredRootDirs": ["/nonexistent-dir"]})]
        self.assertEqual(self.errors(d), [])
        self.assertInvalid(d, "directory does not exist", check_paths=True)

    def test_notifications(self):
        def note(**kw):
            d = sample_desired()
            d["notifications"] = [kw]
            return d
        self.assertEqual(self.errors(note(name="n", type="ntfy", ntfy={"serverUrl": "https://ntfy.example",
                                                                         "topics": ["t"]})), [])
        self.assertInvalid(note(name="n", type="ntfy", gotify={"serverUrl": "https://g", "applicationToken": "x"}),
                           "exactly one provider block")
        self.assertInvalid(note(name="n", type="ntfy", ntfy={"serverUrl": "https://n", "topics": []}),
                           "needs at least one topic")
        self.assertInvalid(note(name="n", type="ntfy", ntfy={"serverUrl": "https://n", "topics": ["t"],
                                                              "authenticationType": "basicauth"}),
                           "basicauth needs username and password")
        self.assertInvalid(note(name="n", type="discord", discord={"webhookUrl": "https://example.com/hook"}),
                           "Discord webhook")
        self.assertInvalid(note(name="n", type="pushover", pushover={"apiToken": "a", "userKey": "u",
                                                                      "priority": "emergency"}),
                           "emergency priority needs at least 30 seconds")
        self.assertInvalid(note(name="n", type="pushover", pushover={"apiToken": "a", "userKey": "u",
                                                                      "devices": ["bad device"]}),
                           "letters, digits")
        self.assertInvalid(note(name="n", type="telegram", telegram={"botToken": "1234567890", "chatId": "abc"}),
                           "must be an integer")
        self.assertInvalid(note(name="n", type="telegram", telegram={"botToken": "1234567890",
                                                                       "chatId": "\u0661\u0662\u0663"}),
                           "must be an integer")
        self.assertInvalid(note(name="n", type="notifiarr", notifiarr={"apiKey": "short", "channelId": "1"}),
                           "at least 10 characters")
        self.assertInvalid(note(name="n", type="apprise", apprise={"mode": "cli"}), "required in cli mode")
        self.assertInvalid(note(name="n", type="gotify", gotify={"serverUrl": "https://g",
                                                                 "applicationToken": "t", "priority": 11}),
                           "above the maximum 10")
        d = note(name="n", type="ntfy", ntfy={"serverUrl": "https://n", "topics": ["t"]})
        d["notifications"].append(dict(d["notifications"][0], name="N"))
        self.assertInvalid(d, "is used twice")


class CronTest(unittest.TestCase):
    # The UI's schedule-picker forms (schedule.util.ts:8-26) except 6 hours, which the DST rule rejects.
    UI_FORMS = (["0/30 * * ? * * *"]
                + [f"0 0/{n} * ? * * *" for n in (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30)]
                + [f"0 0 0/{n} ? * * *" for n in (1, 2, 3, 4)])

    def test_seeded_and_ui_forms_pass(self):
        self.assertIsNone(ac.cron_error("0 0/5 * * * ?", "queueCleaner"))
        self.assertIsNone(ac.cron_error("0/5 * * * * ?", "malwareBlocker"))
        self.assertIsNone(ac.cron_error("0 0 * * * ?", "downloadCleaner"))
        for expression in self.UI_FORMS:
            for job in ("queueCleaner", "downloadCleaner", "malwareBlocker"):
                with self.subTest(expression=expression, job=job):
                    self.assertIsNone(ac.cron_error(expression, job))

    def test_rejections(self):
        cases = [
            ("0 0 12 * * ?", "queueCleaner"),           # once a day
            ("0 0 0,1 * * ?", "queueCleaner"),          # 23 h overnight gap
            ("0 0 0/7 ? * *", "queueCleaner"),          # 7 h gap
            ("0 0 0/6 ? * * *", "queueCleaner"),        # the UI's 6 h option: 7 h on a DST night
            ("0/10 * * * * ?", "queueCleaner"),         # below the 30 s floor
            ("0/10 * * * * ?", "downloadCleaner"),
            ("0 0 0 L * ?", "queueCleaner"),
            ("0 0 0 ? * MON", "queueCleaner"),
            ("0 0 0 ? * 2#1", "queueCleaner"),
            ("0 0/5 * * * *", "queueCleaner"),          # neither day field is '?'
            ("0 0/5 * ? * ?", "queueCleaner"),
            ("0 0/5 * ? 1 *", "queueCleaner"),          # month
            ("0 0/5 * ? * * 2027", "queueCleaner"),     # year
            ("0 0/5 *  ? * *", "queueCleaner"),         # double space
            ("0 0/5 * ? *", "queueCleaner"),            # five fields
            ("0 0/60 * ? * *", "queueCleaner"),         # increment out of range
            ("0 0 0/24 ? * *", "queueCleaner"),
            ("0 5-3 * ? * *", "queueCleaner"),          # inverted range
            ("0 *,5 * ? * *", "queueCleaner"),          # '*' inside a list
            ("0 0 0/1 15W * ?", "queueCleaner"),
            ("0 0,30 8-20 ? * *", "malwareBlocker"),    # 11.5 h overnight gap
        ]
        for expression, job in cases:
            with self.subTest(expression=expression, job=job):
                self.assertIsNotNone(ac.cron_error(expression, job))
        self.assertIsNone(ac.cron_error("0/10 * * * * ?", "malwareBlocker"))
        self.assertIsNone(ac.cron_error("0 0 0/5 ? * *", "queueCleaner"))  # 4 h overnight gap is fine

    def test_every_accepted_form_passes_the_startup_check_across_dst(self):
        # The app checks the real time between the next two local fires (BackgroundJobManager.cs:228-257);
        # walk the Europe/Zurich fall-back and spring-forward nights.
        import datetime
        from zoneinfo import ZoneInfo
        zone = ZoneInfo("Europe/Zurich")
        for expression in self.UI_FORMS + ["0 0/5 * * * ?", "0 0 * * * ?", "0 0 0/5 ? * *"]:
            fields = expression.split()
            secs = ac._cron_field(fields[0], "s", 59)
            mins = ac._cron_field(fields[1], "m", 59)
            hours = ac._cron_field(fields[2], "h", 23)
            for day in (datetime.date(2026, 10, 24), datetime.date(2027, 3, 27)):
                # A set: local times skipped by spring-forward land on instants that exist anyway.
                fires = sorted({datetime.datetime.combine(day + datetime.timedelta(days=d),
                                                          datetime.time(h, m, s), zone).timestamp()
                                for d in range(3) for h in hours for m in mins for s in secs})
                gaps = [b - a for a, b in zip(fires, fires[1:])]
                with self.subTest(expression=expression, day=day):
                    self.assertLessEqual(max(gaps), 6 * 3600)
                    self.assertGreaterEqual(min(gaps), 30)


# -- plan and apply on the fresh fixture ----------------------------------------------------
class ApplyTest(Base):
    def test_fresh_volume_gets_the_validated_write_set(self):
        out = self.apply_ok(sample_desired())
        lines = plan_lines(out)
        expected_updates = {
            "UPDATE general_configs dry_run: false -> true",
            "UPDATE general_configs status_check_enabled: true -> false",
            "UPDATE queue_cleaner_configs enabled: false -> true",
            "UPDATE queue_cleaner_configs cron_expression: '0 0/5 * * * ?' -> '0 0/10 * ? * * *'",
            "UPDATE queue_cleaner_configs failed_import_max_strikes: 0 -> 3",
            "UPDATE queue_cleaner_configs failed_import_ignore_private: false -> true",
            "UPDATE queue_cleaner_configs downloading_metadata_max_strikes: 0 -> 12",
            "UPDATE seeker_configs search_enabled: true -> false",
        }
        self.assertTrue(expected_updates <= set(lines), lines)
        self.assertTrue(any(l.startswith("UPDATE queue_cleaner_configs failed_import_patterns: [] -> [")
                            for l in lines))
        inserts = sorted(l.split(" {")[0] for l in lines if l.startswith("INSERT "))
        self.assertEqual(inserts, [
            "INSERT arr_instances[radarr/radarr]", "INSERT arr_instances[sonarr/sonarr]",
            "INSERT download_clients[qBittorrent]", "INSERT seeker_instance_configs[radarr/radarr]",
            "INSERT seeker_instance_configs[sonarr/sonarr]", "INSERT stall_rules[public-stalled]"])
        self.assertEqual(len(lines), 15)
        self.assertIn("15 changes applied", out)
        self.assertIn("setup wizard", out)
        con = db(self.config)
        client = con.execute("SELECT * FROM download_clients").fetchone()
        self.assertEqual((client["type"], client["url_base"], client["download_directory_source"]),
                         ("torrent", "", None))
        sonarr = con.execute("SELECT i.*, c.type FROM arr_instances i JOIN arr_configs c "
                             "ON c.id = i.arr_config_id WHERE i.name = 'sonarr'").fetchone()
        self.assertEqual((sonarr["type"], sonarr["version"], sonarr["id"]), ("sonarr", 4.0, sonarr["id"].upper()))
        seeker = con.execute("SELECT * FROM seeker_instance_configs WHERE arr_instance_id = ?",
                             (sonarr["id"],)).fetchone()
        self.assertEqual((seeker["enabled"], seeker["total_eligible_items"], seeker["last_processed_at"]),
                         (0, 0, None))
        rule = con.execute("SELECT * FROM stall_rules").fetchone()
        qc = con.execute("SELECT id, failed_import_patterns FROM queue_cleaner_configs").fetchone()
        self.assertEqual(rule["queue_cleaner_config_id"], qc["id"])
        self.assertEqual(json.loads(qc["failed_import_patterns"]), PATTERNS)
        self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_second_run_is_a_no_op(self):
        self.apply_ok(sample_desired())
        before = file_hashes(self.config)
        out = self.apply_ok(sample_desired())
        self.assertIn("no changes", out)
        self.assertEqual(plan_lines(out), [])
        self.assertEqual(before, file_hashes(self.config))

    def test_plan_mode_writes_nothing(self):
        before = file_hashes(self.config)
        code, out = self.reconcile(sample_desired(), "--mode", "plan")
        self.assertEqual(code, 0, out)
        self.assertIn("plan only, 15 changes not applied", out)
        self.assertEqual(before, file_hashes(self.config))

    def test_ui_drift_is_reverted_and_logged(self):
        self.apply_ok(sample_desired())
        con = db(self.config)
        qc_id = con.execute("SELECT id FROM queue_cleaner_configs").fetchone()[0]
        con.executescript(f"""
            UPDATE queue_cleaner_configs SET enabled = 0, failed_import_patterns = '["x"]';
            UPDATE download_clients SET password = 'changed-in-the-ui', enabled = 0;
            UPDATE arr_instances SET name = 'Sonarr' WHERE name = 'sonarr';
            UPDATE general_configs SET auth_trusted_networks = '10.0.0.0/8', log_level = 'Debug';
            INSERT INTO stall_rules (id, reset_strikes_on_progress, minimum_progress, queue_cleaner_config_id,
                name, enabled, max_strikes, privacy_type, min_completion_percentage, max_completion_percentage,
                delete_private_torrents_from_client, change_category)
            VALUES ('AAAAAAAA-0000-0000-0000-000000000001', 1, NULL, '{qc_id}', 'ui-rule', 1, 3, 'private', 0,
                100, 0, 0);
        """)
        con.close()
        out = self.apply_ok(sample_desired())
        lines = plan_lines(out)
        for expected in ("UPDATE queue_cleaner_configs enabled: false -> true",
                         "UPDATE download_clients[qBittorrent] password: (secret changed)",
                         "UPDATE download_clients[qBittorrent] enabled: false -> true",
                         "UPDATE arr_instances[sonarr/sonarr] name: 'Sonarr' -> 'sonarr'",
                         "UPDATE general_configs auth_trusted_networks: ['10.0.0.0/8'] -> []",
                         "UPDATE general_configs log_level: 'debug' -> 'information'",
                         "DELETE stall_rules[ui-rule] (not in values)"):
            self.assertIn(expected, lines)
        self.assertNotIn("changed-in-the-ui", out)
        self.assertIn("no changes", self.apply_ok(sample_desired()))

    def test_semantic_equality_avoids_churn(self):
        d = sample_desired()
        d["general"]["ignoredDownloads"] = ["café", "a/b"]
        d["general"]["auth"] = {"trustedNetworks": ["10.0.0.0/8", "192.168.0.0/16"]}
        d["arr"]["readarr"] = {"instances": [{"name": "readarr", "url": "http://readarr:8787",
                                              "apiKey": "fake-readarr-key"}]}
        self.apply_ok(d)
        con = db(self.config)
        con.executescript("""
            UPDATE general_configs SET ignored_downloads = '[ "caf\\u00E9", "a\\/b" ]',
                log_level = ' INFORMATION', http_certificate_validation = 'Enabled';
            UPDATE arr_instances SET version = 0.4000000059604645 WHERE name = 'readarr';
            UPDATE download_clients SET external_url = 'https://k8s-mediamanager.example.test';
        """)
        con.close()
        out = self.apply_ok(d)
        self.assertIn("no changes", out)

    def test_empty_as_null_and_url_base(self):
        d = sample_desired()
        d["downloadClients"][0]["externalUrl"] = ""
        self.apply_ok(d)
        con = db(self.config)
        self.assertIsNone(con.execute("SELECT external_url FROM download_clients").fetchone()[0])
        con.execute("UPDATE download_clients SET external_url = '', url_base = NULL")
        con.close()
        lines = plan_lines(self.apply_ok(d))
        self.assertEqual(lines, ["UPDATE download_clients[qBittorrent] url_base: None -> ''"])

    def test_duplicate_rows_keep_the_smallest_id(self):
        self.apply_ok(sample_desired())
        con = db(self.config)
        con.execute("""INSERT INTO download_clients (id, enabled, name, type_name, type, host)
                       VALUES ('00000000-0000-0000-0000-000000000000', 1, 'QBITTORRENT', 'qbittorrent',
                       'torrent', 'http://elsewhere:8080')""")
        old_id = con.execute("SELECT id FROM download_clients WHERE name = 'qBittorrent'").fetchone()[0]
        con.close()
        lines = plan_lines(self.apply_ok(sample_desired()))
        self.assertIn(f"DELETE download_clients[qBittorrent] (not in values; cascades 0 blacklist_sync_history rows)",
                      lines)
        con = db(self.config)
        rows = con.execute("SELECT id, name, host FROM download_clients").fetchall()
        self.assertEqual([(r["id"], r["name"]) for r in rows],
                         [("00000000-0000-0000-0000-000000000000", "qBittorrent")])
        self.assertNotEqual(rows[0]["id"], old_id)

    def test_client_removal_cascades_and_rules_follow_type(self):
        d = sample_desired()
        client = d["downloadClients"][0]
        client["seedingRules"] = [
            {"name": "movies", "categories": ["radarr"], "maxRatio": 2, "tagsAny": ["keep"]},
            {"name": "tv", "categories": ["tv-sonarr"], "maxSeedTime": 72}]
        client["unlinked"] = {"enabled": False}
        client["deadTorrents"] = {"enabled": True, "maxStrikes": 3, "categories": ["radarr"]}
        client["orphanedFiles"] = {"enabled": False}
        self.apply_ok(d)
        con = db(self.config)
        rows = con.execute("SELECT name, priority, tags_any, delete_source_files FROM q_bit_seeding_rules "
                           "ORDER BY priority").fetchall()
        self.assertEqual([tuple(r) for r in rows], [("movies", 1, '["keep"]', 1), ("tv", 2, "[]", 1)])
        client_id = con.execute("SELECT id FROM download_clients").fetchone()[0]
        con.execute("INSERT INTO blacklist_sync_history (id, hash, download_client_id) VALUES ('H1', 'abc', ?)",
                    (client_id,))
        con.close()
        client["seedingRules"].reverse()
        lines = plan_lines(self.apply_ok(d))
        self.assertIn("UPDATE q_bit_seeding_rules[qBittorrent/tv] priority: 2 -> 1", lines)
        client["typeName"] = "deluge"
        for rule in client["seedingRules"]:
            rule.pop("tagsAny", None)
        lines = plan_lines(self.apply_ok(d))
        self.assertIn("UPDATE download_clients[qBittorrent] type_name: 'qbittorrent' -> 'deluge'", lines)
        self.assertEqual(sum(l.startswith("DELETE q_bit_seeding_rules") for l in lines), 2)
        self.assertEqual(sum(l.startswith("INSERT deluge_seeding_rules") for l in lines), 2)
        con = db(self.config)
        self.assertEqual(con.execute("SELECT id FROM download_clients").fetchone()[0], client_id)
        con.close()
        d["downloadClients"] = []
        lines = plan_lines(self.apply_ok(d))
        self.assertIn("DELETE download_clients[qBittorrent] (not in values; cascades 1 blacklist_sync_history rows)",
                      lines)
        con = db(self.config)
        for table in ("download_clients", "deluge_seeding_rules", "unlinked_configs", "dead_torrent_configs",
                      "orphaned_files_configs", "blacklist_sync_history"):
            self.assertEqual(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0, table)

    def test_url_credentials_never_reach_the_log(self):
        d = sample_desired()
        d["downloadClients"][0]["host"] = "https://fake-user:FAKE-PW-123@qb.example.test/x?token=FAKE-TOKEN-456"
        # urlsplit reads "u:12" as host and port, so the unencoded "/" hides the userinfo from it.
        d["downloadClients"][0]["externalUrl"] = "https://u:12/34-FAKEPW@ext.example.test/#token=FAKE-FRAG-1"
        out = self.apply_ok(d)
        for secret in ("FAKE-PW-123", "FAKE-TOKEN-456", "34-FAKEPW", "FAKE-FRAG-1"):
            self.assertNotIn(secret, out)
        self.assertIn("host: 'https://(secret)@qb.example.test/x?(secret)'", out)
        con = db(self.config)
        self.assertEqual(con.execute("SELECT host FROM download_clients").fetchone()[0],
                         d["downloadClients"][0]["host"])

    def test_exit_4_when_the_check_still_differs(self):
        real = ac.execute_op

        def drop_general_updates(con, op):
            if not (op.action == "UPDATE" and op.table == "general_configs"):
                real(con, op)
        with mock.patch.object(ac, "execute_op", drop_general_updates):
            code, out = self.reconcile(sample_desired())
        self.assertEqual(code, 4, out)
        self.assertIn("committed cleanuparr.db", out)
        self.assertIn("NOT CONVERGED UPDATE general_configs dry_run: false -> true", out)

    def test_notifications_insert_update_and_type_change(self):
        d = sample_desired()
        d["notifications"] = [{"name": "phone", "type": "ntfy", "events": {"onStalledStrike": True},
                               "ntfy": {"serverUrl": "https://ntfy.example.test", "topics": ["media"],
                                        "authenticationType": "accesstoken", "accessToken": "fake-ntfy-token-1"}}]
        out = self.apply_ok(d)
        self.assertNotIn("fake-ntfy-token-1", out)
        con = db(self.config)
        parent = con.execute("SELECT * FROM notification_configs").fetchone()
        child = con.execute("SELECT * FROM ntfy_configs").fetchone()
        self.assertEqual((parent["type"], parent["on_stalled_strike"], child["notification_config_id"],
                          child["topics"], child["authentication_type"], child["priority"]),
                         ("ntfy", 1, parent["id"], '["media"]', "accesstoken", "default"))
        self.assertEqual(len(parent["created_at"]), 27)
        con.close()
        d["notifications"][0]["ntfy"]["topics"] = ["media", "alerts"]
        lines = plan_lines(self.apply_ok(d))
        self.assertIn("UPDATE ntfy_configs[phone] topics: ['media'] -> ['media', 'alerts']", lines)
        self.assertTrue(any(l.startswith("UPDATE notification_configs[phone] updated_at:") for l in lines))
        d["notifications"][0] = {"name": "phone", "type": "gotify",
                                 "gotify": {"serverUrl": "https://gotify.example.test",
                                            "applicationToken": "fake-gotify-token"}}
        lines = plan_lines(self.apply_ok(d))
        self.assertIn("DELETE ntfy_configs[phone] (provider type changed or duplicated)", lines)
        self.assertIn("UPDATE notification_configs[phone] type: 'ntfy' -> 'gotify'", lines)
        con = db(self.config)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ntfy_configs").fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT priority FROM gotify_configs").fetchone()[0], 5)
        con.close()
        d["notifications"] = []
        self.apply_ok(d)
        con = db(self.config)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM notification_configs").fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM gotify_configs").fetchone()[0], 0)


class EffectsTest(Base):
    def seed_events(self, sonarr_id):
        ev = db(self.config, "events.db")
        ev.executescript(f"""
            INSERT INTO job_runs (id, type, started_at) VALUES ('J1', 'queuecleaner', '2026-01-01 00:00:00.0000000');
            INSERT INTO download_items (id, download_id, title) VALUES ('A', 'a', 'dry only'), ('B', 'b', 'real'),
                ('C', 'c', 'both'), ('D', 'd', 'none');
            INSERT INTO strikes (id, created_at, download_item_id, job_run_id, type, is_dry_run) VALUES
                ('S1', 'x', 'A', 'J1', 'stalled', 1), ('S2', 'x', 'B', 'J1', 'stalled', 0),
                ('S3', 'x', 'C', 'J1', 'stalled', 1), ('S4', 'x', 'C', 'J1', 'stalled', 0);
            INSERT INTO events (id, event_type, failed_import_reasons, grabbed_items, is_dry_run, message, severity,
                timestamp, strike_id, arr_instance_id, search_status) VALUES
                ('E1', 'strike', '[]', '[]', 1, 'm', 'information', 't', 'S1', NULL, NULL),
                ('E2', 'strike', '[]', '[]', 0, 'm', 'information', 't', 'S3', NULL, NULL),
                ('E3', 'searchtriggered', '[]', '[]', 0, 'm', 'information', 't', NULL, '{sonarr_id}', 'pending'),
                ('E4', 'searchtriggered', '[]', '[]', 0, 'm', 'information', 't', NULL, '{sonarr_id}', 'completed');
            INSERT INTO manual_events (id, is_resolved, message, severity, timestamp, is_dry_run) VALUES
                ('M1', 0, 'm', 'warning', 't', 1), ('M2', 0, 'm', 'warning', 't', 0);
            INSERT INTO seeker_history (id, arr_instance_id, external_item_id, item_type, season_number, cycle_id,
                last_searched_at, item_title, search_count, is_dry_run) VALUES
                ('H1', '{sonarr_id}', 1, 'series', 1, 'C', 't', 'x', 1, 1),
                ('H2', '{sonarr_id}', 2, 'series', 1, 'C', 't', 'x', 1, 0);
            INSERT INTO search_queue (id, arr_instance_id, item_id, title, created_at) VALUES
                ('Q1', '{sonarr_id}', 1, 'x', 't');
            INSERT INTO seeker_command_trackers (id, arr_instance_id, command_id, event_id, external_item_id,
                item_title, season_number, created_at, status) VALUES ('T1', '{sonarr_id}', 1, 'E3', 1, 'x', 1, 't',
                'started');
            INSERT INTO custom_format_score_entries (id, arr_instance_id, external_item_id, episode_id, item_type,
                title, file_id, current_score, cutoff_score, quality_profile_name, is_monitored, last_synced_at)
                VALUES ('F1', '{sonarr_id}', 1, 0, 'series', 'x', 1, 0, 0, 'p', 1, 't');
            INSERT INTO custom_format_score_history (id, arr_instance_id, external_item_id, episode_id, item_type,
                title, score, cutoff_score, recorded_at) VALUES ('G1', '{sonarr_id}', 1, 0, 'series', 'x', 0, 0, 't');
        """)
        ev.close()

    def ids(self, table):
        ev = db(self.config, "events.db")
        try:
            return sorted(r[0] for r in ev.execute(f"SELECT id FROM {table}"))
        finally:
            ev.close()

    def test_dry_run_off_purges_exactly_the_dry_run_rows(self):
        self.apply_ok(sample_desired())
        sonarr_id = db(self.config).execute("SELECT id FROM arr_instances WHERE name = 'sonarr'").fetchone()[0]
        self.seed_events(sonarr_id)
        d = sample_desired()
        d["general"]["dryRun"] = False
        out = self.apply_ok(d)
        self.assertIn("EVENTS.DB dry-run purge (general.dryRun true -> false): 2 strikes, 1 events, "
                      "1 manual_events, 2 download_items, 1 seeker_history", out)
        self.assertEqual(self.ids("strikes"), ["S2", "S4"])
        self.assertEqual(self.ids("download_items"), ["B", "C"])
        self.assertEqual(self.ids("events"), ["E2", "E3", "E4"])
        self.assertEqual(self.ids("manual_events"), ["M2"])
        self.assertEqual(self.ids("seeker_history"), ["H2"])
        ev = db(self.config, "events.db")
        self.assertIsNone(ev.execute("SELECT strike_id FROM events WHERE id = 'E2'").fetchone()[0])
        ev.close()
        self.assertNotIn("EVENTS.DB", self.apply_ok(d))

    def test_deleting_an_instance_cleans_events_db(self):
        self.apply_ok(sample_desired())
        sonarr_id = db(self.config).execute("SELECT id FROM arr_instances WHERE name = 'sonarr'").fetchone()[0]
        self.seed_events(sonarr_id)
        d = sample_desired()
        d["arr"]["sonarr"]["instances"] = []
        out = self.apply_ok(d)
        lines = plan_lines(out)
        self.assertIn("DELETE arr_instances[sonarr/sonarr] (not in values; cascades its seeker_instance_configs "
                      "row; events.db: 7 rows)", lines)
        self.assertFalse(any(l.startswith("DELETE seeker_instance_configs") for l in lines), lines)
        for table in ("custom_format_score_entries", "custom_format_score_history", "seeker_history",
                      "search_queue", "seeker_command_trackers"):
            self.assertEqual(self.ids(table), [], table)
        ev = db(self.config, "events.db")
        rows = {r["id"]: (r["search_status"], r["completed_at"]) for r in
                ev.execute("SELECT id, search_status, completed_at FROM events WHERE id IN ('E3', 'E4')")}
        ev.close()
        self.assertEqual(rows["E3"][0], "failed")
        self.assertEqual(len(rows["E3"][1]), 27)
        self.assertEqual(rows["E4"], ("completed", None))
        con = db(self.config)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM seeker_instance_configs").fetchone()[0], 1)
        self.assertEqual(con.execute("SELECT name FROM arr_instances").fetchone()[0], "radarr")


    def test_preexisting_fk_violation_stops_before_any_write(self):
        self.apply_ok(sample_desired())
        sonarr_id = db(self.config).execute("SELECT id FROM arr_instances WHERE name = 'sonarr'").fetchone()[0]
        self.seed_events(sonarr_id)
        raw = sqlite3.connect(os.path.join(self.config, "cleanuparr.db"), isolation_level=None)
        raw.execute("PRAGMA foreign_keys = OFF")
        raw.execute("INSERT INTO blacklist_sync_history (id, hash, download_client_id) VALUES ('X', 'h', 'nobody')")
        raw.close()
        d = sample_desired()
        d["general"]["dryRun"] = False
        code, out = self.reconcile(d)
        self.assertEqual(code, 3, out)
        self.assertIn("cleanuparr.db: 1 blacklist_sync_history rows reference missing download_clients rows", out)
        self.assertEqual(self.ids("strikes"), ["S1", "S2", "S3", "S4"])
        self.assertEqual(db(self.config).execute("SELECT dry_run FROM general_configs").fetchone()[0], 1)

    def test_a_failure_mid_apply_leaves_every_database_untouched(self):
        self.apply_ok(sample_desired())
        sonarr_id = db(self.config).execute("SELECT id FROM arr_instances WHERE name = 'sonarr'").fetchone()[0]
        self.seed_events(sonarr_id)
        d = sample_desired()
        d["general"]["dryRun"] = False
        d["auth"] = {"username": "admin-test", "passwordHash": PASSWORD_HASH, "apiKey": API_KEY}
        real = ac.execute_op

        def fail_users(con, op):
            if op.db == ac.USERS_DB:
                raise sqlite3.OperationalError("disk I/O error")
            real(con, op)
        with mock.patch.object(ac, "execute_op", fail_users):
            code, out = self.reconcile(d)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.ids("strikes"), ["S1", "S2", "S3", "S4"])
        self.assertEqual(db(self.config).execute("SELECT dry_run FROM general_configs").fetchone()[0], 1)
        self.assertEqual(db(self.config, "users.db").execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
        self.assertNotIn("EVENTS.DB dry-run purge (general.dryRun true -> false) done", out)


class UsersTest(Base):
    def test_bootstrap_then_api_key_enforcement(self):
        d = sample_desired()
        d["auth"] = {"username": "admin-test", "passwordHash": PASSWORD_HASH, "apiKey": API_KEY}
        out = self.apply_ok(d)
        self.assertIn("INSERT users[admin-test] {username: 'admin-test', password_hash: (secret set), "
                      "api_key: (secret set), setup_completed: true}", plan_lines(out))
        con = db(self.config, "users.db")
        user = con.execute("SELECT * FROM users").fetchone()
        self.assertEqual((user["api_key"], user["setup_completed"], user["totp_enabled"], user["oidc_scopes"]),
                         (API_KEY, 1, 0, ""))
        con.execute("UPDATE users SET api_key = 'regenerated-in-the-ui', password_hash = 'changed'")
        con.commit()
        con.close()
        lines = plan_lines(self.apply_ok(d))
        self.assertEqual(len(lines), 2, lines)
        self.assertEqual(lines[0], "UPDATE users[admin-test] api_key: (secret changed)")
        self.assertTrue(lines[1].startswith("UPDATE users[admin-test] updated_at: "), lines)
        con = db(self.config, "users.db")
        user = con.execute("SELECT * FROM users").fetchone()
        self.assertEqual((user["api_key"], user["password_hash"]), (API_KEY, "changed"))
        d["auth"]["apiKey"] = ""
        out = self.apply_ok(d)
        self.assertIn("no changes", out)
        self.assertIn("the stored account is kept", out)

    def test_random_key_without_api_key(self):
        d = sample_desired()
        d["auth"] = {"username": "admin-test", "passwordHash": PASSWORD_HASH, "apiKey": ""}
        self.apply_ok(d)
        key = db(self.config, "users.db").execute("SELECT api_key FROM users").fetchone()[0]
        self.assertRegex(key, r"^[0-9a-f]{64}$")
        self.assertIn("no changes", self.apply_ok(d))


class GuardTest(Base):
    ENV = {"CLEANUPARR_IMAGE_TAG": "2.10.8@sha256:" + "ab" * 32}

    def assertGuard(self, needle, desired=None):
        code, out = self.reconcile(desired or sample_desired())
        self.assertEqual(code, 3, out)
        self.assertIn(needle, out)

    def test_unknown_migration(self):
        con = db(self.config)
        con.execute("""INSERT INTO "__EFMigrationsHistory" VALUES ('20991231000000_Future', '10.0.1')""")
        con.commit()
        self.assertGuard("unknown ['20991231000000_Future']")
        code, out = run("preflight", "--config-dir", self.config, env=self.ENV)
        self.assertEqual(code, 3, out)
        self.assertIn("20991231000000_Future", out)

    def test_missing_migration_and_missing_file(self):
        con = db(self.config, "users.db")
        con.execute("""DELETE FROM "__EFMigrationsHistory" WHERE migration_id LIKE '%UserFeatureViews'""")
        con.commit()
        self.assertGuard("missing ['20260614115255_AddUserFeatureViews']")
        os.remove(os.path.join(self.config, "events.db"))
        self.assertGuard("events.db does not exist")

    def test_migration_lock(self):
        con = db(self.config, "events.db")
        con.execute("""INSERT INTO "__EFMigrationsLock" VALUES (1, '2026-01-01')""")
        con.commit()
        self.assertGuard("__EFMigrationsLock holds a row")

    def test_column_drift(self):
        con = db(self.config)
        con.execute("ALTER TABLE general_configs ADD COLUMN new_setting INTEGER")
        con.commit()
        self.assertGuard("general_configs: columns differ (missing none, unexpected ['new_setting:INTEGER'])")

    def test_singleton_and_users_rows(self):
        con = db(self.config)
        row = dict(con.execute("SELECT * FROM download_cleaner_configs").fetchone())
        row["id"] = "FFFFFFFF-0000-0000-0000-000000000000"
        con.execute(f"INSERT INTO download_cleaner_configs ({', '.join(row)}) VALUES "
                    f"({', '.join('?' * len(row))})", list(row.values()))
        con.commit()
        self.assertGuard("download_cleaner_configs has 2 rows")

    def test_more_than_one_user(self):
        con = db(self.config, "users.db")
        for i in (1, 2):
            con.execute("INSERT INTO users (id, username, password_hash, totp_secret, totp_enabled, api_key, "
                        "setup_completed, failed_login_attempts, created_at, updated_at) "
                        "VALUES (?, ?, 'h', '', 0, ?, 1, 0, 't', 't')", (f"U{i}", f"user{i}", f"key{i}"))
        con.commit()
        self.assertGuard("users has 2 rows")

    def test_preflight(self):
        empty = os.path.join(self.tmp, "empty")
        os.mkdir(empty)
        self.assertEqual(run("preflight", "--config-dir", empty, env=self.ENV)[0], 0)
        self.assertEqual(run("preflight", "--config-dir", self.config, env=self.ENV)[0], 0)
        for tag in ("latest", "2.10.9", "2.10.8-rc1", "2.10.80", ""):
            with self.subTest(tag=tag):
                code, out = run("preflight", "--config-dir", empty, env={"CLEANUPARR_IMAGE_TAG": tag})
                self.assertEqual(code, 3, out)
        Path(self.config, "cleanuparr.json").write_text('{"base_path": "/x"}')
        code, out = run("preflight", "--config-dir", self.config, env=self.ENV)
        self.assertEqual(code, 3, out)
        self.assertIn("BASE_PATH", out)

    def test_preflight_refuses_a_leftover_migration_lock(self):
        db(self.config, "events.db").execute("""INSERT INTO "__EFMigrationsLock" VALUES (1, '2026-01-01')""")
        code, out = run("preflight", "--config-dir", self.config, env=self.ENV)
        self.assertEqual(code, 3, out)
        self.assertIn("events.db: __EFMigrationsLock holds a row from an interrupted migration", out)

    def test_preflight_checks_the_migrations_compiled_into_the_bundle(self):
        known = sorted({m for ids in ac.EXPECTED_MIGRATIONS.values() for m in ids})
        newest = f"{ac.IMAGE_NEWEST_MIGRATION}_RemoveEncryptionKey"

        def bundle(ids, pad=0):
            path = os.path.join(self.tmp, "Cleanuparr")
            with open(path, "wb") as handle:
                handle.write(b"\0" * pad)
                for migration_id in ids:
                    handle.write(b"\x01" + migration_id.encode() + b"\x02")
            return path
        # the newest id straddles the 8 MB read boundary
        ok = bundle([newest] + known, pad=(8 << 20) - 10)
        code, out = run("preflight", "--config-dir", self.config, "--app", ok, env=self.ENV)
        self.assertEqual(code, 0, out)
        for ids, needle in (([*known], "newest migration 20260912212027"),
                            ([newest, "20261101000000_AddSomething", *known], "newest migration 20261101000000"),
                            ([newest, *known[1:]], "1 known migrations missing")):
            with self.subTest(needle=needle):
                code, out = run("preflight", "--config-dir", self.config, "--app", bundle(ids), env=self.ENV)
                self.assertEqual(code, 3, out)
                self.assertIn(needle, out)

    def test_invalid_desired_state_exits_2_before_any_db_access(self):
        d = sample_desired()
        d["general"]["http"] = {"timeout": 0}
        os.remove(os.path.join(self.config, "users.db"))
        code, out = self.reconcile(d)
        self.assertEqual(code, 2, out)
        self.assertIn("nothing was written", out)
        d = sample_desired()
        d["appVersion"] = "2.10.9"
        self.assertEqual(self.reconcile(d)[0], 3)
        d["appVersion"], d["schema"] = ac.SUPPORTED_APP_VERSION, 2
        self.assertEqual(self.reconcile(d)[0], 2)


class ValidateCliTest(unittest.TestCase):
    def test_validate_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("validate", "--desired", write_json(tmp, sample_desired()))
            self.assertEqual(code, 0, out)
            bad = sample_desired()
            bad["queueCleaner"]["cronExpression"] = ""
            code, out = run("validate", "--desired", write_json(tmp, bad))
            self.assertEqual(code, 2, out)
            self.assertIn("INVALID cleanuparr.config.queueCleaner.cronExpression: required", out)


class DataOnlyTest(unittest.TestCase):
    def test_data_only_on_a_lone_cleanuparr_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            full = os.path.join(tmp, "full")
            os.mkdir(full)
            make_config_dir(full)
            alone = os.path.join(tmp, "alone")
            os.mkdir(alone)
            shutil.copy(os.path.join(full, "cleanuparr.db"), alone)
            desired = write_json(tmp, sample_desired())
            code, out = run("reconcile", "--desired", desired, "--config-dir", alone, "--data-only")
            self.assertEqual(code, 0, out)
            self.assertIn("--data-only", out)
            self.assertIn("15 changes applied", out)
            d = sample_desired()
            d["general"]["dryRun"] = False
            desired = write_json(tmp, d)
            code, out = run("reconcile", "--desired", desired, "--config-dir", alone, "--data-only")
            self.assertEqual(code, 0, out)
            self.assertIn("events.db dry-run purge is skipped", out)
            self.assertEqual(os.listdir(alone).count("events.db"), 0)


class SecretsTest(Base):
    def test_no_secret_reaches_the_log_even_without_redaction(self):
        with mock.patch.object(ac, "redact", lambda text: text):
            d = sample_desired()
            d["auth"] = {"username": "admin-test", "passwordHash": PASSWORD_HASH, "apiKey": API_KEY}
            outputs = [self.apply_ok(d), self.reconcile(d, "--mode", "plan")[1]]
            con = db(self.config)
            con.execute("UPDATE download_clients SET password = 'old', username = 'old-user'")
            con.execute("UPDATE arr_instances SET api_key = 'old-key'")
            con.commit()
            con.close()
            outputs.append(self.apply_ok(d))
            bad = sample_desired()
            bad["downloadClients"][0]["password"] = QBT_PASSWORD + "•" * 8
            outputs.append(self.reconcile(bad)[1])
        text = "\n".join(outputs)
        for secret in FAKE_SECRETS:
            self.assertNotIn(secret, text)
        self.assertIn("password: (secret changed)", text)
        self.assertIn("api_key: (secret changed)", text)

    PROVIDER_SECRETS = {
        "ntfy": {"serverUrl": "https://ntfy.example.test", "topics": ["t"], "authenticationType": "basicauth",
                 "username": "FAKE-NTFY-USER", "password": "FAKE-NTFY-PASS", "accessToken": "FAKE-NTFY-TOKEN"},
        "notifiarr": {"apiKey": "FAKE-NOTIFIARR-KEY", "channelId": "123"},
        "apprise": {"mode": "api", "url": "https://apprise.example.test/FAKE-APPRISE-PATH", "key": "FAKE-APPRISE-KEY"},
        "pushover": {"apiToken": "FAKE-PUSHOVER-TOKEN", "userKey": "FAKE-PUSHOVER-USER"},
        "telegram": {"botToken": "FAKE-TELEGRAM-TOKEN", "chatId": "-100"},
        "discord": {"webhookUrl": "https://discord.com/api/webhooks/1/FAKE-DISCORD-HOOK"},
        "gotify": {"serverUrl": "https://gotify.example.test", "applicationToken": "FAKE-GOTIFY-TOKEN"},
    }

    def test_every_provider_secret_stays_out_of_the_log(self):
        def secrets_of(block):
            return [v for v in block.values() if isinstance(v, str) and "FAKE-" in v]
        with mock.patch.object(ac, "redact", lambda text: text):
            d = sample_desired()
            d["notifications"] = [{"name": t, "type": t, t: copy.deepcopy(b)} for t, b in self.PROVIDER_SECRETS.items()]
            outputs = [self.apply_ok(d)]
            for note in d["notifications"]:
                block = note[note["type"]]
                for key, value in list(block.items()):
                    if isinstance(value, str) and "FAKE-" in value:
                        block[key] = value.replace("FAKE-", "FAKE-NEW-")
            outputs.append(self.apply_ok(d))
        text = "\n".join(outputs)
        leaked = [v for block in self.PROVIDER_SECRETS.values() for v in secrets_of(block) if v in text]
        leaked += [v.replace("FAKE-", "FAKE-NEW-") for block in self.PROVIDER_SECRETS.values()
                   for v in secrets_of(block) if v.replace("FAKE-", "FAKE-NEW-") in text]
        self.assertEqual(leaked, [])
        self.assertEqual(text.count("(secret changed)"), 11)

    def test_redaction_keeps_the_masks_and_runs_once(self):
        with mock.patch.object(ac, "_SECRETS", {"changed", "secret", "s3cr3t-value"}):
            self.assertEqual(ac.redact("api_key: (secret changed); was changed; s3cr3t-value"),
                             "api_key: (secret changed); was (secret); (secret)")


# -- Helm rendering -------------------------------------------------------------------------
@unittest.skipUnless(shutil.which("helm"), "helm is not installed")
class HelmTest(unittest.TestCase):
    BASE = {
        "gateway": {"restricted": {"enabled": True, "hostname": "media.example.test"}},
        "sonarr": {"apiKey": SONARR_KEY},
        "radarr": {"apiKey": RADARR_KEY},
        "qbittorrent": {"config": {"auth": {"username": QBT_USER, "password": QBT_PASSWORD}}},
        "cleanuparr": {"enabled": True, "config": {
            "enabled": True,
            "arr": {"sonarr": {"instances": [{"name": "sonarr", "fromChart": True}]},
                    "radarr": {"instances": [{"name": "radarr", "fromChart": True,
                                              "externalUrl": ""}]}},
            "downloadClients": [{"name": "qBittorrent", "fromChart": "qbittorrent"}]}},
    }

    def helm(self, values, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            json.dump(values, handle)
        try:
            return subprocess.run(["helm", "template", "kmm", str(CHART), "-f", handle.name, *args],
                                  capture_output=True, text=True)
        finally:
            os.unlink(handle.name)

    def desired(self, values):
        result = self.helm(values, "--show-only", "templates/cleanuparr/config.secret.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        encoded = [l for l in result.stdout.splitlines() if "desired-state.json:" in l][0].split(": ", 1)[1]
        import base64
        return json.loads(base64.b64decode(encoded))

    def test_from_chart_derivation(self):
        ds = self.desired(self.BASE)
        sonarr = ds["arr"]["sonarr"]["instances"][0]
        self.assertEqual((sonarr["url"], sonarr["externalUrl"], sonarr["apiKey"]),
                         ("http://kmm-k8s-mediamanager-sonarr:8989/sonarr", "https://media.example.test/sonarr",
                          SONARR_KEY))
        self.assertEqual(ds["arr"]["radarr"]["instances"][0]["externalUrl"], "")
        client = ds["downloadClients"][0]
        self.assertEqual((client["typeName"], client["host"], client["urlBase"], client["username"],
                          client["password"], client["externalUrl"]),
                         ("qbittorrent", "http://kmm-k8s-mediamanager-qbittorrent:8080", "", QBT_USER,
                          QBT_PASSWORD, "https://media.example.test"))
        self.assertNotIn("fromChart", json.dumps(ds))
        self.assertEqual((ds["schema"], ds["appVersion"], ds["mode"]), (1, ac.SUPPORTED_APP_VERSION, "apply"))
        for key in ("enabled", "resources", "externalBaseUrl"):
            self.assertNotIn(key, ds)
        errs = []
        normalized = ac.normalize(ac.DESIRED, ds, ac.VALUES, errs)
        ac.validate_semantics(normalized, errs, False)
        self.assertEqual(errs, [])

    def test_external_base_url_override(self):
        values = copy.deepcopy(self.BASE)
        values["cleanuparr"]["config"]["externalBaseUrl"] = "https://elsewhere.example.test/"
        ds = self.desired(values)
        self.assertEqual(ds["arr"]["sonarr"]["instances"][0]["externalUrl"], "https://elsewhere.example.test/sonarr")

    @staticmethod
    def with_values(*settings):
        values = copy.deepcopy(HelmTest.BASE)
        for keys, value in settings:
            node = values
            for key in keys[:-1]:
                node = node.setdefault(key, {})
            node[keys[-1]] = value
        return values

    def test_render_failures(self):
        lidarr = (("cleanuparr", "config", "arr"), {"lidarr": {"instances": [{"name": "l", "fromChart": True}]}})
        cases = [
            ([(("cleanuparr", "image", "tag"), "latest")], "supports Cleanuparr"),
            ([(("cleanuparr", "image", "tag"), "2.10.9")], "supports Cleanuparr"),
            ([(("cleanuparr", "config", "mode"), "dry")], "mode must be apply or plan"),
            ([(("cleanuparr", "config", "arr"), {"whisparr": {"instances": [{"name": "w", "fromChart": True}]}})],
             "only sonarr, radarr and lidarr"),
            ([(("cleanuparr", "config", "arr"), {"sonarr": {"instances": [{"name": "s", "fromChart": True,
                                                                           "apiKey": "x"}]}})],
             "fromChart takes it from sonarr.apiKey"),
            ([lidarr, (("lidarr", "enabled"), False)], "lidarr.enabled is false"),
            ([(("qbittorrent", "enabled"), False)], "qbittorrent.enabled is false"),
            ([(("qbittorrent", "config", "auth"), {"username": "", "password": ""})],
             "set qbittorrent.config.auth.username and .password first"),
            ([(("cleanuparr", "config", "downloadClients"), [{"name": "q", "fromChart": "transmission"}])],
             "is not a chart component"),
            ([(("cleanuparr", "config", "downloadClients"), [{"name": "q", "fromChart": "qbittorrent",
                                                              "host": "http://x"}])], "derives it from this chart"),
            ([(("cleanuparr", "config", "auth"), {"passwordHash": PASSWORD_HASH})], "without auth.username"),
            ([(("cleanuparr", "extraEnv"), [{"name": "DATABASE_PROVIDER", "value": "postgres"}])],
             "remove DATABASE_PROVIDER"),
            ([(("cleanuparr", "extraEnv"), [{"name": "DOTNET_DATABASE_PROVIDER", "value": "postgres"}])],
             "remove DATABASE_PROVIDER"),
            ([(("cleanuparr", "extraEnv"), [{"name": "DATABASE_PROVIDER",
                                             "valueFrom": {"secretKeyRef": {"name": "s", "key": "k"}}}])],
             "remove DATABASE_PROVIDER"),
            ([(("sonarr", "apiKey"), "CHANGEME-generate-a-random-32char-hex-key")], "set sonarr.apiKey first"),
        ]
        for settings, needle in cases:
            with self.subTest(needle=needle):
                result = self.helm(self.with_values(*settings))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(needle, result.stderr)

    def test_null_and_blank_values_take_the_defaults(self):
        ds = self.desired(self.with_values((("cleanuparr", "config", "mode"), None),
                                           (("cleanuparr", "config", "auth"), None),
                                           (("cleanuparr", "extraEnv"), [{"name": "DATABASE_PROVIDER", "value": ""}])))
        self.assertEqual((ds["mode"], ds["auth"]), ("apply", {}))
        result = self.helm(self.with_values((("cleanuparr", "config"), None)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("cleanuparr-config", result.stdout)

    def test_disabled_config_renders_nothing_new(self):
        values = copy.deepcopy(self.BASE)
        values["cleanuparr"]["config"]["enabled"] = False
        values["cleanuparr"]["image"] = {"tag": "latest"}
        out = self.helm(values).stdout
        self.assertNotIn("cleanuparr-config", out)
        self.assertNotIn("checksum/cleanuparr", out)

    def test_checksums_follow_content_not_chart_version(self):
        def checksums(chart, *args):
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
                json.dump(self.BASE, handle)
            try:
                out = subprocess.run(["helm", "template", "kmm", str(chart), "-f", handle.name, *args],
                                     capture_output=True, text=True, check=True).stdout
            finally:
                os.unlink(handle.name)
            return sorted(l.strip() for l in out.splitlines()
                          if l.strip().startswith(("checksum/init-config:", "checksum/cleanuparr-config")))
        base = checksums(CHART)
        self.assertEqual(len(base), 3, base)
        with tempfile.TemporaryDirectory() as tmp:
            bumped = Path(tmp, "chart")
            shutil.copytree(CHART, bumped)
            meta = (bumped / "Chart.yaml").read_text()
            (bumped / "Chart.yaml").write_text(re.sub(r"(?m)^version: .*$", "version: 99.0.0", meta, count=1))
            self.assertEqual(checksums(bumped), base)
        for setting, changed in (("qbittorrent.config.shareLimits.ratio=3", "checksum/init-config:"),
                                 ("cleanuparr.config.general.dryRun=false", "checksum/cleanuparr-config:")):
            with self.subTest(setting=setting):
                after = checksums(CHART, "--set", setting)
                self.assertEqual([l.split(" ")[0] for l in sorted(set(after) - set(base))], [changed])

    def test_configmap_carries_the_scripts_verbatim(self):
        result = self.helm(self.BASE, "--show-only", "templates/cleanuparr/config-scripts.configmap.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        yq = shutil.which("yq")
        if not yq:
            self.skipTest("yq is not installed")
        data = json.loads(subprocess.run([yq, "-o", "json", ".data"], input=result.stdout, capture_output=True,
                                         text=True, check=True).stdout)
        for name in ("migrate.sh", "apply_config.py"):
            self.assertEqual(data[name], (CHART / "files" / "cleanuparr" / name).read_text(), name)


if __name__ == "__main__":
    unittest.main()
