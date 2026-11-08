#!/usr/bin/env python3
# Writes the Helm-rendered Cleanuparr settings into its SQLite databases while the app is stopped.
# Stdlib only; runs in the pinned Cleanuparr image. See README "Cleanuparr settings as code".
import argparse
import datetime
import hmac
import ipaddress
import json
import math
import os
import re
import secrets
import sqlite3
import struct
import sys
import traceback
import uuid
from urllib.parse import quote, urlsplit

# WARNING: Helm reads this line to refuse other images; bump it only after the README "Upgrading Cleanuparr" review.
SUPPORTED_APP_VERSION = "2.10.8"
DESIRED_SCHEMA = 1

EXIT_OK, EXIT_ERROR, EXIT_INVALID, EXIT_GUARD, EXIT_NOT_CONVERGED = 0, 1, 2, 3, 4

DATA_DB, EVENTS_DB, USERS_DB = "cleanuparr.db", "events.db", "users.db"

EXPECTED_MIGRATIONS = {
    DATA_DB: (
        "20250621174558_InitialData",
        "20250628231105_AddReadarr",
        "20250702091059_AddWhisparr",
        "20250702192200_ChangeAppriseConfig",
        "20250704152940_AddAppriseTags",
        "20250801143446_AddKnownMalwareOption",
        "20250816183837_AddAdvancedLoggingSettings",
        "20250830230846_ReworkNotificationSystem",
        "20250912234118_AddNtfy",
        "20250915153159_AddBlacklistSyncSettings",
        "20250915181529_AddPerJobIgnoredDownloads",
        "20251012100711_AddQueueCleanerRules",
        "20251022212536_AddFailedImportPrivateSafeguardOption",
        "20251023074842_UpdateSearchDelay",
        "20251023184757_AddFailedImportTypeHandling",
        "20251211102657_AddPushoverProvider",
        "20251213201344_AddAppriseCliMode",
        "20251216204347_AddDeleteSourceFilesToCleanCategory",
        "20251216222056_RenameCleanCategoryToSeedingRule",
        "20251219224200_ChangeUnlinkedIgnoredRootDirType",
        "20251227170911_AddTelegram",
        "20251231171212_AddWhisparrV3",
        "20260112102214_AddDiscord",
        "20260112134008_AddGotify",
        "20260212204459_AddAppStatusSetting",
        "20260212222238_AddExternalUrl",
        "20260213155055_AddStrikeInactivityWindow",
        "20260216220150_AddSeedingRulePrivacyType",
        "20260223085409_AddAuthConfig",
        "20260306140714_AddProcessMissingContentId",
        "20260306144520_RemoveKnownMalwareOption",
        "20260310181205_RemoveProcessMissingId",
        "20260310181320_AddProcessMissingId",
        "20260324200753_AddSeeker",
        "20260325201158_AddPostReleaseGraceHours",
        "20260326195141_AddIsMonitoredToCfScoreEntry",
        "20260329184534_AddPerClientDownloadCleanerSettings",
        "20260408081126_AddSeedingRuleEnhancements",
        "20260415085810_AddSearchItemGrabbedNotification",
        "20260415192034_MoveSeekerFiltersToInstanceConfig",
        "20260420134250_AddLastUpgradedAtToCfScoreEntry",
        "20260504193343_AddQueueCleanerChangeCategory",
        "20260527073208_AddOrphanedFilesCleanup",
        "20260528100503_AddMinSeedersToSeedingRules",
        "20260528201320_AddDeleteIfAnyFileBlocked",
        "20260613142438_AddDeadTorrentConfig",
        "20260614130148_ConvertDatesToDateTimeOffset",
        "20260703173019_AddHistoryRetentionDays",
        "20260710110305_MoveSeekerStateToEvents",
        "20260713155427_WhisparrBlocklistTypeToText",
        "20260721100758_AddSlowRuleIgnoreAltSpeed",
        "20260723144949_AddConnectivityCheck",
        "20260724145908_AddMaxInactiveDaysToQBitSeedingRule",
        "20260804161642_AddSportarr",
        "20260820230125_AddLazyLibrarian",
        "20260822111016_AddHttpSendUserAgent",
        "20260824114948_AddSeekerIgnoreStruckDownloads",
        "20260903082920_AddSeedingRuleStopAction",
        "20260908230836_AddForceImport",
        "20260912212027_RemoveEncryptionKey",
    ),
    EVENTS_DB: (
        "20250614211246_InitialEvents",
        "20251023105637_AddManualEvents",
        "20251220204209_AddStrikes",
        "20260213090744_AddEventContextColumns",
        "20260213160156_AddOnStrikeDeleteBehavior",
        "20260214230732_AddDownloadItemStatuses",
        "20260319195316_AddIsDryRun",
        "20260324200744_AddSeeker",
        "20260405174732_AddSearchEventData",
        "20260614130440_ConvertDatesToDateTimeOffset",
        "20260706084236_EventStreamRework",
        "20260710110253_MoveSeekerStateToEvents",
        "20260903130325_NormalizeDownloadHashCasing",
        "20260908071938_AddEpisodeIdToSeekerCommandTracker",
    ),
    USERS_DB: (
        "20260215094545_Initial",
        "20260312090408_AddOidcSupport",
        "20260614115255_AddUserFeatureViews",
        "20260614130445_ConvertDatesToDateTimeOffset",
    ),
}

# Exact "column:TYPE" sets of every table this script reads or writes, as migrated by 2.10.8.
TABLE_COLUMNS = {
    DATA_DB: {
        "apprise_configs": (
            "id:TEXT key:TEXT notification_config_id:TEXT tags:TEXT url:TEXT mode:TEXT "
            "service_urls:TEXT"
        ),
        "arr_configs": "id:TEXT type:TEXT failed_import_max_strikes:INTEGER",
        "arr_instances": (
            "id:TEXT enabled:INTEGER arr_config_id:TEXT name:TEXT url:TEXT api_key:TEXT "
            "version:REAL external_url:TEXT"
        ),
        "blacklist_sync_configs": "id:TEXT enabled:INTEGER cron_expression:TEXT blacklist_path:TEXT",
        "blacklist_sync_history": "id:TEXT hash:TEXT download_client_id:TEXT",
        "content_blocker_configs": (
            "id:TEXT cron_expression:TEXT delete_if_any_file_blocked:INTEGER delete_private:INTEGER "
            "enabled:INTEGER ignore_private:INTEGER ignored_downloads:TEXT "
            "lidarr_blocklist_path:TEXT lidarr_blocklist_type:TEXT lidarr_enabled:INTEGER "
            "process_no_content_id:INTEGER radarr_blocklist_path:TEXT radarr_blocklist_type:TEXT "
            "radarr_enabled:INTEGER readarr_blocklist_path:TEXT readarr_blocklist_type:TEXT "
            "readarr_enabled:INTEGER sonarr_blocklist_path:TEXT sonarr_blocklist_type:TEXT "
            "sonarr_enabled:INTEGER use_advanced_scheduling:INTEGER whisparr_blocklist_path:TEXT "
            "whisparr_blocklist_type:TEXT whisparr_enabled:INTEGER sportarr_blocklist_path:TEXT "
            "sportarr_blocklist_type:TEXT sportarr_enabled:INTEGER "
            "lazy_librarian_blocklist_path:TEXT lazy_librarian_blocklist_type:TEXT "
            "lazy_librarian_enabled:INTEGER"
        ),
        "dead_torrent_configs": (
            "id:TEXT download_client_config_id:TEXT enabled:INTEGER target_category:TEXT "
            "use_tag:INTEGER max_strikes:INTEGER categories:TEXT"
        ),
        "deluge_seeding_rules": (
            "id:TEXT download_client_config_id:TEXT name:TEXT privacy_type:TEXT max_ratio:REAL "
            "min_seed_time:REAL max_seed_time:REAL delete_source_files:INTEGER categories:TEXT "
            "priority:INTEGER tracker_patterns:TEXT min_seeders:INTEGER action:TEXT"
        ),
        "discord_configs": (
            "id:TEXT notification_config_id:TEXT webhook_url:TEXT username:TEXT avatar_url:TEXT"
        ),
        "download_cleaner_configs": (
            "id:TEXT cron_expression:TEXT enabled:INTEGER ignored_downloads:TEXT "
            "use_advanced_scheduling:INTEGER"
        ),
        "download_clients": (
            "id:TEXT enabled:INTEGER name:TEXT type_name:TEXT type:TEXT host:TEXT username:TEXT "
            "password:TEXT url_base:TEXT external_url:TEXT download_directory_source:TEXT "
            "download_directory_target:TEXT"
        ),
        "general_configs": (
            "id:TEXT auth_disable_auth_for_local_addresses:INTEGER "
            "auth_trust_forwarded_headers:INTEGER auth_trusted_networks:TEXT "
            "connectivity_check_enabled:INTEGER connectivity_check_urls:TEXT "
            "display_support_banner:INTEGER dry_run:INTEGER history_retention_days:INTEGER "
            "http_certificate_validation:TEXT http_max_retries:INTEGER "
            "http_send_user_agent:INTEGER http_timeout:INTEGER ignored_downloads:TEXT "
            "log_archive_enabled:INTEGER log_archive_retained_count:INTEGER "
            "log_archive_time_limit_hours:INTEGER log_level:TEXT log_retained_file_count:INTEGER "
            "log_rolling_size_mb:INTEGER log_time_limit_hours:INTEGER "
            "status_check_enabled:INTEGER strike_inactivity_window_hours:INTEGER"
        ),
        "gotify_configs": (
            "id:TEXT notification_config_id:TEXT server_url:TEXT application_token:TEXT "
            "priority:INTEGER"
        ),
        "notifiarr_configs": "id:TEXT api_key:TEXT channel_id:TEXT notification_config_id:TEXT",
        "notification_configs": (
            "id:TEXT name:TEXT type:TEXT is_enabled:INTEGER on_failed_import_strike:INTEGER "
            "on_stalled_strike:INTEGER on_slow_strike:INTEGER on_queue_item_deleted:INTEGER "
            "on_download_cleaned:INTEGER on_category_changed:INTEGER created_at:TEXT "
            "updated_at:TEXT on_search_triggered:INTEGER on_search_item_grabbed:INTEGER "
            "on_download_stopped:INTEGER on_force_imported:INTEGER"
        ),
        "ntfy_configs": (
            "id:TEXT notification_config_id:TEXT server_url:TEXT topics:TEXT "
            "authentication_type:TEXT username:TEXT password:TEXT access_token:TEXT priority:TEXT "
            "tags:TEXT"
        ),
        "orphaned_files_configs": (
            "id:TEXT download_client_config_id:TEXT enabled:INTEGER scan_directories:TEXT "
            "orphaned_directory:TEXT exclude_patterns:TEXT min_file_age_hours:INTEGER "
            "purge_after_hours:INTEGER"
        ),
        "pushover_configs": (
            "id:TEXT notification_config_id:TEXT api_token:TEXT user_key:TEXT devices:TEXT "
            "priority:TEXT sound:TEXT retry:INTEGER expire:INTEGER tags:TEXT"
        ),
        "q_bit_seeding_rules": (
            "id:TEXT download_client_config_id:TEXT name:TEXT privacy_type:TEXT max_ratio:REAL "
            "min_seed_time:REAL max_seed_time:REAL delete_source_files:INTEGER categories:TEXT "
            "priority:INTEGER tags_all:TEXT tags_any:TEXT tracker_patterns:TEXT "
            "min_seeders:INTEGER max_inactive_days:REAL action:TEXT"
        ),
        "queue_cleaner_configs": (
            "id:TEXT cron_expression:TEXT downloading_metadata_max_strikes:INTEGER enabled:INTEGER "
            "failed_import_delete_private:INTEGER failed_import_ignore_private:INTEGER "
            "failed_import_max_strikes:INTEGER failed_import_pattern_mode:TEXT "
            "failed_import_patterns:TEXT failed_import_skip_if_not_found_in_client:INTEGER "
            "ignored_downloads:TEXT use_advanced_scheduling:INTEGER process_no_content_id:INTEGER "
            "failed_import_change_category:INTEGER failed_import_force_import:INTEGER "
            "failed_import_force_import_max_tries:INTEGER"
        ),
        "r_torrent_seeding_rules": (
            "id:TEXT download_client_config_id:TEXT name:TEXT privacy_type:TEXT max_ratio:REAL "
            "min_seed_time:REAL max_seed_time:REAL delete_source_files:INTEGER categories:TEXT "
            "priority:INTEGER tracker_patterns:TEXT action:TEXT"
        ),
        "seeker_configs": (
            "id:TEXT post_release_grace_hours:INTEGER proactive_search_enabled:INTEGER "
            "search_enabled:INTEGER search_interval:INTEGER selection_strategy:TEXT "
            "use_round_robin:INTEGER"
        ),
        "seeker_instance_configs": (
            "id:TEXT arr_instance_id:TEXT enabled:INTEGER skip_tags:TEXT last_processed_at:TEXT "
            "current_cycle_id:TEXT total_eligible_items:INTEGER active_download_limit:INTEGER "
            "min_cycle_time_days:INTEGER monitored_only:INTEGER use_cutoff:INTEGER "
            "use_custom_format_score:INTEGER ignore_struck_downloads:INTEGER"
        ),
        "slow_rules": (
            "id:TEXT reset_strikes_on_progress:INTEGER max_time_hours:REAL min_speed:TEXT "
            "ignore_above_size:TEXT queue_cleaner_config_id:TEXT name:TEXT enabled:INTEGER "
            "max_strikes:INTEGER privacy_type:TEXT min_completion_percentage:INTEGER "
            "max_completion_percentage:INTEGER delete_private_torrents_from_client:INTEGER "
            "change_category:INTEGER ignore_while_alt_speed_active:INTEGER"
        ),
        "stall_rules": (
            "id:TEXT reset_strikes_on_progress:INTEGER minimum_progress:TEXT "
            "queue_cleaner_config_id:TEXT name:TEXT enabled:INTEGER max_strikes:INTEGER "
            "privacy_type:TEXT min_completion_percentage:INTEGER max_completion_percentage:INTEGER "
            "delete_private_torrents_from_client:INTEGER change_category:INTEGER"
        ),
        "telegram_configs": (
            "id:TEXT notification_config_id:TEXT bot_token:TEXT chat_id:TEXT topic_id:TEXT "
            "send_silently:INTEGER"
        ),
        "transmission_seeding_rules": (
            "id:TEXT download_client_config_id:TEXT name:TEXT privacy_type:TEXT max_ratio:REAL "
            "min_seed_time:REAL max_seed_time:REAL delete_source_files:INTEGER categories:TEXT "
            "priority:INTEGER tags_all:TEXT tags_any:TEXT tracker_patterns:TEXT "
            "min_seeders:INTEGER action:TEXT"
        ),
        "u_torrent_seeding_rules": (
            "id:TEXT download_client_config_id:TEXT name:TEXT privacy_type:TEXT max_ratio:REAL "
            "min_seed_time:REAL max_seed_time:REAL delete_source_files:INTEGER categories:TEXT "
            "priority:INTEGER tracker_patterns:TEXT min_seeders:INTEGER action:TEXT"
        ),
        "unlinked_configs": (
            "id:TEXT categories:TEXT download_client_config_id:TEXT enabled:INTEGER "
            "ignored_root_dirs:TEXT target_category:TEXT use_tag:INTEGER"
        ),
    },
    EVENTS_DB: {
        "custom_format_score_entries": (
            "id:TEXT arr_instance_id:TEXT external_item_id:INTEGER episode_id:INTEGER "
            "item_type:TEXT title:TEXT file_id:INTEGER current_score:INTEGER cutoff_score:INTEGER "
            "quality_profile_name:TEXT is_monitored:INTEGER last_synced_at:TEXT "
            "last_upgraded_at:TEXT"
        ),
        "custom_format_score_history": (
            "id:TEXT arr_instance_id:TEXT external_item_id:INTEGER episode_id:INTEGER "
            "item_type:TEXT title:TEXT score:INTEGER cutoff_score:INTEGER recorded_at:TEXT"
        ),
        "download_items": (
            "id:TEXT download_id:TEXT title:TEXT is_marked_for_removal:INTEGER is_removed:INTEGER "
            "is_returning:INTEGER"
        ),
        "events": (
            "id:TEXT arr_instance_id:TEXT clean_reason:TEXT cleaned_category:TEXT completed_at:TEXT "
            "cycle_id:TEXT delete_reason:TEXT download_client_id:TEXT event_type:TEXT "
            "failed_import_reasons:TEXT grabbed_items:TEXT is_category_tag:INTEGER "
            "is_dry_run:INTEGER item_hash:TEXT item_title:TEXT job_run_id:TEXT message:TEXT "
            "new_category:TEXT old_category:TEXT remove_from_client:INTEGER search_reason:TEXT "
            "search_status:TEXT search_type:TEXT seed_ratio:REAL seeding_time_hours:REAL "
            "severity:TEXT strike_count:INTEGER strike_id:TEXT timestamp:TEXT tracking_id:TEXT"
        ),
        "manual_events": (
            "id:TEXT resolved_at:TEXT download_client_name:TEXT download_client_type:TEXT "
            "instance_type:TEXT instance_url:TEXT is_resolved:INTEGER job_run_id:TEXT "
            "message:TEXT severity:TEXT timestamp:TEXT is_dry_run:INTEGER item_hash:TEXT "
            "item_title:TEXT strike_count:INTEGER type:TEXT"
        ),
        "search_queue": (
            "id:TEXT arr_instance_id:TEXT item_id:INTEGER series_id:INTEGER search_type:TEXT "
            "title:TEXT created_at:TEXT"
        ),
        "seeker_command_trackers": (
            "id:TEXT arr_instance_id:TEXT command_id:INTEGER event_id:TEXT "
            "external_item_id:INTEGER item_title:TEXT season_number:INTEGER created_at:TEXT "
            "status:TEXT episode_id:INTEGER"
        ),
        "seeker_history": (
            "id:TEXT arr_instance_id:TEXT external_item_id:INTEGER item_type:TEXT "
            "season_number:INTEGER cycle_id:TEXT last_searched_at:TEXT item_title:TEXT "
            "search_count:INTEGER is_dry_run:INTEGER"
        ),
        "strikes": (
            "id:TEXT created_at:TEXT download_item_id:TEXT job_run_id:TEXT "
            "last_downloaded_bytes:INTEGER type:TEXT is_dry_run:INTEGER"
        ),
    },
    USERS_DB: {
        "users": (
            "id:TEXT username:TEXT password_hash:TEXT totp_secret:TEXT totp_enabled:INTEGER "
            "plex_account_id:TEXT plex_username:TEXT plex_email:TEXT plex_auth_token:TEXT "
            "api_key:TEXT setup_completed:INTEGER failed_login_attempts:INTEGER lockout_end:TEXT "
            "created_at:TEXT updated_at:TEXT oidc_authorized_subject:TEXT oidc_client_id:TEXT "
            "oidc_client_secret:TEXT oidc_enabled:INTEGER oidc_exclusive_mode:INTEGER "
            "oidc_issuer_url:TEXT oidc_provider_name:TEXT oidc_redirect_url:TEXT oidc_scopes:TEXT"
        ),
    },
}

