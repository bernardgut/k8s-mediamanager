-- Fresh Cleanuparr 2.10.8 databases after a migrate-only start, as sqlite3 iterdump (no secrets).
-- Regenerate on an image bump; the '-- database:' lines split the three files.
-- database: cleanuparr.db
BEGIN TRANSACTION;
CREATE TABLE "__EFMigrationsHistory" (
    "migration_id" TEXT NOT NULL CONSTRAINT "pk___ef_migrations_history" PRIMARY KEY,
    "product_version" TEXT NOT NULL
);
INSERT INTO "__EFMigrationsHistory" VALUES('20250621174558_InitialData','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250628231105_AddReadarr','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250702091059_AddWhisparr','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250702192200_ChangeAppriseConfig','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250704152940_AddAppriseTags','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250801143446_AddKnownMalwareOption','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250816183837_AddAdvancedLoggingSettings','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250830230846_ReworkNotificationSystem','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250912234118_AddNtfy','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250915153159_AddBlacklistSyncSettings','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20250915181529_AddPerJobIgnoredDownloads','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251012100711_AddQueueCleanerRules','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251022212536_AddFailedImportPrivateSafeguardOption','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251023074842_UpdateSearchDelay','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251023184757_AddFailedImportTypeHandling','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251211102657_AddPushoverProvider','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251213201344_AddAppriseCliMode','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251216204347_AddDeleteSourceFilesToCleanCategory','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251216222056_RenameCleanCategoryToSeedingRule','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251219224200_ChangeUnlinkedIgnoredRootDirType','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251227170911_AddTelegram','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251231171212_AddWhisparrV3','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260112102214_AddDiscord','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260112134008_AddGotify','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260212204459_AddAppStatusSetting','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260212222238_AddExternalUrl','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260213155055_AddStrikeInactivityWindow','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260216220150_AddSeedingRulePrivacyType','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260223085409_AddAuthConfig','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260306140714_AddProcessMissingContentId','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260306144520_RemoveKnownMalwareOption','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260310181205_RemoveProcessMissingId','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260310181320_AddProcessMissingId','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260324200753_AddSeeker','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260325201158_AddPostReleaseGraceHours','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260326195141_AddIsMonitoredToCfScoreEntry','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260329184534_AddPerClientDownloadCleanerSettings','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260408081126_AddSeedingRuleEnhancements','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260415085810_AddSearchItemGrabbedNotification','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260415192034_MoveSeekerFiltersToInstanceConfig','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260420134250_AddLastUpgradedAtToCfScoreEntry','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260504193343_AddQueueCleanerChangeCategory','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260527073208_AddOrphanedFilesCleanup','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260528100503_AddMinSeedersToSeedingRules','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260528201320_AddDeleteIfAnyFileBlocked','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260613142438_AddDeadTorrentConfig','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260614130148_ConvertDatesToDateTimeOffset','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260703173019_AddHistoryRetentionDays','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260710110305_MoveSeekerStateToEvents','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260713155427_WhisparrBlocklistTypeToText','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260721100758_AddSlowRuleIgnoreAltSpeed','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260723144949_AddConnectivityCheck','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260724145908_AddMaxInactiveDaysToQBitSeedingRule','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260804161642_AddSportarr','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260820230125_AddLazyLibrarian','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260822111016_AddHttpSendUserAgent','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260824114948_AddSeekerIgnoreStruckDownloads','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260903082920_AddSeedingRuleStopAction','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260908230836_AddForceImport','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260912212027_RemoveEncryptionKey','10.0.1');
CREATE TABLE "__EFMigrationsLock" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK___EFMigrationsLock" PRIMARY KEY,
    "Timestamp" TEXT NOT NULL
);
CREATE TABLE "apprise_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_apprise_configs" PRIMARY KEY,
    "key" TEXT NOT NULL,
    "notification_config_id" TEXT NOT NULL,
    "tags" TEXT NULL,
    "url" TEXT NOT NULL, "mode" TEXT NOT NULL DEFAULT 'api', "service_urls" TEXT NULL,
    CONSTRAINT "fk_apprise_configs_notification_configs_notification_config_id" FOREIGN KEY ("notification_config_id") REFERENCES "notification_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "arr_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_arr_configs" PRIMARY KEY,
    "type" TEXT NOT NULL,
    "failed_import_max_strikes" INTEGER NOT NULL
);
INSERT INTO "arr_configs" VALUES('6096303A-399C-42B8-BE8F-60A02CEC5A51','radarr',-1);
INSERT INTO "arr_configs" VALUES('4FD2B82B-CFFD-4B41-BCC0-204058B1E459','lidarr',-1);
INSERT INTO "arr_configs" VALUES('0B38A68F-3D7B-4D98-AE96-115DA62D9AF2','sonarr',-1);
INSERT INTO "arr_configs" VALUES('013994EA-0A5E-4EED-91B7-271F494B6259','readarr',-1);
INSERT INTO "arr_configs" VALUES('A7363CA9-224A-46C1-9A94-EDDA11FDE7B2','whisparr',-1);
INSERT INTO "arr_configs" VALUES('3F6CD06A-98B4-45F1-8F0E-1C2D7A5B9E04','sportarr',-1);
INSERT INTO "arr_configs" VALUES('D7C2A7A5-6F31-4F0D-9C52-0C2B8C5B1A90','lazylibrarian',-1);
CREATE TABLE "arr_instances" (
    "id" TEXT NOT NULL CONSTRAINT "pk_arr_instances" PRIMARY KEY,
    "enabled" INTEGER NOT NULL,
    "arr_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "api_key" TEXT NOT NULL, "version" REAL NOT NULL DEFAULT 0, "external_url" TEXT NULL,
    CONSTRAINT "fk_arr_instances_arr_configs_arr_config_id" FOREIGN KEY ("arr_config_id") REFERENCES "arr_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "blacklist_sync_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_blacklist_sync_configs" PRIMARY KEY,
    "enabled" INTEGER NOT NULL,
    "cron_expression" TEXT NOT NULL,
    "blacklist_path" TEXT NULL
);
INSERT INTO "blacklist_sync_configs" VALUES('C60FE453-8161-4F15-A027-288DF774777F',0,'0 0 * * * ?',NULL);
CREATE TABLE "blacklist_sync_history" (
    "id" TEXT NOT NULL CONSTRAINT "pk_blacklist_sync_history" PRIMARY KEY,
    "hash" TEXT NOT NULL,
    "download_client_id" TEXT NOT NULL,
    CONSTRAINT "fk_blacklist_sync_history_download_clients_download_client_id" FOREIGN KEY ("download_client_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "content_blocker_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_content_blocker_configs" PRIMARY KEY,
    "cron_expression" TEXT NOT NULL,
    "delete_if_any_file_blocked" INTEGER NOT NULL,
    "delete_private" INTEGER NOT NULL,
    "enabled" INTEGER NOT NULL,
    "ignore_private" INTEGER NOT NULL,
    "ignored_downloads" TEXT NOT NULL,
    "lidarr_blocklist_path" TEXT NULL,
    "lidarr_blocklist_type" TEXT NOT NULL,
    "lidarr_enabled" INTEGER NOT NULL,
    "process_no_content_id" INTEGER NOT NULL,
    "radarr_blocklist_path" TEXT NULL,
    "radarr_blocklist_type" TEXT NOT NULL,
    "radarr_enabled" INTEGER NOT NULL,
    "readarr_blocklist_path" TEXT NULL,
    "readarr_blocklist_type" TEXT NOT NULL,
    "readarr_enabled" INTEGER NOT NULL,
    "sonarr_blocklist_path" TEXT NULL,
    "sonarr_blocklist_type" TEXT NOT NULL,
    "sonarr_enabled" INTEGER NOT NULL,
    "use_advanced_scheduling" INTEGER NOT NULL,
    "whisparr_blocklist_path" TEXT NULL,
    "whisparr_blocklist_type" TEXT NOT NULL,
    "whisparr_enabled" INTEGER NOT NULL
, "sportarr_blocklist_path" TEXT NULL, "sportarr_blocklist_type" TEXT NOT NULL DEFAULT '', "sportarr_enabled" INTEGER NOT NULL DEFAULT 0, "lazy_librarian_blocklist_path" TEXT NULL, "lazy_librarian_blocklist_type" TEXT NOT NULL DEFAULT '', "lazy_librarian_enabled" INTEGER NOT NULL DEFAULT 0);
INSERT INTO "content_blocker_configs" VALUES('B1C5F8D2-3A0E-4B6C-9F7E-8C1D2E3F4A5B','0/5 * * * * ?',0,0,0,0,'[]',NULL,'blacklist',0,0,NULL,'blacklist',0,NULL,'blacklist',0,NULL,'blacklist',0,0,NULL,'blacklist',0,NULL,'blacklist',0,NULL,'blacklist',0);
CREATE TABLE "dead_torrent_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_dead_torrent_configs" PRIMARY KEY,
    "download_client_config_id" TEXT NOT NULL,
    "enabled" INTEGER NOT NULL,
    "target_category" TEXT NOT NULL,
    "use_tag" INTEGER NOT NULL,
    "max_strikes" INTEGER NOT NULL,
    "categories" TEXT NOT NULL,
    CONSTRAINT "fk_dead_torrent_configs_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "deluge_seeding_rules" (
    "id" TEXT NOT NULL CONSTRAINT "pk_deluge_seeding_rules" PRIMARY KEY,
    "download_client_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "privacy_type" TEXT NOT NULL,
    "max_ratio" REAL NOT NULL,
    "min_seed_time" REAL NOT NULL,
    "max_seed_time" REAL NOT NULL,
    "delete_source_files" INTEGER NOT NULL, "categories" TEXT NOT NULL DEFAULT '[]', "priority" INTEGER NOT NULL DEFAULT 0, "tracker_patterns" TEXT NOT NULL DEFAULT '[]', "min_seeders" INTEGER NOT NULL DEFAULT 0, "action" TEXT NOT NULL DEFAULT 'delete',
    CONSTRAINT "fk_deluge_seeding_rules_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "discord_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_discord_configs" PRIMARY KEY,
    "notification_config_id" TEXT NOT NULL,
    "webhook_url" TEXT NOT NULL,
    "username" TEXT NOT NULL,
    "avatar_url" TEXT NOT NULL,
    CONSTRAINT "fk_discord_configs_notification_configs_notification_config_id" FOREIGN KEY ("notification_config_id") REFERENCES "notification_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "download_cleaner_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_download_cleaner_configs" PRIMARY KEY,
    "cron_expression" TEXT NOT NULL,
    "enabled" INTEGER NOT NULL,
    "ignored_downloads" TEXT NOT NULL,
    "use_advanced_scheduling" INTEGER NOT NULL
);
INSERT INTO "download_cleaner_configs" VALUES('EDB20D44-9D7B-478F-AEC5-93A803C26FB4','0 0 * * * ?',0,'[]',0);
CREATE TABLE "download_clients" (
    "id" TEXT NOT NULL CONSTRAINT "pk_download_clients" PRIMARY KEY,
    "enabled" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "type_name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "host" TEXT NULL,
    "username" TEXT NULL,
    "password" TEXT NULL,
    "url_base" TEXT NULL
, "external_url" TEXT NULL, "download_directory_source" TEXT NULL, "download_directory_target" TEXT NULL);
CREATE TABLE "general_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_general_configs" PRIMARY KEY,
    "auth_disable_auth_for_local_addresses" INTEGER NOT NULL,
    "auth_trust_forwarded_headers" INTEGER NOT NULL,
    "auth_trusted_networks" TEXT NOT NULL,
    "connectivity_check_enabled" INTEGER NOT NULL,
    "connectivity_check_urls" TEXT NOT NULL,
    "display_support_banner" INTEGER NOT NULL,
    "dry_run" INTEGER NOT NULL,
    "history_retention_days" INTEGER NOT NULL,
    "http_certificate_validation" TEXT NOT NULL,
    "http_max_retries" INTEGER NOT NULL,
    "http_send_user_agent" INTEGER NOT NULL,
    "http_timeout" INTEGER NOT NULL,
    "ignored_downloads" TEXT NOT NULL,
    "log_archive_enabled" INTEGER NOT NULL,
    "log_archive_retained_count" INTEGER NOT NULL,
    "log_archive_time_limit_hours" INTEGER NOT NULL,
    "log_level" TEXT NOT NULL,
    "log_retained_file_count" INTEGER NOT NULL,
    "log_rolling_size_mb" INTEGER NOT NULL,
    "log_time_limit_hours" INTEGER NOT NULL,
    "status_check_enabled" INTEGER NOT NULL,
    "strike_inactivity_window_hours" INTEGER NOT NULL
);
INSERT INTO "general_configs" VALUES('1490F450-1B29-4111-AB20-8A03DBD9D366',0,0,'',0,'[]',1,0,365,'enabled',0,0,100,'[]',1,60,720,'information',5,10,24,1,24);
CREATE TABLE "gotify_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_gotify_configs" PRIMARY KEY,
    "notification_config_id" TEXT NOT NULL,
    "server_url" TEXT NOT NULL,
    "application_token" TEXT NOT NULL,
    "priority" INTEGER NOT NULL,
    CONSTRAINT "fk_gotify_configs_notification_configs_notification_config_id" FOREIGN KEY ("notification_config_id") REFERENCES "notification_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "notifiarr_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_notifiarr_configs" PRIMARY KEY,
    "api_key" TEXT NOT NULL,
    "channel_id" TEXT NOT NULL,
    "notification_config_id" TEXT NOT NULL,
    CONSTRAINT "fk_notifiarr_configs_notification_configs_notification_config_id" FOREIGN KEY ("notification_config_id") REFERENCES "notification_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "notification_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_notification_configs" PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "is_enabled" INTEGER NOT NULL,
    "on_failed_import_strike" INTEGER NOT NULL,
    "on_stalled_strike" INTEGER NOT NULL,
    "on_slow_strike" INTEGER NOT NULL,
    "on_queue_item_deleted" INTEGER NOT NULL,
    "on_download_cleaned" INTEGER NOT NULL,
    "on_category_changed" INTEGER NOT NULL,
    "created_at" TEXT NOT NULL,
    "updated_at" TEXT NOT NULL
, "on_search_triggered" INTEGER NOT NULL DEFAULT 0, "on_search_item_grabbed" INTEGER NOT NULL DEFAULT 0, "on_download_stopped" INTEGER NOT NULL DEFAULT 0, "on_force_imported" INTEGER NOT NULL DEFAULT 0);
CREATE TABLE "ntfy_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_ntfy_configs" PRIMARY KEY,
    "notification_config_id" TEXT NOT NULL,
    "server_url" TEXT NOT NULL,
    "topics" TEXT NOT NULL,
    "authentication_type" TEXT NOT NULL,
    "username" TEXT NULL,
    "password" TEXT NULL,
    "access_token" TEXT NULL,
    "priority" TEXT NOT NULL,
    "tags" TEXT NOT NULL,
    CONSTRAINT "fk_ntfy_configs_notification_configs_notification_config_id" FOREIGN KEY ("notification_config_id") REFERENCES "notification_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "orphaned_files_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_orphaned_files_configs" PRIMARY KEY,
    "download_client_config_id" TEXT NOT NULL,
    "enabled" INTEGER NOT NULL,
    "scan_directories" TEXT NOT NULL,
    "orphaned_directory" TEXT NOT NULL,
    "exclude_patterns" TEXT NOT NULL,
    "min_file_age_hours" INTEGER NOT NULL,
    "purge_after_hours" INTEGER NULL,
    CONSTRAINT "fk_orphaned_files_configs_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "pushover_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_pushover_configs" PRIMARY KEY,
    "notification_config_id" TEXT NOT NULL,
    "api_token" TEXT NOT NULL,
    "user_key" TEXT NOT NULL,
    "devices" TEXT NOT NULL,
    "priority" TEXT NOT NULL,
    "sound" TEXT NULL,
    "retry" INTEGER NULL,
    "expire" INTEGER NULL,
    "tags" TEXT NOT NULL,
    CONSTRAINT "fk_pushover_configs_notification_configs_notification_config_id" FOREIGN KEY ("notification_config_id") REFERENCES "notification_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "q_bit_seeding_rules" (
    "id" TEXT NOT NULL CONSTRAINT "pk_q_bit_seeding_rules" PRIMARY KEY,
    "download_client_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "privacy_type" TEXT NOT NULL,
    "max_ratio" REAL NOT NULL,
    "min_seed_time" REAL NOT NULL,
    "max_seed_time" REAL NOT NULL,
    "delete_source_files" INTEGER NOT NULL, "categories" TEXT NOT NULL DEFAULT '[]', "priority" INTEGER NOT NULL DEFAULT 0, "tags_all" TEXT NOT NULL DEFAULT '[]', "tags_any" TEXT NOT NULL DEFAULT '[]', "tracker_patterns" TEXT NOT NULL DEFAULT '[]', "min_seeders" INTEGER NOT NULL DEFAULT 0, "max_inactive_days" REAL NOT NULL DEFAULT -1.0, "action" TEXT NOT NULL DEFAULT 'delete',
    CONSTRAINT "fk_q_bit_seeding_rules_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "queue_cleaner_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_queue_cleaner_configs" PRIMARY KEY,
    "cron_expression" TEXT NOT NULL,
    "downloading_metadata_max_strikes" INTEGER NOT NULL,
    "enabled" INTEGER NOT NULL,
    "failed_import_delete_private" INTEGER NOT NULL,
    "failed_import_ignore_private" INTEGER NOT NULL,
    "failed_import_max_strikes" INTEGER NOT NULL,
    "failed_import_pattern_mode" TEXT NOT NULL,
    "failed_import_patterns" TEXT NOT NULL,
    "failed_import_skip_if_not_found_in_client" INTEGER NOT NULL,
    "ignored_downloads" TEXT NOT NULL,
    "use_advanced_scheduling" INTEGER NOT NULL