# Newest migration timestamp in the 2.10.8 bundle, Postgres ids included; a release adding migrations differs.
IMAGE_NEWEST_MIGRATION = "20260912212035"
MIGRATION_ID_RE = re.compile(rb"20[0-9]{12}_[A-Z][A-Za-z0-9]+")

SINGLETON_TABLES = (
    "general_configs", "queue_cleaner_configs", "content_blocker_configs",
    "download_cleaner_configs", "blacklist_sync_configs", "seeker_configs",
)

# The UI's masked-secret marker: the API keeps the stored secret on receiving it (SensitiveDataHelper.cs:15-22).
SECRET_PLACEHOLDER = "\u2022" * 8

INT32_MAX = 2**31 - 1

# -- output and errors ----------------------------------------------------------------------------
_SECRETS = set()
# The script's own masks; redaction skips them so a secret such as "changed" cannot mangle them.
_MASK_RE = re.compile(r"(\(secret(?: set| changed| removed| empty)?\))")


def remember_secret(value):
    if isinstance(value, str) and len(value) >= 4:
        _SECRETS.add(value)


def redact(text):
    if not _SECRETS:
        return text
    # One left-to-right pass, longest first, so an inserted "(secret)" is never matched again.
    pattern = re.compile("|".join(re.escape(v) for v in sorted(_SECRETS, key=len, reverse=True)))
    parts = _MASK_RE.split(text)
    return "".join(part if index % 2 else pattern.sub("(secret)", part) for index, part in enumerate(parts))


def log(message):
    print(redact(f"cleanuparr-config: {message}"), flush=True)


def mask_url(text):
    """Hides the userinfo, query and fragment a URL may carry; the app keeps them (DataContext.cs:335)."""
    if not isinstance(text, str) or "://" not in text:
        return text
    scheme, rest = text.split("://", 1)
    rest, fragment_sep, fragment = rest.partition("#")
    rest, query_sep, query = rest.partition("?")
    if "@" in rest:
        rest = "(secret)@" + rest.rsplit("@", 1)[1]
    return (f"{scheme}://{rest}" + (query_sep + "(secret)" if query else query_sep)
            + (fragment_sep + "(secret)" if fragment else fragment_sep))


def _masked(value):
    if isinstance(value, (list, tuple)):
        return type(value)(_masked(item) for item in value)
    if isinstance(value, dict):
        return {key: _masked(item) for key, item in value.items()}
    return mask_url(value)


def masked_repr(value):
    return repr(_masked(value))


class Fail(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# -- value checks ---------------------------------------------------------------------------------
def http_url_error(value):
    message = "must be an absolute http(s) URL"
    if any(ch.isspace() for ch in value):
        return message
    try:
        parts = urlsplit(value)
        host = parts.hostname
        parts.port  # noqa: B018 - raises on an invalid port
    except ValueError:
        return message
    if parts.scheme.lower() not in ("http", "https") or not host:
        return message
    return None


def absolute_url_error(value):
    parts = urlsplit(value) if not any(ch.isspace() for ch in value) else None
    if parts is None or not parts.scheme or not (parts.netloc or parts.path):
        return "must be an absolute URL"
    return None


def ip_or_cidr_error(value):
    try:
        if "/" in value:
            address, prefix = value.split("/", 1)
            ip = ipaddress.ip_address(address)
            if not (prefix.isascii() and prefix.isdigit()) or int(prefix) > (32 if ip.version == 4 else 128):
                raise ValueError
        else:
            ipaddress.ip_address(value)
    except ValueError:
        return "must be an IP address or a CIDR range"
    return None


# ASCII only: .NET rejects the Unicode digits and spaces that Python's \d and \s accept.
BYTESIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(KB|MB|GB)\s*$", re.IGNORECASE | re.ASCII)
BYTESIZE_UNITS = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}


def bytesize_error(value):
    match = BYTESIZE_RE.match(value)
    if not match:
        return "must be a size such as 100MB (KB, MB or GB)"
    if float(match.group(1)) * BYTESIZE_UNITS[match.group(2).upper()] >= 2**63:
        return "is too large"
    return None


def int_text_error(bits, signed):
    def check(value):
        pattern = r"-?\d+" if signed else r"\d+"
        if not re.fullmatch(pattern, value, re.ASCII):
            return "must be an integer"
        number = int(value)
        low, high = (-(2 ** (bits - 1)), 2 ** (bits - 1) - 1) if signed else (0, 2**bits - 1)
        return None if low <= number <= high else "is out of range"
    return check


def discord_webhook_error(value):
    prefixes = ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")
    if not value.lower().startswith(prefixes):
        return "must be a Discord webhook URL (https://discord.com/api/webhooks/...)"
    return None


def pushover_device_error(value):
    if len(value) > 25 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return "must be at most 25 letters, digits, '_' or '-'"
    return None


def username_error(value):
    return None if 3 <= len(value) <= 50 else "must be 3 to 50 characters"


def bcrypt_error(value):
    if not re.fullmatch(r"\$2[abxy]\$\d\d\$[./A-Za-z0-9]{53}", value, re.ASCII):
        return "must be a bcrypt hash (htpasswd -nbBC 12 '' '<password>' | tr -d ':\\n')"
    return None


def api_key_error(value):
    return None if re.fullmatch(r"[0-9a-f]{64}", value) else "must be 64 lowercase hex characters"


# -- cron -----------------------------------------------------------------------------------------
# Fire-time floors per job (Constants.cs:7-9); the malware blocker has none.
CRON_MIN_GAP = {"queueCleaner": 30, "downloadCleaner": 30, "malwareBlocker": 0}
# The app refuses gaps over 6 h in local time, so a 6 h cron fails on DST nights (BackgroundJobManager.cs:228-257).
CRON_MAX_GAP = 5 * 3600
CRON_TOKEN_RE = re.compile(r"(\*|\d{1,2}|\d{1,2}-\d{1,2})(?:/(\d{1,2}))?", re.ASCII)


def _cron_field(text, name, high):
    if text == "*":
        return set(range(0, high + 1))
    parts = text.split(",")
    values = set()
    for part in parts:
        match = CRON_TOKEN_RE.fullmatch(part)
        if not match or (match.group(1) == "*" and len(parts) > 1):
            raise ValueError(f"unsupported {name} field {text!r}")
        base, step = match.group(1), match.group(2)
        if base == "*":
            first, last = 0, high
        elif "-" in base:
            first, last = (int(x) for x in base.split("-"))
        else:
            first = int(base)
            last = high if step else first
        if not 0 <= first <= last <= high:
            raise ValueError(f"{name} field {text!r} is out of range 0-{high}")
        increment = int(step) if step else 1
        if not 1 <= increment <= (59 if high == 59 else 23):
            raise ValueError(f"{name} field {text!r} has an invalid increment")
        values.update(range(first, last + 1, increment))
    return values


def cron_error(expression, job):
    """Accepts only daily-repeating Quartz crons whose every gap passes the app's startup check."""
    fields = expression.split(" ")
    if len(fields) not in (6, 7) or any(f == "" for f in fields):
        return "must be a Quartz cron: sec min hour day-of-month month day-of-week [year], single spaces"
    dom, month, dow = fields[3], fields[4], fields[5]
    if sorted((dom, dow)) != ["*", "?"]:
        return "day-of-month and day-of-week must be '?' and '*' (one each)"
    if month != "*" or (len(fields) == 7 and fields[6] != "*"):
        return "month and year must be '*'"
    try:
        seconds = _cron_field(fields[0], "second", 59)
        minutes = _cron_field(fields[1], "minute", 59)
        hours = _cron_field(fields[2], "hour", 23)
    except ValueError as exc:
        return str(exc)
    fires = sorted(h * 3600 + m * 60 + s for h in hours for m in minutes for s in seconds)
    gaps = [b - a for a, b in zip(fires, fires[1:])] + [fires[0] + 86400 - fires[-1]]
    if max(gaps) > CRON_MAX_GAP:
        return "must fire at least every 5 hours, all day (the app's 6 h limit minus a DST hour)"
    if min(gaps) < CRON_MIN_GAP[job]:
        return f"must not fire more often than every {CRON_MIN_GAP[job]} seconds"
    return None


def cron_check(job):
    return lambda value: cron_error(value, job)


# -- desired-state schema (values tree -> columns) ------------------------------------------------
BOOL, INT, REAL, REAL32, TEXT, ENUM, JSON_LIST, CSV_LIST = (
    "bool", "int", "real", "real32", "text", "enum", "json_list", "csv_list")
REQUIRED = object()


class Leaf:
    def __init__(self, kind, default, col=None, *, lo=None, hi=None, maxlen=None, choices=None,
                 secret=False, empty_as_null=False, nullable=False, check=None, item_check=None,
                 strip=False, nonempty=False):
        self.kind, self.default, self.col = kind, default, col
        self.lo, self.hi, self.maxlen, self.choices = lo, hi, maxlen, choices
        self.secret, self.empty_as_null, self.nullable = secret, empty_as_null, nullable
        self.check, self.item_check, self.strip = check, item_check, strip
        self.nonempty = nonempty


class Obj:
    def __init__(self, fields, table=None, nullable=False):
        self.fields, self.table, self.nullable = fields, table, nullable


class Lst:
    def __init__(self, item):
        self.item = item


PRIVACY = ("public", "private", "both")


def _rule_fields():
    return {
        "name": Leaf(TEXT, REQUIRED, "name", strip=True),
        "enabled": Leaf(BOOL, True, "enabled"),
        # The UI's rule dialogs cap it at 5000.
        "maxStrikes": Leaf(INT, 3, "max_strikes", lo=3, hi=5000),
        "privacyType": Leaf(ENUM, "public", "privacy_type", choices=PRIVACY),
        "minCompletionPercentage": Leaf(INT, 0, "min_completion_percentage", lo=0, hi=100),
        "maxCompletionPercentage": Leaf(INT, 100, "max_completion_percentage", lo=1, hi=100),
        "resetStrikesOnProgress": Leaf(BOOL, True, "reset_strikes_on_progress"),
        "deletePrivateTorrentsFromClient": Leaf(BOOL, False, "delete_private_torrents_from_client"),
        "changeCategory": Leaf(BOOL, False, "change_category"),
    }


STALL_RULE = Obj({
    **_rule_fields(),
    "minimumProgress": Leaf(TEXT, "", "minimum_progress", empty_as_null=True, check=bytesize_error,
                            strip=True),
}, table="stall_rules")

SLOW_RULE = Obj({
    **_rule_fields(),
    "maxTimeHours": Leaf(REAL, 0.0, "max_time_hours", lo=0),
    "minSpeed": Leaf(TEXT, "", "min_speed", check=bytesize_error, strip=True),
    "ignoreAboveSize": Leaf(TEXT, "", "ignore_above_size", empty_as_null=True, check=bytesize_error,
                            strip=True),
    "ignoreWhileAltSpeedActive": Leaf(BOOL, True, "ignore_while_alt_speed_active"),
}, table="slow_rules")


def _blocklist(prefix):
    return Obj({
        "enabled": Leaf(BOOL, False, f"{prefix}_enabled"),
        "blocklistType": Leaf(ENUM, "blacklist", f"{prefix}_blocklist_type",
                              choices=("blacklist", "whitelist")),
        "blocklistPath": Leaf(TEXT, "", f"{prefix}_blocklist_path", empty_as_null=True),
    })


# values key -> (arr_configs.type, default version, versions the UI offers; arr-settings.component.ts:18-26)
ARR_TYPES = {
    "sonarr": ("sonarr", 4.0, (4.0,)),
    "radarr": ("radarr", 6.0, (6.0,)),
    "lidarr": ("lidarr", 3.0, (3.0,)),
    "readarr": ("readarr", 0.4, (0.4,)),
    "whisparr": ("whisparr", 2.0, (2.0, 3.0)),
    "sportarr": ("sportarr", 3.0, (3.0,)),
    "lazyLibrarian": ("lazylibrarian", 1.0, (1.0,)),
}
# The Seeker only searches these types (Seeker.cs:233-240).
SEEKER_TYPES = ("sonarr", "radarr")

SEEKER_INSTANCE = Obj({
    "enabled": Leaf(BOOL, False, "enabled"),
    "skipTags": Leaf(JSON_LIST, [], "skip_tags"),
    "activeDownloadLimit": Leaf(INT, 3, "active_download_limit", lo=0, hi=100),
    "minCycleTimeDays": Leaf(INT, 7, "min_cycle_time_days", lo=1, hi=365),
    "monitoredOnly": Leaf(BOOL, True, "monitored_only"),
    "useCutoff": Leaf(BOOL, False, "use_cutoff"),
    "useCustomFormatScore": Leaf(BOOL, False, "use_custom_format_score"),
    "ignoreStruckDownloads": Leaf(BOOL, False, "ignore_struck_downloads"),
}, table="seeker_instance_configs")


def _version_check(allowed):
    def check(value):
        if any(abs(value - v) < 1e-6 for v in allowed):
            return None
        return "must be one of " + ", ".join(f"{v:g}" for v in allowed)
    return check


def _instance(key):
    _, default_version, allowed = ARR_TYPES[key]
    fields = {
        "name": Leaf(TEXT, REQUIRED, "name", strip=True),
        "enabled": Leaf(BOOL, True, "enabled"),
        "version": Leaf(REAL32, default_version, "version", check=_version_check(allowed)),
        "url": Leaf(TEXT, REQUIRED, "url", check=http_url_error),
        "apiKey": Leaf(TEXT, REQUIRED, "api_key", secret=True),
        "externalUrl": Leaf(TEXT, "", "external_url", empty_as_null=True, check=http_url_error),
    }
    if key in SEEKER_TYPES:
        fields["seeker"] = SEEKER_INSTANCE
    return Obj(fields, table="arr_instances")


CLIENT_TYPES = ("qbittorrent", "deluge", "transmission", "utorrent", "rtorrent")
SEEDING_TABLES = {
    "qbittorrent": "q_bit_seeding_rules",
    "deluge": "deluge_seeding_rules",
    "transmission": "transmission_seeding_rules",
    "utorrent": "u_torrent_seeding_rules",
    "rtorrent": "r_torrent_seeding_rules",
}
# Seeding-rule fields only some client tables have (ISeedingRule.cs and its implementations).
SEEDING_FIELD_CLIENTS = {
    "minSeeders": ("qbittorrent", "deluge", "transmission", "utorrent"),
    "tagsAll": ("qbittorrent", "transmission"),
    "tagsAny": ("qbittorrent", "transmission"),
    "maxInactiveDays": ("qbittorrent",),
}

SEEDING_RULE = Obj({
    "name": Leaf(TEXT, REQUIRED, "name", strip=True),
    "privacyType": Leaf(ENUM, "public", "privacy_type", choices=PRIVACY),
    "maxRatio": Leaf(REAL, -1.0, "max_ratio"),
    "minSeedTime": Leaf(REAL, 0.0, "min_seed_time", lo=0),
    "maxSeedTime": Leaf(REAL, -1.0, "max_seed_time"),
    # The API's and UI's default (SeedingRuleRequest.cs:72); only the entity initializer says false.
    "deleteSourceFiles": Leaf(BOOL, True, "delete_source_files"),
    "categories": Leaf(JSON_LIST, [], "categories", strip=True),
    "trackerPatterns": Leaf(JSON_LIST, [], "tracker_patterns", strip=True),
    "minSeeders": Leaf(INT, 0, "min_seeders", lo=0, hi=INT32_MAX),
    "tagsAll": Leaf(JSON_LIST, [], "tags_all", strip=True),
    "tagsAny": Leaf(JSON_LIST, [], "tags_any", strip=True),
    "maxInactiveDays": Leaf(REAL, -1.0, "max_inactive_days"),
    "action": Leaf(ENUM, "delete", "action", choices=("delete", "stop")),
})

UNLINKED = Obj({
    "enabled": Leaf(BOOL, False, "enabled"),
    "targetCategory": Leaf(TEXT, "cleanuparr-unlinked", "target_category"),
    "useTag": Leaf(BOOL, False, "use_tag"),
    "categories": Leaf(JSON_LIST, [], "categories"),
    "ignoredRootDirs": Leaf(JSON_LIST, [], "ignored_root_dirs"),
}, table="unlinked_configs", nullable=True)

DEAD_TORRENTS = Obj({
    "enabled": Leaf(BOOL, False, "enabled"),
    "targetCategory": Leaf(TEXT, "cleanuparr-dead", "target_category"),
    "useTag": Leaf(BOOL, False, "use_tag"),
    "maxStrikes": Leaf(INT, 0, "max_strikes", lo=0, hi=65535),
    "categories": Leaf(JSON_LIST, [], "categories"),
}, table="dead_torrent_configs", nullable=True)

ORPHANED_FILES = Obj({
    "enabled": Leaf(BOOL, False, "enabled"),
    "scanDirectories": Leaf(JSON_LIST, [], "scan_directories"),
    "orphanedDirectory": Leaf(TEXT, "", "orphaned_directory"),
    "excludePatterns": Leaf(JSON_LIST, [], "exclude_patterns"),
    "minFileAgeHours": Leaf(INT, 24, "min_file_age_hours", lo=0, hi=INT32_MAX),
    "purgeAfterHours": Leaf(INT, None, "purge_after_hours", lo=1, hi=INT32_MAX, nullable=True),
}, table="orphaned_files_configs", nullable=True)

DOWNLOAD_CLIENT = Obj({
    "name": Leaf(TEXT, REQUIRED, "name", strip=True),
    "enabled": Leaf(BOOL, True, "enabled"),
    "typeName": Leaf(ENUM, REQUIRED, "type_name", choices=CLIENT_TYPES),
    "host": Leaf(TEXT, REQUIRED, "host", check=http_url_error),
    "urlBase": Leaf(TEXT, "", "url_base"),
    "username": Leaf(TEXT, "", "username", secret=True, empty_as_null=True),
    "password": Leaf(TEXT, "", "password", secret=True, empty_as_null=True),
    "externalUrl": Leaf(TEXT, "", "external_url", empty_as_null=True, check=http_url_error),
    "downloadDirectorySource": Leaf(TEXT, "", "download_directory_source", empty_as_null=True),
    "downloadDirectoryTarget": Leaf(TEXT, "", "download_directory_target", empty_as_null=True),
    "seedingRules": Lst(SEEDING_RULE),
    "unlinked": UNLINKED,
    "deadTorrents": DEAD_TORRENTS,
    "orphanedFiles": ORPHANED_FILES,
}, table="download_clients")

# The UI always creates torrent clients (download-clients.component.ts:189,247).
FIXED_COLUMNS = {"download_clients": {"type": (Leaf(ENUM, "torrent", "type"), "torrent")}}