, "process_no_content_id" INTEGER NOT NULL DEFAULT 0, "failed_import_change_category" INTEGER NOT NULL DEFAULT 0, "failed_import_force_import" INTEGER NOT NULL DEFAULT 0, "failed_import_force_import_max_tries" INTEGER NOT NULL DEFAULT 3);
INSERT INTO "queue_cleaner_configs" VALUES('098AE890-21DD-4A23-9BA8-ED5CE1AB4817','0 0/5 * * * ?',0,0,0,0,0,'include','[]',1,'[]',0,0,0,0,3);
CREATE TABLE "r_torrent_seeding_rules" (
    "id" TEXT NOT NULL CONSTRAINT "pk_r_torrent_seeding_rules" PRIMARY KEY,
    "download_client_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "privacy_type" TEXT NOT NULL,
    "max_ratio" REAL NOT NULL,
    "min_seed_time" REAL NOT NULL,
    "max_seed_time" REAL NOT NULL,
    "delete_source_files" INTEGER NOT NULL, "categories" TEXT NOT NULL DEFAULT '[]', "priority" INTEGER NOT NULL DEFAULT 0, "tracker_patterns" TEXT NOT NULL DEFAULT '[]', "action" TEXT NOT NULL DEFAULT 'delete',
    CONSTRAINT "fk_r_torrent_seeding_rules_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "seeker_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_seeker_configs" PRIMARY KEY,
    "post_release_grace_hours" INTEGER NOT NULL,
    "proactive_search_enabled" INTEGER NOT NULL,
    "search_enabled" INTEGER NOT NULL,
    "search_interval" INTEGER NOT NULL,
    "selection_strategy" TEXT NOT NULL,
    "use_round_robin" INTEGER NOT NULL
);
INSERT INTO "seeker_configs" VALUES('2A09AB33-47B4-4624-89C2-59F5A482DED5',6,0,1,10,'balancedweighted',1);
CREATE TABLE "seeker_instance_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_seeker_instance_configs" PRIMARY KEY,
    "arr_instance_id" TEXT NOT NULL,
    "enabled" INTEGER NOT NULL,
    "skip_tags" TEXT NOT NULL,
    "last_processed_at" TEXT NULL,
    "current_cycle_id" TEXT NOT NULL,
    "total_eligible_items" INTEGER NOT NULL,
    "active_download_limit" INTEGER NOT NULL,
    "min_cycle_time_days" INTEGER NOT NULL, "monitored_only" INTEGER NOT NULL DEFAULT 1, "use_cutoff" INTEGER NOT NULL DEFAULT 0, "use_custom_format_score" INTEGER NOT NULL DEFAULT 0, "ignore_struck_downloads" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT "fk_seeker_instance_configs_arr_instances_arr_instance_id" FOREIGN KEY ("arr_instance_id") REFERENCES "arr_instances" ("id") ON DELETE CASCADE
);
CREATE TABLE "slow_rules" (
    "id" TEXT NOT NULL CONSTRAINT "pk_slow_rules" PRIMARY KEY,
    "reset_strikes_on_progress" INTEGER NOT NULL,
    "max_time_hours" REAL NOT NULL,
    "min_speed" TEXT NOT NULL,
    "ignore_above_size" TEXT NULL,
    "queue_cleaner_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "enabled" INTEGER NOT NULL,
    "max_strikes" INTEGER NOT NULL,
    "privacy_type" TEXT NOT NULL,
    "min_completion_percentage" INTEGER NOT NULL,
    "max_completion_percentage" INTEGER NOT NULL,
    "delete_private_torrents_from_client" INTEGER NOT NULL, "change_category" INTEGER NOT NULL DEFAULT 0, "ignore_while_alt_speed_active" INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT "fk_slow_rules_queue_cleaner_configs_queue_cleaner_config_id" FOREIGN KEY ("queue_cleaner_config_id") REFERENCES "queue_cleaner_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "stall_rules" (
    "id" TEXT NOT NULL CONSTRAINT "pk_stall_rules" PRIMARY KEY,
    "reset_strikes_on_progress" INTEGER NOT NULL,
    "minimum_progress" TEXT NULL,
    "queue_cleaner_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "enabled" INTEGER NOT NULL,
    "max_strikes" INTEGER NOT NULL,
    "privacy_type" TEXT NOT NULL,
    "min_completion_percentage" INTEGER NOT NULL,
    "max_completion_percentage" INTEGER NOT NULL,
    "delete_private_torrents_from_client" INTEGER NOT NULL, "change_category" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT "fk_stall_rules_queue_cleaner_configs_queue_cleaner_config_id" FOREIGN KEY ("queue_cleaner_config_id") REFERENCES "queue_cleaner_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "telegram_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_telegram_configs" PRIMARY KEY,
    "notification_config_id" TEXT NOT NULL,
    "bot_token" TEXT NOT NULL,
    "chat_id" TEXT NOT NULL,
    "topic_id" TEXT NULL,
    "send_silently" INTEGER NOT NULL,
    CONSTRAINT "fk_telegram_configs_notification_configs_notification_config_id" FOREIGN KEY ("notification_config_id") REFERENCES "notification_configs" ("id") ON DELETE CASCADE
);
CREATE TABLE "transmission_seeding_rules" (
    "id" TEXT NOT NULL CONSTRAINT "pk_transmission_seeding_rules" PRIMARY KEY,
    "download_client_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "privacy_type" TEXT NOT NULL,
    "max_ratio" REAL NOT NULL,
    "min_seed_time" REAL NOT NULL,
    "max_seed_time" REAL NOT NULL,
    "delete_source_files" INTEGER NOT NULL, "categories" TEXT NOT NULL DEFAULT '[]', "priority" INTEGER NOT NULL DEFAULT 0, "tags_all" TEXT NOT NULL DEFAULT '[]', "tags_any" TEXT NOT NULL DEFAULT '[]', "tracker_patterns" TEXT NOT NULL DEFAULT '[]', "min_seeders" INTEGER NOT NULL DEFAULT 0, "action" TEXT NOT NULL DEFAULT 'delete',
    CONSTRAINT "fk_transmission_seeding_rules_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "u_torrent_seeding_rules" (
    "id" TEXT NOT NULL CONSTRAINT "pk_u_torrent_seeding_rules" PRIMARY KEY,
    "download_client_config_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "privacy_type" TEXT NOT NULL,
    "max_ratio" REAL NOT NULL,
    "min_seed_time" REAL NOT NULL,
    "max_seed_time" REAL NOT NULL,
    "delete_source_files" INTEGER NOT NULL, "categories" TEXT NOT NULL DEFAULT '[]', "priority" INTEGER NOT NULL DEFAULT 0, "tracker_patterns" TEXT NOT NULL DEFAULT '[]', "min_seeders" INTEGER NOT NULL DEFAULT 0, "action" TEXT NOT NULL DEFAULT 'delete',
    CONSTRAINT "fk_u_torrent_seeding_rules_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE TABLE "unlinked_configs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_unlinked_configs" PRIMARY KEY,
    "categories" TEXT NOT NULL,
    "download_client_config_id" TEXT NOT NULL,
    "enabled" INTEGER NOT NULL,
    "ignored_root_dirs" TEXT NOT NULL,
    "target_category" TEXT NOT NULL,
    "use_tag" INTEGER NOT NULL,
    CONSTRAINT "fk_unlinked_configs_download_clients_download_client_config_id" FOREIGN KEY ("download_client_config_id") REFERENCES "download_clients" ("id") ON DELETE CASCADE
);
CREATE INDEX "ix_arr_instances_arr_config_id" ON "arr_instances" ("arr_config_id");
CREATE UNIQUE INDEX "ix_notification_configs_name" ON "notification_configs" ("name");
CREATE UNIQUE INDEX "ix_notifiarr_configs_notification_config_id" ON "notifiarr_configs" ("notification_config_id");
CREATE UNIQUE INDEX "ix_apprise_configs_notification_config_id" ON "apprise_configs" ("notification_config_id");
CREATE UNIQUE INDEX "ix_ntfy_configs_notification_config_id" ON "ntfy_configs" ("notification_config_id");
CREATE INDEX "ix_blacklist_sync_history_download_client_id" ON "blacklist_sync_history" ("download_client_id");
CREATE INDEX "ix_blacklist_sync_history_hash" ON "blacklist_sync_history" ("hash");
CREATE UNIQUE INDEX "ix_blacklist_sync_history_hash_download_client_id" ON "blacklist_sync_history" ("hash", "download_client_id");
CREATE INDEX "ix_slow_rules_queue_cleaner_config_id" ON "slow_rules" ("queue_cleaner_config_id");
CREATE INDEX "ix_stall_rules_queue_cleaner_config_id" ON "stall_rules" ("queue_cleaner_config_id");
CREATE UNIQUE INDEX "ix_pushover_configs_notification_config_id" ON "pushover_configs" ("notification_config_id");
CREATE UNIQUE INDEX "ix_telegram_configs_notification_config_id" ON "telegram_configs" ("notification_config_id");
CREATE UNIQUE INDEX "ix_discord_configs_notification_config_id" ON "discord_configs" ("notification_config_id");
CREATE UNIQUE INDEX "ix_gotify_configs_notification_config_id" ON "gotify_configs" ("notification_config_id");
CREATE UNIQUE INDEX "ix_seeker_instance_configs_arr_instance_id" ON "seeker_instance_configs" ("arr_instance_id");
CREATE INDEX "ix_deluge_seeding_rules_download_client_config_id" ON "deluge_seeding_rules" ("download_client_config_id");
CREATE INDEX "ix_q_bit_seeding_rules_download_client_config_id" ON "q_bit_seeding_rules" ("download_client_config_id");
CREATE INDEX "ix_r_torrent_seeding_rules_download_client_config_id" ON "r_torrent_seeding_rules" ("download_client_config_id");
CREATE INDEX "ix_transmission_seeding_rules_download_client_config_id" ON "transmission_seeding_rules" ("download_client_config_id");
CREATE INDEX "ix_u_torrent_seeding_rules_download_client_config_id" ON "u_torrent_seeding_rules" ("download_client_config_id");
CREATE UNIQUE INDEX "ix_orphaned_files_configs_download_client_config_id" ON "orphaned_files_configs" ("download_client_config_id");
CREATE UNIQUE INDEX "ix_unlinked_configs_download_client_config_id" ON "unlinked_configs" ("download_client_config_id");
CREATE UNIQUE INDEX "ix_dead_torrent_configs_download_client_config_id" ON "dead_torrent_configs" ("download_client_config_id");
COMMIT;
-- database: events.db
BEGIN TRANSACTION;
CREATE TABLE "__EFMigrationsHistory" (
    "migration_id" TEXT NOT NULL CONSTRAINT "pk___ef_migrations_history" PRIMARY KEY,
    "product_version" TEXT NOT NULL
);
INSERT INTO "__EFMigrationsHistory" VALUES('20250614211246_InitialEvents','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251023105637_AddManualEvents','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20251220204209_AddStrikes','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260213090744_AddEventContextColumns','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260213160156_AddOnStrikeDeleteBehavior','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260214230732_AddDownloadItemStatuses','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260319195316_AddIsDryRun','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260324200744_AddSeeker','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260405174732_AddSearchEventData','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260614130440_ConvertDatesToDateTimeOffset','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260706084236_EventStreamRework','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260710110253_MoveSeekerStateToEvents','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260903130325_NormalizeDownloadHashCasing','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260908071938_AddEpisodeIdToSeekerCommandTracker','10.0.1');
CREATE TABLE "__EFMigrationsLock" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK___EFMigrationsLock" PRIMARY KEY,
    "Timestamp" TEXT NOT NULL
);
CREATE TABLE "custom_format_score_entries" (
    "id" TEXT NOT NULL CONSTRAINT "pk_custom_format_score_entries" PRIMARY KEY,
    "arr_instance_id" TEXT NOT NULL,
    "external_item_id" INTEGER NOT NULL,
    "episode_id" INTEGER NOT NULL,
    "item_type" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "file_id" INTEGER NOT NULL,
    "current_score" INTEGER NOT NULL,
    "cutoff_score" INTEGER NOT NULL,
    "quality_profile_name" TEXT NOT NULL,
    "is_monitored" INTEGER NOT NULL,
    "last_synced_at" TEXT NOT NULL,
    "last_upgraded_at" TEXT NULL
);
CREATE TABLE "custom_format_score_history" (
    "id" TEXT NOT NULL CONSTRAINT "pk_custom_format_score_history" PRIMARY KEY,
    "arr_instance_id" TEXT NOT NULL,
    "external_item_id" INTEGER NOT NULL,
    "episode_id" INTEGER NOT NULL,
    "item_type" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "score" INTEGER NOT NULL,
    "cutoff_score" INTEGER NOT NULL,
    "recorded_at" TEXT NOT NULL
);
CREATE TABLE "download_items" (
    "id" TEXT NOT NULL CONSTRAINT "pk_download_items" PRIMARY KEY,
    "download_id" TEXT NOT NULL,
    "title" TEXT NOT NULL
, "is_marked_for_removal" INTEGER NOT NULL DEFAULT 0, "is_removed" INTEGER NOT NULL DEFAULT 0, "is_returning" INTEGER NOT NULL DEFAULT 0);
CREATE TABLE "events" (
    "id" TEXT NOT NULL CONSTRAINT "pk_events" PRIMARY KEY,
    "arr_instance_id" TEXT NULL,
    "clean_reason" TEXT NULL,
    "cleaned_category" TEXT NULL,
    "completed_at" TEXT NULL,
    "cycle_id" TEXT NULL,
    "delete_reason" TEXT NULL,
    "download_client_id" TEXT NULL,
    "event_type" TEXT NOT NULL,
    "failed_import_reasons" TEXT NOT NULL,
    "grabbed_items" TEXT NOT NULL,
    "is_category_tag" INTEGER NULL,
    "is_dry_run" INTEGER NOT NULL,
    "item_hash" TEXT NULL,
    "item_title" TEXT NULL,
    "job_run_id" TEXT NULL,
    "message" TEXT NOT NULL,
    "new_category" TEXT NULL,
    "old_category" TEXT NULL,
    "remove_from_client" INTEGER NULL,
    "search_reason" TEXT NULL,
    "search_status" TEXT NULL,
    "search_type" TEXT NULL,
    "seed_ratio" REAL NULL,
    "seeding_time_hours" REAL NULL,
    "severity" TEXT NOT NULL,
    "strike_count" INTEGER NULL,
    "strike_id" TEXT NULL,
    "timestamp" TEXT NOT NULL,
    "tracking_id" TEXT NULL,
    CONSTRAINT "fk_events_job_runs_job_run_id" FOREIGN KEY ("job_run_id") REFERENCES "job_runs" ("id") ON DELETE SET NULL,
    CONSTRAINT "fk_events_strikes_strike_id" FOREIGN KEY ("strike_id") REFERENCES "strikes" ("id") ON DELETE SET NULL
);
CREATE TABLE "job_runs" (
    "id" TEXT NOT NULL CONSTRAINT "pk_job_runs" PRIMARY KEY,
    "type" TEXT NOT NULL,
    "started_at" TEXT NOT NULL,
    "completed_at" TEXT NULL,
    "status" TEXT NULL
);
CREATE TABLE "manual_events" (
    "id" TEXT NOT NULL CONSTRAINT "pk_manual_events" PRIMARY KEY,
    "resolved_at" TEXT NULL,
    "download_client_name" TEXT NULL,
    "download_client_type" TEXT NULL,
    "instance_type" TEXT NULL,
    "instance_url" TEXT NULL,
    "is_resolved" INTEGER NOT NULL,
    "job_run_id" TEXT NULL,
    "message" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "timestamp" TEXT NOT NULL, "is_dry_run" INTEGER NOT NULL DEFAULT 0, "item_hash" TEXT NULL, "item_title" TEXT NULL, "strike_count" INTEGER NULL, "type" TEXT NOT NULL DEFAULT '',
    CONSTRAINT "fk_manual_events_job_runs_job_run_id" FOREIGN KEY ("job_run_id") REFERENCES "job_runs" ("id")
);
CREATE TABLE "search_queue" (
    "id" TEXT NOT NULL CONSTRAINT "pk_search_queue" PRIMARY KEY,
    "arr_instance_id" TEXT NOT NULL,
    "item_id" INTEGER NOT NULL,
    "series_id" INTEGER NULL,
    "search_type" TEXT NULL,
    "title" TEXT NOT NULL,
    "created_at" TEXT NOT NULL
);
CREATE TABLE "seeker_command_trackers" (
    "id" TEXT NOT NULL CONSTRAINT "pk_seeker_command_trackers" PRIMARY KEY,
    "arr_instance_id" TEXT NOT NULL,
    "command_id" INTEGER NOT NULL,
    "event_id" TEXT NOT NULL,
    "external_item_id" INTEGER NOT NULL,
    "item_title" TEXT NOT NULL,
    "season_number" INTEGER NOT NULL,
    "created_at" TEXT NOT NULL,
    "status" TEXT NOT NULL
, "episode_id" INTEGER NOT NULL DEFAULT 0);
CREATE TABLE "seeker_history" (
    "id" TEXT NOT NULL CONSTRAINT "pk_seeker_history" PRIMARY KEY,
    "arr_instance_id" TEXT NOT NULL,
    "external_item_id" INTEGER NOT NULL,
    "item_type" TEXT NOT NULL,
    "season_number" INTEGER NOT NULL,
    "cycle_id" TEXT NOT NULL,
    "last_searched_at" TEXT NOT NULL,
    "item_title" TEXT NOT NULL,
    "search_count" INTEGER NOT NULL,
    "is_dry_run" INTEGER NOT NULL
);
CREATE TABLE "strikes" (
    "id" TEXT NOT NULL CONSTRAINT "pk_strikes" PRIMARY KEY,
    "created_at" TEXT NOT NULL,
    "download_item_id" TEXT NOT NULL,
    "job_run_id" TEXT NOT NULL,
    "last_downloaded_bytes" INTEGER NULL,
    "type" TEXT NOT NULL, "is_dry_run" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT "fk_strikes_download_items_download_item_id" FOREIGN KEY ("download_item_id") REFERENCES "download_items" ("id") ON DELETE CASCADE,
    CONSTRAINT "fk_strikes_job_runs_job_run_id" FOREIGN KEY ("job_run_id") REFERENCES "job_runs" ("id") ON DELETE CASCADE
);
CREATE INDEX "ix_job_runs_started_at" ON "job_runs" ("started_at" DESC);
CREATE INDEX "ix_job_runs_type" ON "job_runs" ("type");
CREATE INDEX "ix_manual_events_instance_type" ON "manual_events" ("instance_type");
CREATE INDEX "ix_manual_events_is_resolved" ON "manual_events" ("is_resolved");
CREATE INDEX "ix_manual_events_job_run_id" ON "manual_events" ("job_run_id");
CREATE INDEX "ix_manual_events_message" ON "manual_events" ("message");
CREATE INDEX "ix_manual_events_severity" ON "manual_events" ("severity");
CREATE INDEX "ix_manual_events_timestamp" ON "manual_events" ("timestamp" DESC);
CREATE INDEX "ix_strikes_created_at" ON "strikes" ("created_at");
CREATE INDEX "ix_strikes_download_item_id_type" ON "strikes" ("download_item_id", "type");
CREATE INDEX "ix_strikes_job_run_id" ON "strikes" ("job_run_id");
CREATE UNIQUE INDEX "ix_manual_events_type_item_hash" ON "manual_events" ("type", "item_hash") WHERE "is_resolved" = 0;
CREATE INDEX "ix_events_arr_instance_id" ON "events" ("arr_instance_id");
CREATE INDEX "ix_events_cycle_id" ON "events" ("cycle_id");
CREATE INDEX "ix_events_delete_reason" ON "events" ("delete_reason");
CREATE INDEX "ix_events_event_type" ON "events" ("event_type");
CREATE INDEX "ix_events_job_run_id" ON "events" ("job_run_id");
CREATE INDEX "ix_events_severity" ON "events" ("severity");
CREATE INDEX "ix_events_strike_id" ON "events" ("strike_id");
CREATE INDEX "ix_events_timestamp" ON "events" ("timestamp" DESC);
CREATE UNIQUE INDEX "ix_custom_format_score_entries_arr_instance_id_external_item_id_episode_id" ON "custom_format_score_entries" ("arr_instance_id", "external_item_id", "episode_id");
CREATE INDEX "ix_custom_format_score_entries_last_upgraded_at" ON "custom_format_score_entries" ("last_upgraded_at");
CREATE INDEX "ix_custom_format_score_history_arr_instance_id_external_item_id_episode_id" ON "custom_format_score_history" ("arr_instance_id", "external_item_id", "episode_id");
CREATE INDEX "ix_custom_format_score_history_recorded_at" ON "custom_format_score_history" ("recorded_at");
CREATE INDEX "ix_search_queue_arr_instance_id" ON "search_queue" ("arr_instance_id");
CREATE INDEX "ix_seeker_command_trackers_arr_instance_id" ON "seeker_command_trackers" ("arr_instance_id");
CREATE UNIQUE INDEX "ix_seeker_history_arr_instance_id_external_item_id_item_type_season_number_cycle_id" ON "seeker_history" ("arr_instance_id", "external_item_id", "item_type", "season_number", "cycle_id");
CREATE UNIQUE INDEX "ix_download_items_download_id" ON "download_items" ("download_id");
COMMIT;
-- database: users.db
BEGIN TRANSACTION;
CREATE TABLE "__EFMigrationsHistory" (
    "migration_id" TEXT NOT NULL CONSTRAINT "pk___ef_migrations_history" PRIMARY KEY,
    "product_version" TEXT NOT NULL
);
INSERT INTO "__EFMigrationsHistory" VALUES('20260215094545_Initial','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260312090408_AddOidcSupport','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260614115255_AddUserFeatureViews','10.0.1');
INSERT INTO "__EFMigrationsHistory" VALUES('20260614130445_ConvertDatesToDateTimeOffset','10.0.1');
CREATE TABLE "__EFMigrationsLock" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK___EFMigrationsLock" PRIMARY KEY,
    "Timestamp" TEXT NOT NULL
);
CREATE TABLE "recovery_codes" (
    "id" TEXT NOT NULL CONSTRAINT "pk_recovery_codes" PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "code_hash" TEXT NOT NULL,
    "is_used" INTEGER NOT NULL,
    "used_at" TEXT NULL,
    CONSTRAINT "fk_recovery_codes_users_user_id" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE "refresh_tokens" (
    "id" TEXT NOT NULL CONSTRAINT "pk_refresh_tokens" PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "token_hash" TEXT NOT NULL,
    "expires_at" TEXT NOT NULL,
    "created_at" TEXT NOT NULL,
    "revoked_at" TEXT NULL,
    CONSTRAINT "fk_refresh_tokens_users_user_id" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE "user_feature_views" (
    "id" TEXT NOT NULL CONSTRAINT "pk_user_feature_views" PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "feature_id" TEXT NOT NULL,
    "first_seen_at" TEXT NOT NULL,
    CONSTRAINT "fk_user_feature_views_users_user_id" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE "users" (
    "id" TEXT NOT NULL CONSTRAINT "pk_users" PRIMARY KEY,
    "username" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "totp_secret" TEXT NOT NULL,
    "totp_enabled" INTEGER NOT NULL,
    "plex_account_id" TEXT NULL,
    "plex_username" TEXT NULL,
    "plex_email" TEXT NULL,
    "plex_auth_token" TEXT NULL,
    "api_key" TEXT NOT NULL,
    "setup_completed" INTEGER NOT NULL,
    "failed_login_attempts" INTEGER NOT NULL,
    "lockout_end" TEXT NULL,
    "created_at" TEXT NOT NULL,
    "updated_at" TEXT NOT NULL
, "oidc_authorized_subject" TEXT NOT NULL DEFAULT '', "oidc_client_id" TEXT NOT NULL DEFAULT '', "oidc_client_secret" TEXT NOT NULL DEFAULT '', "oidc_enabled" INTEGER NOT NULL DEFAULT 0, "oidc_exclusive_mode" INTEGER NOT NULL DEFAULT 0, "oidc_issuer_url" TEXT NOT NULL DEFAULT '', "oidc_provider_name" TEXT NOT NULL DEFAULT '', "oidc_redirect_url" TEXT NOT NULL DEFAULT '', "oidc_scopes" TEXT NOT NULL DEFAULT '');
CREATE INDEX "ix_recovery_codes_user_id" ON "recovery_codes" ("user_id");
CREATE UNIQUE INDEX "ix_refresh_tokens_token_hash" ON "refresh_tokens" ("token_hash");
CREATE INDEX "ix_refresh_tokens_user_id" ON "refresh_tokens" ("user_id");
CREATE UNIQUE INDEX "ix_users_api_key" ON "users" ("api_key");
CREATE UNIQUE INDEX "ix_users_username" ON "users" ("username");
CREATE UNIQUE INDEX "ix_user_feature_views_user_id_feature_id" ON "user_feature_views" ("user_id", "feature_id");
COMMIT;