PROVIDERS = {
    "notifiarr": Obj({
        "apiKey": Leaf(TEXT, REQUIRED, "api_key", secret=True, maxlen=255),
        "channelId": Leaf(TEXT, REQUIRED, "channel_id", maxlen=50, check=int_text_error(64, False)),
    }, table="notifiarr_configs", nullable=True),
    "apprise": Obj({
        "mode": Leaf(ENUM, "api", "mode", choices=("api", "cli")),
        "url": Leaf(TEXT, "", "url", secret=True, maxlen=500),
        "key": Leaf(TEXT, "", "key", secret=True, maxlen=255),
        "tags": Leaf(TEXT, "", "tags", maxlen=255, empty_as_null=True),
        "serviceUrls": Leaf(TEXT, "", "service_urls", secret=True, maxlen=4000, empty_as_null=True),
    }, table="apprise_configs", nullable=True),
    "ntfy": Obj({
        "serverUrl": Leaf(TEXT, REQUIRED, "server_url", maxlen=500, check=http_url_error),
        "topics": Leaf(JSON_LIST, [], "topics"),
        "authenticationType": Leaf(ENUM, "none", "authentication_type",
                                   choices=("none", "basicauth", "accesstoken")),
        "username": Leaf(TEXT, "", "username", secret=True, maxlen=255, empty_as_null=True),
        "password": Leaf(TEXT, "", "password", secret=True, maxlen=255, empty_as_null=True),
        "accessToken": Leaf(TEXT, "", "access_token", secret=True, maxlen=500, empty_as_null=True),
        "priority": Leaf(ENUM, "default", "priority", choices=("min", "low", "default", "high", "max")),
        "tags": Leaf(JSON_LIST, [], "tags"),
    }, table="ntfy_configs", nullable=True),
    "pushover": Obj({
        "apiToken": Leaf(TEXT, REQUIRED, "api_token", secret=True, maxlen=50),
        "userKey": Leaf(TEXT, REQUIRED, "user_key", secret=True, maxlen=50),
        "devices": Leaf(CSV_LIST, [], "devices", item_check=pushover_device_error),
        "priority": Leaf(ENUM, "normal", "priority",
                         choices=("lowest", "low", "normal", "high", "emergency")),
        "sound": Leaf(TEXT, "", "sound", maxlen=50, empty_as_null=True),
        "retry": Leaf(INT, None, "retry", nullable=True, lo=0, hi=INT32_MAX),
        "expire": Leaf(INT, None, "expire", nullable=True, lo=0, hi=INT32_MAX),
        "tags": Leaf(CSV_LIST, [], "tags"),
    }, table="pushover_configs", nullable=True),
    "telegram": Obj({
        "botToken": Leaf(TEXT, REQUIRED, "bot_token", secret=True, maxlen=255),
        "chatId": Leaf(TEXT, REQUIRED, "chat_id", maxlen=100, check=int_text_error(64, True)),
        "topicId": Leaf(TEXT, "", "topic_id", maxlen=100, empty_as_null=True,
                        check=int_text_error(32, True)),
        "sendSilently": Leaf(BOOL, False, "send_silently"),
    }, table="telegram_configs", nullable=True),
    "discord": Obj({
        "webhookUrl": Leaf(TEXT, REQUIRED, "webhook_url", secret=True, maxlen=500,
                           check=discord_webhook_error),
        "username": Leaf(TEXT, "", "username", maxlen=80),
        "avatarUrl": Leaf(TEXT, "", "avatar_url", maxlen=500, check=absolute_url_error),
    }, table="discord_configs", nullable=True),
    "gotify": Obj({
        "serverUrl": Leaf(TEXT, REQUIRED, "server_url", maxlen=500, check=http_url_error),
        "applicationToken": Leaf(TEXT, REQUIRED, "application_token", secret=True, maxlen=200),
        "priority": Leaf(INT, 5, "priority", lo=0, hi=10),
    }, table="gotify_configs", nullable=True),
}

NOTIFICATION = Obj({
    "name": Leaf(TEXT, REQUIRED, "name", strip=True, maxlen=100),
    "type": Leaf(ENUM, REQUIRED, "type", choices=tuple(PROVIDERS)),
    "enabled": Leaf(BOOL, True, "is_enabled"),
    "events": Obj({
        "onFailedImportStrike": Leaf(BOOL, False, "on_failed_import_strike"),
        "onStalledStrike": Leaf(BOOL, False, "on_stalled_strike"),
        "onSlowStrike": Leaf(BOOL, False, "on_slow_strike"),
        "onQueueItemDeleted": Leaf(BOOL, False, "on_queue_item_deleted"),
        "onDownloadCleaned": Leaf(BOOL, False, "on_download_cleaned"),
        "onCategoryChanged": Leaf(BOOL, False, "on_category_changed"),
        "onSearchTriggered": Leaf(BOOL, False, "on_search_triggered"),
        "onSearchItemGrabbed": Leaf(BOOL, False, "on_search_item_grabbed"),
        "onDownloadStopped": Leaf(BOOL, False, "on_download_stopped"),
        "onForceImported": Leaf(BOOL, False, "on_force_imported"),
    }),
    **PROVIDERS,
}, table="notification_configs")

DESIRED = Obj({
    "schema": Leaf(INT, REQUIRED),
    "appVersion": Leaf(TEXT, REQUIRED),
    "mode": Leaf(ENUM, "apply", choices=("apply", "plan")),
    "auth": Obj({
        "username": Leaf(TEXT, "", check=username_error),
        "passwordHash": Leaf(TEXT, "", secret=True, check=bcrypt_error),
        "apiKey": Leaf(TEXT, "", secret=True, check=api_key_error),
    }),
    "general": Obj({
        "dryRun": Leaf(BOOL, True, "dry_run"),
        "statusCheckEnabled": Leaf(BOOL, False, "status_check_enabled"),
        "displaySupportBanner": Leaf(BOOL, True, "display_support_banner"),
        "historyRetentionDays": Leaf(INT, 365, "history_retention_days", lo=1, hi=3650),
        "strikeInactivityWindowHours": Leaf(INT, 24, "strike_inactivity_window_hours", lo=1, hi=168),
        "ignoredDownloads": Leaf(JSON_LIST, [], "ignored_downloads"),
        "connectivityCheckEnabled": Leaf(BOOL, False, "connectivity_check_enabled"),
        "connectivityCheckUrls": Leaf(JSON_LIST, [], "connectivity_check_urls",
                                      item_check=http_url_error),
        "http": Obj({
            "maxRetries": Leaf(INT, 0, "http_max_retries", lo=0, hi=65535),
            "timeout": Leaf(INT, 100, "http_timeout", lo=1, hi=65535),
            "certificateValidation": Leaf(ENUM, "enabled", "http_certificate_validation",
                                          choices=("enabled", "disabledforlocaladdresses", "disabled")),
            "sendUserAgent": Leaf(BOOL, False, "http_send_user_agent"),
        }),
        "log": Obj({
            "level": Leaf(ENUM, "information", "log_level",
                          choices=("verbose", "debug", "information", "warning", "error", "fatal")),
            "rollingSizeMB": Leaf(INT, 10, "log_rolling_size_mb", lo=0, hi=100),
            "retainedFileCount": Leaf(INT, 5, "log_retained_file_count", lo=0, hi=50),
            "timeLimitHours": Leaf(INT, 24, "log_time_limit_hours", lo=0, hi=1440),
            "archiveEnabled": Leaf(BOOL, True, "log_archive_enabled"),
            "archiveRetainedCount": Leaf(INT, 60, "log_archive_retained_count", lo=0, hi=100),
            "archiveTimeLimitHours": Leaf(INT, 720, "log_archive_time_limit_hours", lo=0, hi=1440),
        }),
        "auth": Obj({
            "disableAuthForLocalAddresses": Leaf(BOOL, False, "auth_disable_auth_for_local_addresses"),
            "trustForwardedHeaders": Leaf(BOOL, False, "auth_trust_forwarded_headers"),
            "trustedNetworks": Leaf(CSV_LIST, [], "auth_trusted_networks", item_check=ip_or_cidr_error),
        }),
    }, table="general_configs"),
    "queueCleaner": Obj({
        "enabled": Leaf(BOOL, False, "enabled"),
        "cronExpression": Leaf(TEXT, "0 0/5 * * * ?", "cron_expression", strip=True,
                               check=cron_check("queueCleaner"), nonempty=True),
        "useAdvancedScheduling": Leaf(BOOL, False, "use_advanced_scheduling"),
        "ignoredDownloads": Leaf(JSON_LIST, [], "ignored_downloads"),
        "processNoContentId": Leaf(BOOL, False, "process_no_content_id"),
        "downloadingMetadataMaxStrikes": Leaf(INT, 0, "downloading_metadata_max_strikes", lo=0, hi=65535),
        "failedImport": Obj({
            "maxStrikes": Leaf(INT, 0, "failed_import_max_strikes", lo=0, hi=65535),
            "ignorePrivate": Leaf(BOOL, False, "failed_import_ignore_private"),
            "deletePrivate": Leaf(BOOL, False, "failed_import_delete_private"),
            "skipIfNotFoundInClient": Leaf(BOOL, True, "failed_import_skip_if_not_found_in_client"),
            "patternMode": Leaf(ENUM, "include", "failed_import_pattern_mode",
                                choices=("include", "exclude")),
            "patterns": Leaf(JSON_LIST, [], "failed_import_patterns"),
            "changeCategory": Leaf(BOOL, False, "failed_import_change_category"),
            "forceImport": Leaf(BOOL, False, "failed_import_force_import"),
            "forceImportMaxTries": Leaf(INT, 3, "failed_import_force_import_max_tries", lo=0, hi=65535),
        }),
        "stallRules": Lst(STALL_RULE),
        "slowRules": Lst(SLOW_RULE),
    }, table="queue_cleaner_configs"),
    "malwareBlocker": Obj({
        "enabled": Leaf(BOOL, False, "enabled"),
        "cronExpression": Leaf(TEXT, "0/5 * * * * ?", "cron_expression", strip=True,
                               check=cron_check("malwareBlocker"), nonempty=True),
        "useAdvancedScheduling": Leaf(BOOL, False, "use_advanced_scheduling"),
        "ignorePrivate": Leaf(BOOL, False, "ignore_private"),
        "deletePrivate": Leaf(BOOL, False, "delete_private"),
        "processNoContentId": Leaf(BOOL, False, "process_no_content_id"),
        "deleteIfAnyFileBlocked": Leaf(BOOL, False, "delete_if_any_file_blocked"),
        "ignoredDownloads": Leaf(JSON_LIST, [], "ignored_downloads"),
        "sonarr": _blocklist("sonarr"),
        "radarr": _blocklist("radarr"),
        "lidarr": _blocklist("lidarr"),
        "readarr": _blocklist("readarr"),
        "whisparr": _blocklist("whisparr"),
        "sportarr": _blocklist("sportarr"),
        "lazyLibrarian": _blocklist("lazy_librarian"),
    }, table="content_blocker_configs"),
    "downloadCleaner": Obj({
        "enabled": Leaf(BOOL, False, "enabled"),
        "cronExpression": Leaf(TEXT, "0 0 * * * ?", "cron_expression", strip=True,
                               check=cron_check("downloadCleaner"), nonempty=True),
        "useAdvancedScheduling": Leaf(BOOL, False, "use_advanced_scheduling"),
        "ignoredDownloads": Leaf(JSON_LIST, [], "ignored_downloads"),
    }, table="download_cleaner_configs"),
    "blacklistSync": Obj({
        "enabled": Leaf(BOOL, False, "enabled"),
        "blacklistPath": Leaf(TEXT, "", "blacklist_path", empty_as_null=True),
    }, table="blacklist_sync_configs"),
    "seeker": Obj({
        "searchEnabled": Leaf(BOOL, True, "search_enabled"),
        "searchInterval": Leaf(INT, 10, "search_interval", lo=2, hi=360),
        "proactiveSearchEnabled": Leaf(BOOL, False, "proactive_search_enabled"),
        "selectionStrategy": Leaf(ENUM, "balancedweighted", "selection_strategy", choices=(
            "balancedweighted", "oldestsearchfirst", "oldestsearchweighted", "newestfirst",
            "newestweighted", "random")),
        "useRoundRobin": Leaf(BOOL, True, "use_round_robin"),
        "postReleaseGraceHours": Leaf(INT, 6, "post_release_grace_hours", lo=0, hi=72),
    }, table="seeker_configs"),
    "arr": Obj({
        key: Obj({
            # -1 follows queueCleaner.failedImport.maxStrikes, 0 turns failed-import strikes off
            # for this type (ArrClient.cs:146-152).
            "failedImportMaxStrikes": Leaf(INT, -1, "failed_import_max_strikes", lo=-1, hi=32767),
            "instances": Lst(_instance(key)),
        }, table="arr_configs")
        for key in ARR_TYPES
    }),
    "downloadClients": Lst(DOWNLOAD_CLIENT),
    "notifications": Lst(NOTIFICATION),
})

# The app's choices (SeekerConfig.cs:66) without 360, which hits the DST gap above.
SEEKER_INTERVALS = (2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60, 120, 180, 240)


# -- normalization: defaults, types, unknown keys -------------------------------------------------
def _norm_leaf(leaf, value, path, errs):
    if value is None:
        if leaf.default is REQUIRED:
            errs.append(f"{path}: required")
            return None
        return list(leaf.default) if isinstance(leaf.default, list) else leaf.default
    shown = "(secret)" if leaf.secret else masked_repr(value)[:80]
    kind = leaf.kind
    if kind == BOOL:
        if not isinstance(value, bool):
            errs.append(f"{path}: must be true or false, got {shown}")
            return leaf.default
        return value
    if kind == INT:
        if isinstance(value, bool) or not (
                isinstance(value, int) or (isinstance(value, float) and value.is_integer())):
            errs.append(f"{path}: must be an integer, got {shown}")
            return None
        value = int(value)
    elif kind in (REAL, REAL32):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errs.append(f"{path}: must be a number, got {shown}")
            return None
        value = float(value)
    elif kind in (TEXT, ENUM):
        if not isinstance(value, str):
            errs.append(f"{path}: must be a string, got {shown}")
            return None
        if leaf.strip:
            value = value.strip()
        if kind == ENUM:
            value = value.strip().lower()
            if value not in leaf.choices:
                errs.append(f"{path}: {shown} is not one of {', '.join(leaf.choices)}")
            return value
        if leaf.secret:
            remember_secret(value)
            if SECRET_PLACEHOLDER in value:
                errs.append(f"{path}: contains the UI's masked-secret placeholder")
        if (leaf.default is REQUIRED or leaf.nonempty) and value == "":
            errs.append(f"{path}: required")
        if leaf.maxlen is not None and len(value) > leaf.maxlen:
            errs.append(f"{path}: longer than {leaf.maxlen} characters")
    elif kind in (JSON_LIST, CSV_LIST):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errs.append(f"{path}: must be a list of strings")
            return []
        items = [item.strip() for item in value] if leaf.strip else list(value)
        for index, item in enumerate(items):
            if item.strip() == "":
                errs.append(f"{path}[{index}]: must not be blank")
            elif kind == CSV_LIST and "," in item:
                errs.append(f"{path}[{index}]: must not contain ','")
            elif leaf.item_check and (message := leaf.item_check(item)):
                errs.append(f"{path}[{index}]: {message}")
        return items
    if kind in (INT, REAL, REAL32):
        if leaf.lo is not None and value < leaf.lo:
            errs.append(f"{path}: {shown} is below the minimum {leaf.lo}")
        if leaf.hi is not None and value > leaf.hi:
            errs.append(f"{path}: {shown} is above the maximum {leaf.hi}")
    if leaf.check and value != "" and (message := leaf.check(value)):
        errs.append(f"{path}: {message}")
    return value


def normalize(spec, value, path, errs):
    if isinstance(spec, Leaf):
        return _norm_leaf(spec, value, path, errs)
    if isinstance(spec, Lst):
        if value is None:
            return []
        if not isinstance(value, list):
            errs.append(f"{path}: must be a list")
            return []
        return [normalize(spec.item, item, f"{path}[{i}]", errs) for i, item in enumerate(value)]
    if value is None:
        if spec.nullable:
            return None
        value = {}
    if not isinstance(value, dict):
        errs.append(f"{path}: must be a mapping")
        value = {}
    for key in sorted(set(value) - set(spec.fields)):
        errs.append(f"{path}.{key}: unknown key")
    return {key: normalize(field, value.get(key), f"{path}.{key}", errs)
            for key, field in spec.fields.items()}


# -- semantic validation (ports of the app's Validate() methods) ----------------------------------
VALUES = "cleanuparr.config"


def _dupes(names):
    seen, dupes = set(), set()
    for name in names:
        key = (name or "").lower()
        (dupes if key in seen else seen).add(key)
    return dupes


def _path_ok(path, check_paths, kind):
    if not check_paths:
        return True
    return os.path.isfile(path) if kind == "file" else os.path.isdir(path)


def _norm_dir(path):
    return "/".join(path.replace("\\", "/").split("/")).rstrip("/")


def _overlap(a, b):
    a_l, b_l = a.lower(), b.lower()
    return a_l == b_l or a_l.startswith(b_l + "/") or b_l.startswith(a_l + "/")


def validate_semantics(ds, errs, check_paths, unsupported=None):
    unsupported = unsupported or {}
    g = ds["general"]
    if g["connectivityCheckEnabled"] and not g["connectivityCheckUrls"]:
        errs.append(f"{VALUES}.general.connectivityCheckUrls: needs at least one URL when "
                    "connectivityCheckEnabled is true")
    lg = g["log"]
    if lg["archiveEnabled"] and lg["archiveRetainedCount"] == 0 and lg["archiveTimeLimitHours"] == 0:
        errs.append(f"{VALUES}.general.log: archiveEnabled needs archiveRetainedCount or "
                    "archiveTimeLimitHours above 0")

    qc = ds["queueCleaner"]
    p = f"{VALUES}.queueCleaner"
    if qc["downloadingMetadataMaxStrikes"] in (1, 2):
        errs.append(f"{p}.downloadingMetadataMaxStrikes: must be 0 or at least 3")
    fi = qc["failedImport"]
    if fi["maxStrikes"] in (1, 2):
        errs.append(f"{p}.failedImport.maxStrikes: must be 0 or at least 3")
    if (fi["maxStrikes"] or 0) >= 3 and fi["patternMode"] == "include" and not fi["patterns"]:
        errs.append(f"{p}.failedImport.patterns: include mode needs at least one pattern")
    if fi["changeCategory"] and fi["deletePrivate"]:
        errs.append(f"{p}.failedImport: changeCategory and deletePrivate cannot both be true")
    if fi["forceImport"] and not 1 <= (fi["forceImportMaxTries"] or 0) <= 5000:
        errs.append(f"{p}.failedImport.forceImportMaxTries: must be 1..5000 when forceImport is true")
    for kind in ("stallRules", "slowRules"):
        rules = qc[kind]
        for name in sorted(_dupes(r["name"] for r in rules)):
            errs.append(f"{p}.{kind}: rule name {name!r} is used twice (names are case-insensitive)")
        for i, r in enumerate(rules):
            rp = f"{p}.{kind}[{i}]"
            lo, hi = r["minCompletionPercentage"], r["maxCompletionPercentage"]
            if lo is not None and hi is not None and hi < lo:
                errs.append(f"{rp}: maxCompletionPercentage is below minCompletionPercentage")
            if r["changeCategory"] and r["deletePrivateTorrentsFromClient"]:
                errs.append(f"{rp}: changeCategory and deletePrivateTorrentsFromClient cannot both be true")
            if kind == "slowRules" and not r["minSpeed"] and not (r["maxTimeHours"] or 0) > 0:
                errs.append(f"{rp}: set minSpeed or a maxTimeHours above 0")
        # Enabled rules of one kind must not share a completion range per privacy type
        # (RuleIntervalValidator.cs:60-120); 'both' counts as public and private.
        spans = []
        for r in rules:
            if r["enabled"] and r["minCompletionPercentage"] is not None and r["maxCompletionPercentage"] is not None:
                for privacy in (("public", "private") if r["privacyType"] == "both" else (r["privacyType"],)):
                    spans.append((privacy, r["minCompletionPercentage"], r["maxCompletionPercentage"], r["name"]))
        for i, (pa, sa, ea, na) in enumerate(spans):
            for pb, sb, eb, nb in spans[i + 1:]:
                if pa == pb and na != nb and sa < eb and sb < ea and min(ea, eb) > max(sa, sb):
                    errs.append(f"{p}.{kind}: enabled rules {na!r} and {nb!r} overlap for {pa} "
                                f"torrents ({max(sa, sb)}-{min(ea, eb)}%)")

    mb = ds["malwareBlocker"]
    arr_lists = [k for k in ("sonarr", "radarr", "lidarr", "readarr", "whisparr", "sportarr", "lazyLibrarian")]
    if mb["enabled"] and not any(mb[k]["enabled"] for k in arr_lists):
        errs.append(f"{VALUES}.malwareBlocker: enabled needs at least one enabled blocklist")
    if mb["enabled"]:
        for k in arr_lists:
            bl = mb[k]
            bp = f"{VALUES}.malwareBlocker.{k}.blocklistPath"
            if not bl["enabled"]:
                continue
            if not (bl["blocklistPath"] or "").strip():
                errs.append(f"{bp}: required when the {k} blocklist is enabled")
            elif http_url_error(bl["blocklistPath"]) and not _path_ok(bl["blocklistPath"], check_paths, "file"):
                errs.append(f"{bp}: must be an http(s) URL or an existing file")

    bs = ds["blacklistSync"]
    if bs["enabled"]:
        bp = f"{VALUES}.blacklistSync.blacklistPath"
        if not (bs["blacklistPath"] or "").strip():
            errs.append(f"{bp}: required when blacklistSync is enabled")
        elif http_url_error(bs["blacklistPath"]) and not _path_ok(bs["blacklistPath"], check_paths, "file"):
            errs.append(f"{bp}: must be an http(s) URL or an existing file")

    sk = ds["seeker"]
    if sk["searchInterval"] is not None and sk["searchInterval"] not in SEEKER_INTERVALS:
        errs.append(f"{VALUES}.seeker.searchInterval: must be one of "
                    + ", ".join(str(v) for v in SEEKER_INTERVALS))
    if sk["proactiveSearchEnabled"]:
        if not any(i["seeker"]["enabled"] for t in SEEKER_TYPES for i in ds["arr"][t]["instances"]):
            errs.append(f"{VALUES}.seeker.proactiveSearchEnabled: needs a sonarr or radarr instance "
                        "with seeker.enabled true")

    for key in ARR_TYPES:
        for name in sorted(_dupes(i["name"] for i in ds["arr"][key]["instances"])):
            errs.append(f"{VALUES}.arr.{key}.instances: name {name!r} is used twice")
    fims = ds["arr"]
    for key in ARR_TYPES:
        if fims[key]["failedImportMaxStrikes"] in (1, 2):
            errs.append(f"{VALUES}.arr.{key}.failedImportMaxStrikes: must be -1, 0 or at least 3")

    clients = ds["downloadClients"]
    for name in sorted(_dupes(c["name"] for c in clients)):
        errs.append(f"{VALUES}.downloadClients: name {name!r} is used twice")
    for ci, c in enumerate(clients):
        cp = f"{VALUES}.downloadClients[{ci}]"
        if bool(c["downloadDirectorySource"].strip()) != bool(c["downloadDirectoryTarget"].strip()):
            errs.append(f"{cp}: set downloadDirectorySource and downloadDirectoryTarget together")
        for name in sorted(_dupes(r["name"] for r in c["seedingRules"])):
            errs.append(f"{cp}.seedingRules: name {name!r} is used twice")
        for ri, r in enumerate(c["seedingRules"]):
            rp = f"{cp}.seedingRules[{ri}]"
            if not r["categories"]:
                errs.append(f"{rp}.categories: needs at least one category")
            for field in ("maxRatio", "maxSeedTime", "maxInactiveDays"):
                if r[field] is not None and r[field] < 0 and r[field] != -1:
                    errs.append(f"{rp}.{field}: must be -1 (off) or at least 0")
            if r["maxRatio"] is not None and r["maxSeedTime"] is not None and r["maxRatio"] < 0 and r["maxSeedTime"] < 0:
                errs.append(f"{rp}: set maxRatio or maxSeedTime to 0 or more")
            for field in unsupported.get((ci, ri), ()):
                errs.append(f"{rp}.{field}: not supported by {c['typeName']} clients")
        u = c["unlinked"]
        if u and u["enabled"]:
            up = f"{cp}.unlinked"
            if not u["targetCategory"].strip():
                errs.append(f"{up}.targetCategory: required when enabled")
            if not u["categories"]:
                errs.append(f"{up}.categories: needs at least one category when enabled")
            if u["targetCategory"].lower() in (x.lower() for x in u["categories"]):
                errs.append(f"{up}.categories: must not contain targetCategory")
            for di, d in enumerate(u["ignoredRootDirs"]):
                if not _path_ok(d, check_paths, "dir"):
                    errs.append(f"{up}.ignoredRootDirs[{di}]: directory does not exist in the pod")
        d = c["deadTorrents"]
        if d and d["enabled"]:
            dp = f"{cp}.deadTorrents"
            if c["typeName"] == "rtorrent":
                errs.append(f"{dp}: rtorrent reports no seeder count, so dead-torrent handling is unsupported")
            if not d["targetCategory"].strip():
                errs.append(f"{dp}.targetCategory: required when enabled")
            if not d["categories"]:
                errs.append(f"{dp}.categories: needs at least one category when enabled")
            if d["targetCategory"].lower() in (x.lower() for x in d["categories"]):
                errs.append(f"{dp}.categories: must not contain targetCategory")
            if (d["maxStrikes"] or 0) < 3:
                errs.append(f"{dp}.maxStrikes: must be at least 3 when enabled")
        o = c["orphanedFiles"]
        if o and o["enabled"]:
            op = f"{cp}.orphanedFiles"
            if not o["scanDirectories"]:
                errs.append(f"{op}.scanDirectories: needs at least one directory when enabled")
            if not o["orphanedDirectory"].strip():
                errs.append(f"{op}.orphanedDirectory: required when enabled")
            else:
                orphaned = _norm_dir(o["orphanedDirectory"])
                for s in o["scanDirectories"]:
                    scan = _norm_dir(s)
                    if scan.lower() == orphaned.lower() or scan.lower().startswith(orphaned.lower() + "/"):
                        errs.append(f"{op}.orphanedDirectory: must not equal or contain scan directory {s!r}")
            mine = [_norm_dir(x) for x in o["scanDirectories"]] + (
                [_norm_dir(o["orphanedDirectory"])] if o["orphanedDirectory"].strip() else [])
            for oi, other in enumerate(clients):
                if oi == ci:
                    continue
                theirs = []
                if other["orphanedFiles"]:
                    theirs += [_norm_dir(x) for x in other["orphanedFiles"]["scanDirectories"]]
                    if other["orphanedFiles"]["orphanedDirectory"].strip():
                        theirs.append(_norm_dir(other["orphanedFiles"]["orphanedDirectory"]))
                if other["downloadDirectoryTarget"].strip():
                    theirs.append(_norm_dir(other["downloadDirectoryTarget"]))
                for a in mine:
                    for b in theirs:
                        if _overlap(a, b):
                            errs.append(f"{op}: path {a!r} overlaps {b!r} of client {other['name']!r}")

    notes = ds["notifications"]
    for name in sorted(_dupes(n["name"] for n in notes)):
        errs.append(f"{VALUES}.notifications: name {name!r} is used twice")
    for ni, n in enumerate(notes):
        np_ = f"{VALUES}.notifications[{ni}]"
        present = [k for k in PROVIDERS if n[k] is not None]
        if present != [n["type"]]:
            errs.append(f"{np_}: needs exactly one provider block, named as the type ({n['type']!r})")
            continue
        pv = n[n["type"]]
        pp = f"{np_}.{n['type']}"
        t = n["type"]
        if t == "notifiarr" and len(pv["apiKey"] or "") < 10:
            errs.append(f"{pp}.apiKey: must be at least 10 characters")
        elif t == "apprise":
            if pv["mode"] == "api":
                if not pv["url"] or http_url_error(pv["url"]):
                    errs.append(f"{pp}.url: an http(s) URL is required in api mode")
                if len(pv["key"].strip()) < 2:
                    errs.append(f"{pp}.key: at least 2 characters are required in api mode")
            elif not pv["serviceUrls"].strip():
                errs.append(f"{pp}.serviceUrls: required in cli mode")
        elif t == "ntfy":
            if not any(x.strip() for x in pv["topics"]):
                errs.append(f"{pp}.topics: needs at least one topic")
            if pv["authenticationType"] == "basicauth" and not (pv["username"].strip() and pv["password"].strip()):
                errs.append(f"{pp}: basicauth needs username and password")
            if pv["authenticationType"] == "accesstoken" and not pv["accessToken"].strip():
                errs.append(f"{pp}.accessToken: required for accesstoken authentication")
        elif t == "pushover":
            if pv["priority"] == "emergency":
                if pv["retry"] is None or pv["retry"] < 30:
                    errs.append(f"{pp}.retry: emergency priority needs at least 30 seconds")
                if pv["expire"] is None or not 1 <= pv["expire"] <= 10800:
                    errs.append(f"{pp}.expire: emergency priority needs 1..10800 seconds")
            if pv["sound"] and not pv["sound"].strip():
                errs.append(f"{pp}.sound: must not be blank")
        elif t == "telegram" and len(pv["botToken"] or "") < 10:
            errs.append(f"{pp}.botToken: must be at least 10 characters")

    auth = ds["auth"]
    if bool(auth["username"]) != bool(auth["passwordHash"]):
        errs.append(f"{VALUES}.auth: set username and passwordHash together")


def load_desired(path, check_paths):
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError) as exc:
        raise Fail(EXIT_INVALID, f"cannot read the desired state {path}: {type(exc).__name__}")
    errs = []
    ds = normalize(DESIRED, raw, VALUES, errs)
    if not errs:
        validate_semantics(ds, errs, check_paths, _unsupported_rule_fields(raw, ds))
    if ds.get("schema") not in (None, DESIRED_SCHEMA):
        errs.append(f"schema: {ds['schema']!r} is not {DESIRED_SCHEMA}; render it with a matching chart")
    if errs:
        for line in errs:
            log(f"INVALID {line}")
        raise Fail(EXIT_INVALID, f"{len(errs)} invalid value(s); nothing was written")
    if ds["appVersion"] != SUPPORTED_APP_VERSION:
        raise Fail(EXIT_GUARD, f"the desired state targets Cleanuparr {ds['appVersion']}, this script "
                               f"supports {SUPPORTED_APP_VERSION}")
    return ds


def _unsupported_rule_fields(raw, ds):
    """{(client index, rule index): [fields]} set in values that the client's rule table lacks."""
    bad = {}
    for ci, (client, raw_client) in enumerate(zip(ds["downloadClients"], raw.get("downloadClients") or [])):
        for ri, rule in enumerate((raw_client or {}).get("seedingRules") or []):
            fields = [f for f, types in SEEDING_FIELD_CLIENTS.items()
                      if isinstance(rule, dict) and rule.get(f) is not None and client["typeName"] not in types]
            if fields:
                bad[(ci, ri)] = fields
    return bad


# -- storage mapping and semantic comparison ------------------------------------------------------
def to_storage(leaf, value):
    if value is None:
        return None
    kind = leaf.kind
    if kind == BOOL:
        return 1 if value else 0
    if kind == INT:
        return int(value)
    if kind in (REAL, REAL32):
        return float(value)
    if kind == ENUM:
        return value.lower()
    if kind == JSON_LIST:
        return json.dumps(list(value), separators=(",", ":"), ensure_ascii=False)
    if kind == CSV_LIST:
        return ",".join(value)
    if leaf.empty_as_null and value == "":
        return None
    return value


def _semantic(leaf, stored):
    kind = leaf.kind
    if kind == JSON_LIST:
        if stored is None:
            return []
        try:
            parsed = json.loads(stored)
        except (TypeError, ValueError):
            return ("<unparsable>", stored)
        return [] if parsed is None else parsed
    if kind == CSV_LIST:
        return [x for x in (stored or "").split(",") if x]
    if kind == BOOL:
        return None if stored is None else stored != 0
    if kind == ENUM:
        return None if stored is None else str(stored).strip().lower()
    if kind == TEXT and leaf.empty_as_null and stored == "":
        return None
    return stored


def same(leaf, stored, desired):
    if leaf.secret:
        a, b = _semantic(leaf, stored), _semantic(leaf, desired)
        if a is None or b is None:
            return a is None and b is None
        return hmac.compare_digest(str(a).encode(), str(b).encode())
    a, b = _semantic(leaf, stored), _semantic(leaf, desired)
    if leaf.kind in (REAL, REAL32) and a is not None and b is not None:
        try:
            a, b = float(a), float(b)
            # The app's model is float32 for REAL32 columns, so a UI save stores 0.4 as 0.4000000059604645.
            if leaf.kind == REAL32:
                return struct.pack("<f", a) == struct.pack("<f", b)
        except (TypeError, ValueError, OverflowError):
            return False
        return abs(a - b) < 1e-9
    if leaf.kind == INT and a is not None and b is not None:
        return isinstance(a, int) and not isinstance(a, bool) and a == b
    return a == b


def show(leaf, stored):
    if leaf.secret:
        return "(secret set)" if _semantic(leaf, stored) not in (None, "") else "(secret empty)"
    value = _semantic(leaf, stored)
    if leaf.kind == BOOL and value is not None:
        return "true" if value else "false"
    text = masked_repr(value)
    return text if len(text) <= 200 else text[:197] + "..."


def leaves_for(spec, value):
    """(leaf, value) pairs of spec's own table columns, without nested tables or lists."""
    out = []
    for key, field in spec.fields.items():
        if isinstance(field, Leaf):
            if field.col:
                out.append((field, value[key]))
        elif isinstance(field, Obj) and field.table is None:
            out.extend(leaves_for(field, value[key]))
    return out


def new_guid():
    return str(uuid.uuid4()).upper()


def utc_now():
    # 7 fractional digits, as UtcDateTimeOffsetConverter.cs:16 writes them.
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f") + "0"


# -- plan model -----------------------------------------------------------------------------------
class Op:
    def __init__(self, action, db, table, label, *, row_id=None, values=None, leaves=None,
                 changes=None, note="", phase=0):
        self.action, self.db, self.table, self.label = action, db, table, label
        self.row_id, self.values, self.leaves = row_id, values or {}, leaves or {}
        self.changes, self.note, self.phase = changes or [], note, phase

    def lines(self):
        target = self.table + (f"[{self.label}]" if self.label is not None else "")
        if self.action == "UPDATE":
            return [f"UPDATE {target} {col}: {self._change(leaf, old, new)}" for col, leaf, old, new in self.changes]
        if self.action == "INSERT":
            body = ", ".join(f"{col}: {show(leaf, self.values[col])}" for col, leaf in self.leaves.items())
            return [f"INSERT {target} {{{body}}}"]
        return [f"DELETE {target} ({self.note})" if self.note else f"DELETE {target}"]

    @staticmethod
    def _change(leaf, old, new):
        if not leaf.secret:
            return f"{show(leaf, old)} -> {show(leaf, new)}"
        if _semantic(leaf, new) in (None, ""):
            return "(secret removed)"
        return "(secret set)" if _semantic(leaf, old) in (None, "") else "(secret changed)"


class Effect:
    """events.db statements the app's API runs alongside a settings change."""

    def __init__(self, title, statements, counts):
        self.title, self.statements, self.counts = title, statements, counts

    def lines(self):
        detail = ", ".join(f"{n} {t}" for t, n in self.counts)
        return [f"EVENTS.DB {self.title}: {detail}"]


# Execution order: child deletes, parent deletes, parent upserts, child upserts, singletons.
PHASE_DELETE_CHILD, PHASE_DELETE_PARENT, PHASE_UPSERT_PARENT, PHASE_UPSERT_CHILD, PHASE_SINGLETON = range(5)
EVENT_INSTANCE_TABLES = ("custom_format_score_entries", "custom_format_score_history", "seeker_history",
                         "search_queue", "seeker_command_trackers")


class Planner:
    def __init__(self, dbs, ds, data_only):
        self.dbs, self.ds, self.data_only = dbs, ds, data_only
        self.ops, self.effects, self.notes = [], [], []
        self.deleted_instances = []
        self.instance_label, self.client_label = {}, {}

    def rows(self, table, db=DATA_DB):
        rows = [dict(r) for r in self.dbs[db].execute(f'SELECT * FROM "{table}"')]
        for row in rows:
            for col in SECRET_COLUMNS.get(table, ()):
                remember_secret(row.get(col))
        return rows

    def diff(self, row, pairs, extra=None):
        changes = []
        for leaf, value in pairs:
            new = to_storage(leaf, value)
            if not same(leaf, row[leaf.col], new):
                changes.append((leaf.col, leaf, row[leaf.col], new))
        for col, (leaf, new) in (extra or {}).items():
            if not same(leaf, row[col], new):
                changes.append((col, leaf, row[col], new))
        return changes

    def upsert(self, table, label, row, pairs, phase, extra=None, insert_extra=None, db=DATA_DB):
        """Plans an INSERT (row is None) or an UPDATE of the changed columns; returns (id, changed)."""
        if row is None:
            leaves = {leaf.col: leaf for leaf, _ in pairs}
            values = {leaf.col: to_storage(leaf, value) for leaf, value in pairs}
            for col, (leaf, new) in (extra or {}).items():
                leaves[col], values[col] = leaf, new
            values.update(insert_extra or {})
            values["id"] = new_guid()
            self.ops.append(Op("INSERT", db, table, label, values=values, leaves=leaves, phase=phase))
            return values["id"], True
        changes = self.diff(row, pairs, extra)
        if changes:
            self.ops.append(Op("UPDATE", db, table, label, row_id=row["id"], changes=changes, phase=phase))
        return row["id"], bool(changes)

    def delete(self, table, label, row, note, phase=PHASE_DELETE_CHILD):
        self.ops.append(Op("DELETE", DATA_DB, table, label, row_id=row["id"], note=note, phase=phase))

    @staticmethod
    def match(rows, key_fn, wanted):
        """Pairs rows with wanted natural keys; the smallest id wins, every other row is returned as extra."""
        matched, extras = {}, []
        for row in sorted(rows, key=lambda r: r["id"]):
            key = key_fn(row)
            if key in wanted and key not in matched:
                matched[key] = row
            else:
                extras.append(row)
        return matched, extras

    def plan(self):
        self.plan_singletons()
        seeker_instances = self.plan_arr()
        clients = self.plan_clients()
        self.plan_rules()
        self.plan_notifications()
        self.plan_seeker_instances(seeker_instances)
        self.plan_client_children(clients)
        if self.data_only:
            if self.rows("general_configs")[0]["dry_run"] and not self.ds["general"]["dryRun"]:
                self.notes.append("--data-only: the events.db dry-run purge is skipped")
        else:
            self.plan_users()
            self.plan_effects()
        self.ops.sort(key=lambda op: op.phase)
        return self

    def plan_singletons(self):
        for section, spec in DESIRED.fields.items():
            if isinstance(spec, Obj) and spec.table in SINGLETON_TABLES:
                row = self.rows(spec.table)[0]
                self.upsert(spec.table, None, row, leaves_for(spec, self.ds[section]), PHASE_SINGLETON)

    def plan_arr(self):
        configs = {r["type"]: r for r in self.rows("arr_configs")}
        type_by_config = {r["id"]: r["type"] for r in configs.values()}
        instances = self.rows("arr_instances")
        self.instance_label = {r["id"]: f"{type_by_config.get(r['arr_config_id'], '?')}/{r['name']}"
                               for r in instances}
        seeker_instances = {}
        for key, (db_type, _, _) in ARR_TYPES.items():
            spec = DESIRED.fields["arr"].fields[key]
            config = configs[db_type]
            self.upsert("arr_configs", db_type, config, leaves_for(spec, self.ds["arr"][key]), PHASE_SINGLETON)
            wanted = {i["name"].lower(): i for i in self.ds["arr"][key]["instances"]}
            mine = [r for r in instances if r["arr_config_id"] == config["id"]]
            matched, extras = self.match(mine, lambda r: r["name"].strip().lower(), wanted)
            for row in extras:
                self.deleted_instances.append(row)
                note = "not in values; cascades its seeker_instance_configs row"
                if not self.data_only:
                    total = sum(n for _, n in self._instance_event_counts(row["id"]))
                    note += f"; events.db: {total} rows"
                self.delete("arr_instances", self.instance_label[row["id"]], row, note, PHASE_DELETE_PARENT)
            config_fk = {"arr_config_id": (Leaf(TEXT, None, "arr_config_id"), config["id"])}
            for name_key, inst in wanted.items():
                instance_id, _ = self.upsert(
                    "arr_instances", f"{db_type}/{inst['name']}", matched.get(name_key),
                    leaves_for(spec.fields["instances"].item, inst), PHASE_UPSERT_PARENT, extra=config_fk)
                if key in SEEKER_TYPES:
                    seeker_instances[instance_id] = (db_type, inst)
        return seeker_instances

    def plan_seeker_instances(self, seeker_instances):
        matched, extras = self.match(self.rows("seeker_instance_configs"), lambda r: r["arr_instance_id"],
                                     seeker_instances)
        deleted = {row["id"] for row in self.deleted_instances}
        for row in extras:
            if row["arr_instance_id"] in deleted:
                continue  # removed by the instance delete's ON DELETE CASCADE
            label = self.instance_label.get(row["arr_instance_id"], row["arr_instance_id"])
            self.delete("seeker_instance_configs", label, row, "instance not searched by the Seeker")
        for instance_id, (db_type, inst) in seeker_instances.items():
            # Runtime columns are written on INSERT only; Seeker.cs updates them in place.
            self.upsert("seeker_instance_configs", f"{db_type}/{inst['name']}", matched.get(instance_id),
                        leaves_for(SEEKER_INSTANCE, inst["seeker"]), PHASE_UPSERT_CHILD,
                        insert_extra={"arr_instance_id": instance_id, "current_cycle_id": new_guid(),
                                      "total_eligible_items": 0, "last_processed_at": None})

    def plan_clients(self):
        rows = self.rows("download_clients")
        self.client_label = {r["id"]: r["name"] for r in rows}
        history = {}
        for r in self.rows("blacklist_sync_history"):
            history[r["download_client_id"]] = history.get(r["download_client_id"], 0) + 1
        wanted = {c["name"].lower(): c for c in self.ds["downloadClients"]}
        matched, extras = self.match(rows, lambda r: r["name"].strip().lower(), wanted)
        for row in extras:
            self.delete("download_clients", row["name"], row,
                        f"not in values; cascades {history.get(row['id'], 0)} blacklist_sync_history rows",
                        PHASE_DELETE_PARENT)
        clients = {}
        for key, client in wanted.items():
            client_id, _ = self.upsert("download_clients", client["name"], matched.get(key),
                                       leaves_for(DOWNLOAD_CLIENT, client), PHASE_UPSERT_PARENT,
                                       extra=FIXED_COLUMNS["download_clients"])
            clients[client_id] = client
        return clients

    def plan_client_children(self, clients):
        for type_name, table in SEEDING_TABLES.items():
            rows = self.rows(table)
            columns = set(_columns(DATA_DB, table))
            for client_id, client in clients.items():
                mine = [r for r in rows if r["download_client_config_id"] == client_id]
                wanted = {}
                if client["typeName"] == type_name:
                    wanted = {r["name"].lower(): (i, r) for i, r in enumerate(client["seedingRules"])}
                matched, extras = self.match(mine, lambda r: r["name"].strip().lower(), wanted)
                for row in extras:
                    self.delete(table, f"{client['name']}/{row['name']}", row, "not in values")
                for key, (index, rule) in wanted.items():
                    pairs = [(leaf, v) for leaf, v in leaves_for(SEEDING_RULE, rule) if leaf.col in columns]
                    # List order is the evaluation order the UI's reorder endpoint stores as 1..n.
                    priority = {"priority": (Leaf(INT, None, "priority"), index + 1)}
                    self.upsert(table, f"{client['name']}/{rule['name']}", matched.get(key), pairs,
                                PHASE_UPSERT_CHILD, extra=priority,
                                insert_extra={"download_client_config_id": client_id})
            for row in rows:
                if row["download_client_config_id"] not in clients:
                    label = f"{self.client_label.get(row['download_client_config_id'], '?')}/{row['name']}"
                    self.delete(table, label, row, "client not in values")
        for field, spec in (("unlinked", UNLINKED), ("deadTorrents", DEAD_TORRENTS),
                            ("orphanedFiles", ORPHANED_FILES)):
            wanted = {cid: c[field] for cid, c in clients.items() if c[field] is not None}
            matched, extras = self.match(self.rows(spec.table), lambda r: r["download_client_config_id"], wanted)
            for row in extras:
                self.delete(spec.table, self.client_label.get(row["download_client_config_id"], "?"), row,
                            "not in values")
            for client_id, value in wanted.items():
                self.upsert(spec.table, clients[client_id]["name"], matched.get(client_id),
                            leaves_for(spec, value), PHASE_UPSERT_CHILD,
                            insert_extra={"download_client_config_id": client_id})

    def plan_rules(self):
        queue_cleaner_fk = {"queue_cleaner_config_id": (Leaf(TEXT, None, "queue_cleaner_config_id"),
                                                        self.rows("queue_cleaner_configs")[0]["id"])}
        for field, spec in (("stallRules", STALL_RULE), ("slowRules", SLOW_RULE)):
            wanted = {r["name"].lower(): r for r in self.ds["queueCleaner"][field]}
            matched, extras = self.match(self.rows(spec.table), lambda r: r["name"].strip().lower(), wanted)
            for row in extras:
                self.delete(spec.table, row["name"], row, "not in values")
            for key, rule in wanted.items():
                self.upsert(spec.table, rule["name"], matched.get(key), leaves_for(spec, rule),
                            PHASE_UPSERT_CHILD, extra=queue_cleaner_fk)

    def plan_notifications(self):
        children = {t: self.rows(spec.table) for t, spec in PROVIDERS.items()}

        def children_of(parent_id):
            return [(t, c) for t in PROVIDERS for c in sorted(children[t], key=lambda c: c["id"])
                    if c["notification_config_id"] == parent_id]

        wanted = {n["name"].lower(): n for n in self.ds["notifications"]}
        matched, extras = self.match(self.rows("notification_configs"), lambda r: r["name"].strip().lower(),
                                     wanted)
        for row in extras:
            for t, child in children_of(row["id"]):
                self.delete(PROVIDERS[t].table, row["name"], child, "provider not in values")
            self.delete("notification_configs", row["name"], row, "not in values", PHASE_DELETE_PARENT)
        now = utc_now()
        for key, note in wanted.items():
            row, provider = matched.get(key), PROVIDERS[note["type"]]
            pairs, child_pairs = leaves_for(NOTIFICATION, note), leaves_for(provider, note[note["type"]])
            if row is None:
                parent_id, _ = self.upsert("notification_configs", note["name"], None, pairs, PHASE_UPSERT_PARENT,
                                           insert_extra={"created_at": now, "updated_at": now})
                self.upsert(provider.table, note["name"], None, child_pairs, PHASE_UPSERT_CHILD,
                            insert_extra={"notification_config_id": parent_id})
                continue
            kept, child_changed = None, False
            for t, child in children_of(row["id"]):
                if t == note["type"] and kept is None:
                    kept = child
                else:
                    self.delete(PROVIDERS[t].table, note["name"], child, "provider type changed or duplicated")
                    child_changed = True
            _, changed = self.upsert(provider.table, note["name"], kept, child_pairs, PHASE_UPSERT_CHILD,
                                     insert_extra={"notification_config_id": row["id"]})
            parent_changes = self.diff(row, pairs)
            if parent_changes or changed or child_changed:
                parent_changes.append(("updated_at", Leaf(TEXT, None, "updated_at"), row["updated_at"], now))
                self.ops.append(Op("UPDATE", DATA_DB, "notification_configs", note["name"], row_id=row["id"],
                                   changes=parent_changes, phase=PHASE_UPSERT_PARENT))

    def plan_users(self):
        auth = self.ds["auth"]
        users = self.rows("users", USERS_DB)
        for row in users:
            remember_secret(row["api_key"])
            remember_secret(row["password_hash"])
        if not users:
            if not auth["username"]:
                self.notes.append("WARNING no Cleanuparr account and no auth.username/passwordHash: "
                                  "the UI will show the setup wizard")
                return
            now = utc_now()
            api_key = auth["apiKey"] or secrets.token_hex(32)
            remember_secret(api_key)
            values = {"id": new_guid(), "username": auth["username"], "password_hash": auth["passwordHash"],
                      "totp_secret": "", "totp_enabled": 0, "api_key": api_key, "setup_completed": 1,
                      "failed_login_attempts": 0, "created_at": now, "updated_at": now}
            leaves = {"username": Leaf(TEXT, None, "username"),
                      "password_hash": Leaf(TEXT, None, "password_hash", secret=True),
                      "api_key": Leaf(TEXT, None, "api_key", secret=True),
                      "setup_completed": Leaf(BOOL, None, "setup_completed")}
            self.ops.append(Op("INSERT", USERS_DB, "users", auth["username"], values=values, leaves=leaves,
                               phase=PHASE_SINGLETON))
            return
        user = users[0]
        if auth["apiKey"]:
            leaf = Leaf(TEXT, None, "api_key", secret=True)
            if not same(leaf, user["api_key"], auth["apiKey"]):
                self.ops.append(Op("UPDATE", USERS_DB, "users", user["username"], row_id=user["id"], changes=[
                    ("api_key", leaf, user["api_key"], auth["apiKey"]),
                    ("updated_at", Leaf(TEXT, None, "updated_at"), user["updated_at"], utc_now())],
                    phase=PHASE_SINGLETON))
        if auth["username"] and (auth["username"] != user["username"] or not hmac.compare_digest(
                auth["passwordHash"].encode(), (user["password_hash"] or "").encode())):
            self.notes.append("an account exists: auth.username and auth.passwordHash only bootstrap an "
                              "empty users.db, so the stored account is kept")
        if not user["setup_completed"]:
            self.notes.append("WARNING the stored account has not completed setup, so API keys are rejected")

    def _instance_event_counts(self, instance_id):
        events = self.dbs[EVENTS_DB]
        counts = [(t, events.execute(f'SELECT COUNT(*) FROM "{t}" WHERE arr_instance_id = ?',
                                     (instance_id,)).fetchone()[0]) for t in EVENT_INSTANCE_TABLES]
        counts.append(("searchtriggered events marked failed", events.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'searchtriggered' "
            "AND search_status IN ('pending', 'started') AND arr_instance_id = ?", (instance_id,)).fetchone()[0]))
        return counts

    def plan_effects(self):
        events = self.dbs[EVENTS_DB]
        if self.rows("general_configs")[0]["dry_run"] and not self.ds["general"]["dryRun"]:
            # The purge GeneralConfigController.cs:66-100 runs when Dry Run is switched off.
            statements = [
                ("strikes", "DELETE FROM strikes WHERE is_dry_run = 1", ()),
                ("events", "DELETE FROM events WHERE is_dry_run = 1", ()),
                ("manual_events", "DELETE FROM manual_events WHERE is_dry_run = 1", ()),
                ("download_items", "DELETE FROM download_items WHERE NOT EXISTS "
                                   "(SELECT 1 FROM strikes s WHERE s.download_item_id = download_items.id)", ()),
                ("seeker_history", "DELETE FROM seeker_history WHERE is_dry_run = 1", ()),
            ]
            counts = [(t, events.execute(f"SELECT COUNT(*) FROM {t} WHERE is_dry_run = 1").fetchone()[0])
                      for t in ("strikes", "events", "manual_events")]
            counts.insert(3, ("download_items", events.execute(
                "SELECT COUNT(*) FROM download_items d WHERE NOT EXISTS (SELECT 1 FROM strikes s "
                "WHERE s.download_item_id = d.id AND s.is_dry_run = 0)").fetchone()[0]))
            counts.append(("seeker_history", events.execute(
                "SELECT COUNT(*) FROM seeker_history WHERE is_dry_run = 1").fetchone()[0]))
            self.effects.append(Effect("dry-run purge (general.dryRun true -> false)", statements, counts))
        for row in self.deleted_instances:
            instance_id = row["id"]
            # The cleanup ArrConfigController.cs:334-382 and EventPublisher.cs:455-469 run on an instance delete.
            statements = [(t, f'DELETE FROM "{t}" WHERE arr_instance_id = ?', (instance_id,))
                          for t in EVENT_INSTANCE_TABLES]
            statements.append(("searchtriggered events marked failed",
                               "UPDATE events SET search_status = 'failed', completed_at = ? "
                               "WHERE event_type = 'searchtriggered' AND search_status IN ('pending', 'started') "
                               "AND arr_instance_id = ?", ("@now", instance_id)))
            self.effects.append(Effect(f"cleanup for deleted instance {self.instance_label[instance_id]}",
                                       statements, self._instance_event_counts(instance_id)))


SECRET_COLUMNS = {}


def _collect_secret_columns(spec):
    if isinstance(spec, Lst):
        _collect_secret_columns(spec.item)
    elif isinstance(spec, Obj):
        for field in spec.fields.values():
            if isinstance(field, Leaf) and field.secret and field.col and spec.table:
                SECRET_COLUMNS.setdefault(spec.table, set()).add(field.col)
            elif isinstance(field, (Obj, Lst)):
                _collect_secret_columns(field)


_collect_secret_columns(DESIRED)


def _columns(db, table):
    return [token.split(":")[0] for token in TABLE_COLUMNS[db][table].split()]


# -- databases and guards -------------------------------------------------------------------------
def connect(path, readonly):
    mode = "ro" if readonly else "rw"
    con = sqlite3.connect(f"file:{quote(path)}?mode={mode}", uri=True, isolation_level=None, timeout=10)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout = 10000")
        # Python's SQLite defaults to off; the app's bundled SQLite enforces foreign keys, and cascades
        # must match what its own deletes do.
        con.execute("PRAGMA foreign_keys = ON")
        if con.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise Fail(EXIT_GUARD, f"{os.path.basename(path)}: cannot enable foreign keys")
    except BaseException:
        con.close()
        raise
    return con


def applied_migrations(con):
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "__EFMigrationsHistory" not in tables:
        return []
    return [r[0] for r in con.execute('SELECT migration_id FROM "__EFMigrationsHistory" ORDER BY migration_id')]


def open_databases(config_dir, names, readonly):
    dbs = {}
    try:
        for name in names:
            path = os.path.join(config_dir, name)
            if not os.path.isfile(path):
                raise Fail(EXIT_GUARD, f"{name} does not exist in {config_dir}; the migrate step must run first")
            dbs[name] = connect(path, readonly)
    except BaseException:
        close_all(dbs)
        raise
    return dbs


def guard(dbs):
    problems = []
    for name, con in dbs.items():
        applied = applied_migrations(con)
        expected = list(EXPECTED_MIGRATIONS[name])
        if applied != sorted(expected):
            unknown = sorted(set(applied) - set(expected))
            missing = sorted(set(expected) - set(applied))
            problems.append(f"{name}: migrations differ from Cleanuparr {SUPPORTED_APP_VERSION} "
                            f"(unknown {unknown or 'none'}, missing {missing or 'none'})")
            continue
        if con.execute('SELECT COUNT(*) FROM "__EFMigrationsLock"').fetchone()[0]:
            problems.append(f"{name}: __EFMigrationsLock holds a row (a migration is running or crashed)")
        for table, spec in TABLE_COLUMNS[name].items():
            want = set(spec.split())
            have = {f"{r[1]}:{r[2]}" for r in con.execute(f'PRAGMA table_info("{table}")')}
            if have != want:
                problems.append(f"{name}.{table}: columns differ (missing {sorted(want - have) or 'none'}, "
                                f"unexpected {sorted(have - want) or 'none'})")
    if problems:
        for line in problems:
            log(f"GUARD {line}")
        raise Fail(EXIT_GUARD, "schema guard failed; nothing was written")
    data = dbs[DATA_DB]
    for table in SINGLETON_TABLES:
        count = data.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        if count != 1:
            problems.append(f"{table} has {count} rows, expected exactly 1")
    types = [r[0] for r in data.execute("SELECT type FROM arr_configs")]
    if sorted(types) != sorted(t for t, _, _ in ARR_TYPES.values()):
        problems.append(f"arr_configs types are {sorted(types)}, expected one row per arr type")
    if USERS_DB in dbs:
        users = dbs[USERS_DB].execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if users > 1:
            problems.append(f"users has {users} rows; the app supports one account")
    # Every FK is immediate, so a violation found after the writes could only predate them.
    for name, con in dbs.items():
        broken = {}
        for table, _, parent, _ in con.execute("PRAGMA foreign_key_check"):
            broken[(table, parent)] = broken.get((table, parent), 0) + 1
        for (table, parent), count in sorted(broken.items()):
            problems.append(f"{name}: {count} {table} rows reference missing {parent} rows")
    if problems:
        for line in problems:
            log(f"GUARD {line}")
        raise Fail(EXIT_GUARD, "data guard failed; nothing was written")


# -- apply ----------------------------------------------------------------------------------------
def _quote_cols(cols):
    return ", ".join(f'"{c}"' for c in cols)


def execute_op(con, op):
    if op.action == "INSERT":
        cols = list(op.values)
        con.execute(f'INSERT INTO "{op.table}" ({_quote_cols(cols)}) VALUES ({", ".join("?" * len(cols))})',
                    [op.values[c] for c in cols])
        return
    if op.action == "UPDATE":
        assignments = ", ".join(f'"{col}" = ?' for col, _, _, _ in op.changes)
        cursor = con.execute(f'UPDATE "{op.table}" SET {assignments} WHERE id = ?',
                             [new for _, _, _, new in op.changes] + [op.row_id])
    else:
        cursor = con.execute(f'DELETE FROM "{op.table}" WHERE id = ?', (op.row_id,))
    if cursor.rowcount != 1:
        raise Fail(EXIT_ERROR, f"{op.action} {op.table} touched {cursor.rowcount} rows instead of 1")


def apply_plan(dbs, planner):
    now = utc_now()
    targets = ([EVENTS_DB] if planner.effects else []) + [
        name for name in (DATA_DB, USERS_DB) if any(op.db == name for op in planner.ops)]
    begun, done = [], []
    try:
        # All write locks first, so a failure before the commits leaves every database untouched.
        for name in targets:
            dbs[name].execute("BEGIN IMMEDIATE")
            begun.append(name)
        for effect in planner.effects:
            counts = []
            for table, sql, params in effect.statements:
                params = tuple(now if p == "@now" else p for p in params)
                counts.append(f"{dbs[EVENTS_DB].execute(sql, params).rowcount} {table}")
            done.append(f"EVENTS.DB {effect.title} done: {', '.join(counts)}")
        for name in (n for n in targets if n != EVENTS_DB):
            con = dbs[name]
            for op in planner.ops:
                if op.db == name:
                    execute_op(con, op)
            if con.execute("PRAGMA foreign_key_check").fetchall():
                raise Fail(EXIT_ERROR, f"{name}: the changes broke a foreign key; rolled back")
    except BaseException:
        for name in begun:
            try:
                dbs[name].execute("ROLLBACK")
            except sqlite3.Error:
                pass  # SQLite already rolled it back (disk full, I/O error); keep the original error
        raise
    # Commit order events.db, cleanuparr.db, users.db: a stop between commits leaves the earlier ones
    # committed, and the next start plans and writes the rest.
    for name in targets:
        dbs[name].execute("COMMIT")
        log(f"committed {name}")
        if name == EVENTS_DB:
            for line in done:
                log(line)
    log(f"{len(plan_lines(planner))} changes applied to {', '.join(targets)}")
    for name in targets:
        try:
            busy = dbs[name].execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]
        except sqlite3.Error as exc:
            busy = exc
        if busy:
            log(f"WARNING {name}: WAL checkpoint incomplete ({busy}); the app checkpoints it later")
    return targets


def plan_lines(planner):
    lines = []
    for effect in planner.effects:
        lines.extend(effect.lines())
    for op in planner.ops:
        lines.extend(op.lines())
    return lines


def make_plan(config_dir, ds, data_only, readonly):
    names = [DATA_DB] if data_only else [DATA_DB, EVENTS_DB, USERS_DB]
    dbs = open_databases(config_dir, names, readonly)
    try:
        guard(dbs)
        return dbs, Planner(dbs, ds, data_only).plan()
    except BaseException:
        close_all(dbs)
        raise


def close_all(dbs):
    for con in dbs.values():
        con.close()


# -- subcommands ----------------------------------------------------------------------------------
TAG_RE = re.compile(r"v?([0-9]+\.[0-9]+\.[0-9]+)(@sha256:[0-9a-f]{64})?")


def embedded_migrations(path):
    """Migration ids compiled into the app bundle, read in chunks (the bundle is about 200 MB)."""
    found, carry = set(), b""
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(8 << 20)
            data = carry + chunk
            for match in MIGRATION_ID_RE.finditer(data):
                if chunk and match.end() == len(data):
                    continue  # may continue in the next chunk
                found.add(match.group().decode())
            if not chunk:
                return found
            carry = data[-128:]


def cmd_preflight(args):
    tag = os.environ.get("CLEANUPARR_IMAGE_TAG", "")
    match = TAG_RE.fullmatch(tag)
    if not match or match.group(1) != SUPPORTED_APP_VERSION:
        raise Fail(EXIT_GUARD, f"image tag {tag!r} is not Cleanuparr {SUPPORTED_APP_VERSION}; this chart's "
                               "settings contract was reviewed for that version only")
    if args.app:
        found = embedded_migrations(args.app)
        newest = max((m.split("_", 1)[0] for m in found), default="none")
        missing = sorted({m for ids in EXPECTED_MIGRATIONS.values() for m in ids} - found)
        if newest != IMAGE_NEWEST_MIGRATION or missing:
            raise Fail(EXIT_GUARD, f"{args.app} is not the Cleanuparr {SUPPORTED_APP_VERSION} build (newest "
                                   f"migration {newest}, expected {IMAGE_NEWEST_MIGRATION}; {len(missing)} "
                                   "known migrations missing): the image digest belongs to another release")
        log(f"preflight: {args.app} embeds the {SUPPORTED_APP_VERSION} migrations")
    settings_file = os.path.join(args.config_dir, "cleanuparr.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, encoding="utf-8") as handle:
                keys = {str(k).upper() for k in json.load(handle)}
        except (OSError, ValueError, TypeError):
            raise Fail(EXIT_GUARD, "cleanuparr.json is unreadable; it would override the migrate-only settings")
        # The app loads this file after the environment (Program.cs:21-22), so it would override BASE_PATH.
        if keys & {"BASE_PATH", "DATABASE_PROVIDER"}:
            raise Fail(EXIT_GUARD, "cleanuparr.json sets BASE_PATH or DATABASE_PROVIDER, which defeats the "
                                   "migrate-only start; remove those keys")
    for name, expected in EXPECTED_MIGRATIONS.items():
        path = os.path.join(args.config_dir, name)
        if not os.path.isfile(path):
            log(f"preflight: {name} not present yet (fresh volume)")
            continue
        con = connect(path, readonly=True)
        try:
            applied = applied_migrations(con)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            locked = "__EFMigrationsLock" in tables and con.execute(
                'SELECT COUNT(*) FROM "__EFMigrationsLock"').fetchone()[0]
        finally:
            con.close()
        unknown = sorted(set(applied) - set(expected))
        if unknown:
            raise Fail(EXIT_GUARD, f"{name} carries migrations newer than Cleanuparr {SUPPORTED_APP_VERSION} "
                                   f"({', '.join(unknown)}); restore the matching image or a backup")
        # A pending migration would wait on this lock forever (a crash mid-migration leaves the row).
        if locked:
            raise Fail(EXIT_GUARD, f"{name}: __EFMigrationsLock holds a row from an interrupted migration; "
                                   "back up /config, then delete that row")
        log(f"preflight: {name} has {len(applied)}/{len(expected)} known migrations")
    log("preflight ok")
    return EXIT_OK


def cmd_validate(args):
    load_desired(args.desired, check_paths=False)
    log(f"desired state valid for Cleanuparr {SUPPORTED_APP_VERSION}; file and directory paths are "
        "checked at pod start only")
    return EXIT_OK


def cmd_reconcile(args):
    ds = load_desired(args.desired, check_paths=True)
    mode = args.mode or ds["mode"]
    if args.data_only:
        log("--data-only: users.db and events.db are neither checked nor written")
    dbs, planner = make_plan(args.config_dir, ds, args.data_only, readonly=(mode == "plan"))
    heads = ", ".join(f"{n}={applied_migrations(c)[-1]}" for n, c in dbs.items())
    log(f"contract Cleanuparr {SUPPORTED_APP_VERSION} (schema {DESIRED_SCHEMA}), mode {mode}, heads {heads}")
    try:
        for note in planner.notes:
            log(note)
        lines = plan_lines(planner)
        for line in lines:
            log(line)
        if mode == "plan":
            log(f"plan only, {len(lines)} changes not applied" if lines else "plan only, no changes")
            return EXIT_OK
        if not lines:
            log("no changes")
            return EXIT_OK
        apply_plan(dbs, planner)
    finally:
        close_all(dbs)
    dbs, verify = make_plan(args.config_dir, ds, args.data_only, readonly=True)
    try:
        leftover = plan_lines(verify)
    finally:
        close_all(dbs)
    if leftover:
        for line in leftover:
            log(f"NOT CONVERGED {line}")
        raise Fail(EXIT_NOT_CONVERGED, "post-apply check still finds differences")
    log("post-apply check: no differences")
    return EXIT_OK


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cleanuparr settings as code")
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight", help="refuse unknown image versions and newer databases")
    pre.add_argument("--config-dir", required=True)
    pre.add_argument("--app", help="app bundle whose embedded migrations must match this version")
    val = sub.add_parser("validate", help="validate a desired-state file offline")
    val.add_argument("--desired", required=True)
    rec = sub.add_parser("reconcile", help="plan or apply the desired state")
    rec.add_argument("--desired", required=True)
    rec.add_argument("--config-dir", required=True)
    rec.add_argument("--mode", choices=("plan", "apply"))
    rec.add_argument("--data-only", action="store_true",
                     help="diagnostics on a cleanuparr.db copy; skips users.db and events.db")
    args = parser.parse_args(argv)
    handler = {"preflight": cmd_preflight, "validate": cmd_validate, "reconcile": cmd_reconcile}
    try:
        return handler[args.command](args)
    except Fail as exc:
        log(exc.message)
        return exc.code
    except Exception:
        log("unexpected error; every open transaction was rolled back")
        for line in redact(traceback.format_exc()).splitlines():
            log(line)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
