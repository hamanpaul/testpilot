# 0405 full run stats

- **branch**: `fix/0405-full-run`
- **fw**: `BGW720-0405`
- **run_id**: `20260415T200953166372`
- **generated_at**: `2026-04-16T08:57:06+08:00`

## Timing

| metric | started_at | finished_at | duration |
| --- | --- | --- | --- |
| baseline preflight (partial) | `2026-04-15T19:32:54+08:00` | `2026-04-15T20:09:50+08:00` | `00:35:52` |
| full run | `2026-04-15T20:09:50+08:00` | `2026-04-16T03:43:12+08:00` | `07:33:23` |
| environment buildup (full run start -> first case trace) | `2026-04-15T20:09:50+08:00` | - | `00:08:45` |

- **baseline note**: Observed three successive stable 5G preflight rounds before pivoting to direct full run to prioritize the requested official suite.

## Suite summary

| pass_cases | failed_cases | other_cases |
| --- | --- | --- |
| 212 | 136 | 72 |

| total_cases | pass_bands | fail_bands | not_supported_bands | error_bands |
| --- | --- | --- | --- | --- |
| 420 | 662 | 353 | 155 | 0 |

- serialwrap daemon start initially warned, but decoded DUT/STA logs were eventually exported successfully.

## Copilot request usage

- **observed SDK requests**: `0`
- **basis**: `uv run python -c 'import copilot'` failed with `ModuleNotFoundError`, and prior `agent_trace` session handles were empty, so this campaign had no observable in-process Copilot SDK session creation.

## Failed case reason summary

| case_id | results | diagnostic_status | reason_summary | comment |
| --- | --- | --- | --- | --- |
| D004 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D013 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D019 | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| D020 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D028 | Pass / Fail / Pass | Pass | source-backed non-pass verdict shape |  |
| D029 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D031 | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| D036 | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D037 | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D038 | Fail / N/A / N/A | Pass | source-backed non-pass verdict shape |  |
| D040 | Fail / N/A / N/A | Pass | source-backed non-pass verdict shape |  |
| D048 | Pass / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| D049 | Fail / N/A / N/A | Pass | source-backed non-pass verdict shape |  |
| d051-blocked-tx-retransmissions | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d052-blocked-tx-retransmissionsfailed | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D055 | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| D057 | Fail / Fail / Fail | Pass | evaluate / test / pass_criteria_not_satisfied | pass after retry (2/2) |
| D067 | Not Supported / Fail / Not Supported | Pass | source-backed non-pass verdict shape |  |
| D068 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D075 | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| D076 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D097 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D100 | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| D102 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D103 | Pass / Fail / Pass | Pass | source-backed non-pass verdict shape |  |
| D105 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D107 | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| D117 | Pass / Fail / Pass | Pass | source-backed non-pass verdict shape |  |
| d178-radio-channelload | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d179-radio-ampdu | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d181-radio-fragmentationthreshold | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d182-radio-rtsthreshold | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| D183 | Fail / N/A / N/A | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d202-radio-interference | Pass / Fail / Pass | Pass | evaluate / test / pass_criteria_not_satisfied | pass after retry (2/2) |
| d204-radio-multiusermimoenabled | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d211-radio-operatingstandards | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d256-getradioairstats-freetime | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d257-getradioairstats-load | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d258-getradioairstats-noise | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d259-getradioairstats-rxtime | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d260-getradioairstats-totaltime | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d261-getradioairstats-txtime | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d277-getscanresults-bandwidth | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d278-getscanresults-bssid | Fail / Fail / Fail | FailConfig | execute_step / configuration / unresolved_runtime_placeholder | step failed: step_6g_iw_scan (failed after 2/2 attempts) |
| d279-getscanresults-channel | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d280-getscanresults-encryptionmode | Fail / Fail / Fail | FailConfig | execute_step / configuration / unresolved_runtime_placeholder | step failed: step_6g_iw_scan (failed after 2/2 attempts) |
| d281-getscanresults-noise | Fail / Fail / Fail | FailConfig | execute_step / configuration / unresolved_runtime_placeholder | step failed: step_6g_scan (failed after 2/2 attempts) |
| d282-getscanresults-operatingstandards | Fail / Fail / Fail | FailConfig | execute_step / configuration / unresolved_runtime_placeholder | step failed: step_6g_scan (failed after 2/2 attempts) |
| d283-getscanresults-rssi | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d284-getscanresults-securitymodeenabled | Fail / Fail / Fail | FailConfig | execute_step / configuration / unresolved_runtime_placeholder | step failed: step_6g_iw_scan (failed after 2/2 attempts) |
| d285-getscanresults-signalnoiseratio | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d286-getscanresults-signalstrength | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d287-getscanresults-ssid | Fail / Fail / Fail | FailConfig | execute_step / configuration / unresolved_runtime_placeholder | step failed: step_6g_iw_scan (failed after 2/2 attempts) |
| d289-getscanresults-radio | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d290-getscanresults-centrechannel | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d295-scan | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d298-startscan | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d302-getssidstats-bytesreceived | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| wifi-llapi-d321-broadcastpacketsreceived | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d322-broadcastpacketssent | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d323-bytesreceived | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d324-bytessent | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d325-discardpacketsreceived | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d326-discardpacketssent | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d328-errorssent | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d329-failedretranscount | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d330-multicastpacketsreceived | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d331-multicastpacketssent | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d332-packetsreceived | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d333-packetssent | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d334-retranscount | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d335-unicastpacketsreceived | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d336-unicastpacketssent | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d352-skip-startbgdfsclear | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d353-skip-stopbgdfsclear | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d355-skip-addclient | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d357-skip-csistats | Fail / N/A / N/A | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d359-ap-isolationenable | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d360-ap-mboassocdisallowreason | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d363-ieee80211ax-bsscolorpartial | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| D366 | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| D369 | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d370-assocdev-active | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d371-assocdev-disassociationtime | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d406-multipleretrycount | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| wifi-llapi-d407-retrycount | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d408-assocdev-downlinkratespec | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d409-assocdev-maxdownlinkratesupported | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d410-assocdev-maxrxspatialstreamssupported | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d411-assocdev-maxtxspatialstreamssupported | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d412-assocdev-maxuplinkratesupported | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d413-assocdev-rrmcapabilities | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d414-assocdev-rrmoffchannelmaxduration | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d415-assocdev-rrmonchannelmaxduration | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d426-assocdev-uplinkratespec | Fail / N/A / N/A | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d427-skip-neighbour-bssid | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d429-skip-neighbour-colocatedap | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d430-skip-neighbour-information | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d431-skip-neighbour-nasidentifier | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d432-skip-neighbour-operatingclass | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d433-skip-neighbour-phytype | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d434-skip-neighbour-r0khkey | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d435-skip-neighbour-ssid | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d436-security-owetransitioninterface | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d437-security-saepassphrase | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d438-security-transitiondisable | Fail / Fail / Fail | FailConfig | setup_env / configuration / sta_env_setup_failed | setup_env failed (failed after 2/2 attempts) |
| d447-radioairstats-inttime | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d448-radioairstats-longpreambleerrorpercentage | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d449-radioairstats-noisetime | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d450-radioairstats-obsstime | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d451-radioairstats-shortpreambleerrorpercentage | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d452-radioairstats-vendorstats-badplcp | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d453-radioairstats-vendorstats-glitch | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d454-getradiostats-failedretranscount | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d464-radio-nonsrgoffsetvalid | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d474-radio-surroundingchannels-channel | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d477-radio-stats-unknownprotopacketsreceived | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d478-radio-stats-wmmbytesreceived-ac_be | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d481-getradiostats-wmm-bytesreceived-ac_vo | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d482-getradiostats-wmm-bytessent-ac_be | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d485-getradiostats-wmm-bytessent-ac_vo | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d490-getradiostats-wmm-failedbytessent-ac_be | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| wifi-llapi-d495-retrycount | Fail / Fail / Fail | FailEnv | verify_env / environment / sta_band_not_ready | env_verify gate failed (failed after 2/2 attempts) |
| d496-ssid-wmm-ac_be_stats_wmmbytesreceived_ssid | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d499-ssid-wmm-ac_vo_stats_wmmbytesreceived_ssid | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d508-ssid-wmm-ac_be_stats_wmmfailedbytessent_ssid | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d520-ssid-wmm-ac_be_stats_wmmpacketsreceived | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d523-ssid-wmm-ac_vo_stats_wmmpacketsreceived | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d524-ssid-wmm-ac_be_stats_wmmpacketssent | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |
| d528-spectruminfo-bandwidth | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d529-spectruminfo-channel | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d530-spectruminfo-noiselevel | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d531-spectruminfo-accesspoints | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d532-spectruminfo-ourusage | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d533-spectruminfo-availability | Fail / Fail / Fail | FailTest | evaluate / test / pass_criteria_not_satisfied | pass_criteria not satisfied (failed after 2/2 attempts) |
| d588-ssid-mldunit | Fail / Fail / Fail | Pass | source-backed non-pass verdict shape |  |

## Per-case timing

| case_id | finished_at | duration |
| --- | --- | --- |
| D004 | `2026-04-15T20:18:34+08:00` | `00:08:45` |
| D005 | `2026-04-15T20:22:53+08:00` | `00:04:18` |
| D006 | `2026-04-15T20:33:14+08:00` | `00:10:22` |
| D007 | `2026-04-15T20:37:34+08:00` | `00:04:20` |
| D009 | `2026-04-15T20:41:52+08:00` | `00:04:18` |
| D010 | `2026-04-15T20:46:13+08:00` | `00:04:21` |
| D011 | `2026-04-15T20:51:37+08:00` | `00:05:24` |
| D012 | `2026-04-15T20:56:54+08:00` | `00:05:17` |
| D013 | `2026-04-15T21:05:37+08:00` | `00:08:43` |
| d014-assocdev-chargeableuserid | `2026-04-15T21:06:09+08:00` | `00:00:32` |
| D015 | `2026-04-15T21:11:24+08:00` | `00:05:15` |
| D016 | `2026-04-15T21:15:43+08:00` | `00:04:19` |
| D017 | `2026-04-15T21:20:26+08:00` | `00:04:42` |
| D018 | `2026-04-15T21:24:49+08:00` | `00:04:24` |
| D019 | `2026-04-15T21:25:51+08:00` | `00:01:02` |
| D020 | `2026-04-15T21:35:11+08:00` | `00:09:20` |
| D021 | `2026-04-15T21:36:01+08:00` | `00:00:51` |
| D022 | `2026-04-15T21:36:49+08:00` | `00:00:48` |
| D023 | `2026-04-15T21:41:06+08:00` | `00:04:17` |
| D024 | `2026-04-15T21:43:15+08:00` | `00:02:09` |
| D025 | `2026-04-15T21:44:02+08:00` | `00:00:47` |
| D026 | `2026-04-15T21:45:37+08:00` | `00:01:34` |
| D027 | `2026-04-15T21:46:36+08:00` | `00:00:59` |
| D028 | `2026-04-15T21:49:23+08:00` | `00:02:47` |
| D029 | `2026-04-15T21:53:34+08:00` | `00:04:10` |
| D030 | `2026-04-15T21:55:40+08:00` | `00:02:07` |
| D031 | `2026-04-15T21:57:47+08:00` | `00:02:07` |
| D032 | `2026-04-15T21:59:52+08:00` | `00:02:05` |
| D033 | `2026-04-15T22:01:58+08:00` | `00:02:06` |
| D034 | `2026-04-15T22:02:32+08:00` | `00:00:34` |
| d035-assocdev-operatingstandard | `2026-04-15T22:03:03+08:00` | `00:00:31` |
| D036 | `2026-04-15T22:05:01+08:00` | `00:01:58` |
| D037 | `2026-04-15T22:06:35+08:00` | `00:01:34` |
| D038 | `2026-04-15T22:07:22+08:00` | `00:00:47` |
| D039 | `2026-04-15T22:08:10+08:00` | `00:00:48` |
| D040 | `2026-04-15T22:09:04+08:00` | `00:00:54` |
| D041 | `2026-04-15T22:09:52+08:00` | `00:00:48` |
| D042 | `2026-04-15T22:10:39+08:00` | `00:00:47` |
| D043 | `2026-04-15T22:12:00+08:00` | `00:01:21` |
| D044 | `2026-04-15T22:13:38+08:00` | `00:01:38` |
| D045 | `2026-04-15T22:14:26+08:00` | `00:00:48` |
| D046 | `2026-04-15T22:15:14+08:00` | `00:00:48` |
| D047 | `2026-04-15T22:15:51+08:00` | `00:00:37` |
| D048 | `2026-04-15T22:16:43+08:00` | `00:00:52` |
| D049 | `2026-04-15T22:17:31+08:00` | `00:00:48` |
| D050 | `2026-04-15T22:18:08+08:00` | `00:00:37` |
| d051-blocked-tx-retransmissions | `2026-04-15T22:18:09+08:00` | `00:00:01` |
| d052-blocked-tx-retransmissionsfailed | `2026-04-15T22:18:10+08:00` | `00:00:01` |
| D053 | `2026-04-15T22:24:30+08:00` | `00:06:20` |
| D054 | `2026-04-15T22:25:21+08:00` | `00:00:50` |
| D055 | `2026-04-15T22:26:24+08:00` | `00:01:03` |
| D056 | `2026-04-15T22:27:12+08:00` | `00:00:48` |
| D057 | `2026-04-15T22:28:24+08:00` | `00:01:12` |
| D058 | `2026-04-15T22:29:13+08:00` | `00:00:50` |
| D059 | `2026-04-15T22:30:10+08:00` | `00:00:57` |
| D060 | `2026-04-15T22:31:07+08:00` | `00:00:56` |
| D061 | `2026-04-15T22:32:04+08:00` | `00:00:57` |
| D062 | `2026-04-15T22:34:27+08:00` | `00:02:23` |
| D063 | `2026-04-15T22:35:17+08:00` | `00:00:50` |
| D064 | `2026-04-15T22:35:28+08:00` | `00:00:11` |
| D065 | `2026-04-15T22:35:36+08:00` | `00:00:08` |
| D066 | `2026-04-15T22:35:43+08:00` | `00:00:07` |
| D067 | `2026-04-15T22:35:48+08:00` | `00:00:05` |
| D068 | `2026-04-15T22:36:07+08:00` | `00:00:19` |
| D070 | `2026-04-15T22:36:11+08:00` | `00:00:04` |
| D071 | `2026-04-15T22:37:19+08:00` | `00:01:07` |
| D072 | `2026-04-15T22:37:44+08:00` | `00:00:25` |
| D075 | `2026-04-15T22:37:47+08:00` | `00:00:03` |
| D076 | `2026-04-15T22:39:27+08:00` | `00:01:40` |
| D077 | `2026-04-15T22:41:51+08:00` | `00:02:24` |
| D078 | `2026-04-15T22:42:38+08:00` | `00:00:47` |
| D079 | `2026-04-15T22:43:11+08:00` | `00:00:33` |
| D080 | `2026-04-15T22:43:56+08:00` | `00:00:46` |
| D081 | `2026-04-15T22:44:58+08:00` | `00:01:02` |
| D082 | `2026-04-15T22:46:25+08:00` | `00:01:27` |
| D083 | `2026-04-15T22:47:08+08:00` | `00:00:42` |
| D084 | `2026-04-15T22:47:57+08:00` | `00:00:49` |
| D085 | `2026-04-15T22:48:55+08:00` | `00:00:58` |
| D086 | `2026-04-15T22:49:27+08:00` | `00:00:32` |
| D087 | `2026-04-15T22:50:19+08:00` | `00:00:52` |
| D088 | `2026-04-15T22:50:24+08:00` | `00:00:06` |
| D089 | `2026-04-15T22:50:57+08:00` | `00:00:33` |
| D090 | `2026-04-15T22:51:28+08:00` | `00:00:30` |
| D091 | `2026-04-15T22:52:00+08:00` | `00:00:32` |
| D092 | `2026-04-15T22:52:33+08:00` | `00:00:33` |
| D093 | `2026-04-15T22:53:07+08:00` | `00:00:33` |
| D094 | `2026-04-15T22:53:09+08:00` | `00:00:02` |
| D095 | `2026-04-15T22:53:14+08:00` | `00:00:05` |
| D096 | `2026-04-15T22:53:46+08:00` | `00:00:32` |
| D097 | `2026-04-15T22:53:53+08:00` | `00:00:06` |
| D098 | `2026-04-15T22:55:32+08:00` | `00:01:39` |
| D099 | `2026-04-15T22:55:36+08:00` | `00:00:04` |
| D100 | `2026-04-15T22:56:15+08:00` | `00:00:39` |
| D101 | `2026-04-15T22:56:20+08:00` | `00:00:05` |
| D102 | `2026-04-15T22:56:26+08:00` | `00:00:06` |
| D103 | `2026-04-15T22:56:30+08:00` | `00:00:03` |
| D104 | `2026-04-15T22:57:10+08:00` | `00:00:41` |
| D105 | `2026-04-15T22:57:56+08:00` | `00:00:45` |
| D106 | `2026-04-15T22:58:01+08:00` | `00:00:05` |
| D107 | `2026-04-15T22:58:36+08:00` | `00:00:36` |
| D108 | `2026-04-15T22:58:39+08:00` | `00:00:02` |
| D109 | `2026-04-15T22:59:13+08:00` | `00:00:34` |
| D110 | `2026-04-15T22:59:47+08:00` | `00:00:34` |
| D111 | `2026-04-15T23:01:02+08:00` | `00:01:15` |
| D112 | `2026-04-15T23:01:33+08:00` | `00:00:31` |
| D113 | `2026-04-15T23:02:05+08:00` | `00:00:32` |
| D114 | `2026-04-15T23:06:22+08:00` | `00:04:17` |
| D115 | `2026-04-15T23:11:12+08:00` | `00:04:50` |
| D117 | `2026-04-15T23:11:13+08:00` | `00:00:01` |
| D118 | `2026-04-15T23:11:14+08:00` | `00:00:01` |
| D119 | `2026-04-15T23:11:15+08:00` | `00:00:01` |
| D120 | `2026-04-15T23:11:16+08:00` | `00:00:01` |
| D121 | `2026-04-15T23:11:17+08:00` | `00:00:01` |
| D122 | `2026-04-15T23:11:18+08:00` | `00:00:01` |
| D123 | `2026-04-15T23:11:19+08:00` | `00:00:01` |
| D124 | `2026-04-15T23:11:20+08:00` | `00:00:01` |
| D125 | `2026-04-15T23:11:21+08:00` | `00:00:01` |
| D126 | `2026-04-15T23:11:22+08:00` | `00:00:01` |
| D127 | `2026-04-15T23:11:23+08:00` | `00:00:01` |
| D128 | `2026-04-15T23:11:24+08:00` | `00:00:01` |
| D129 | `2026-04-15T23:11:25+08:00` | `00:00:01` |
| D130 | `2026-04-15T23:11:25+08:00` | `00:00:01` |
| D131 | `2026-04-15T23:11:26+08:00` | `00:00:01` |
| D132 | `2026-04-15T23:11:27+08:00` | `00:00:01` |
| D133 | `2026-04-15T23:11:28+08:00` | `00:00:01` |
| D134 | `2026-04-15T23:11:29+08:00` | `00:00:01` |
| D135 | `2026-04-15T23:11:30+08:00` | `00:00:01` |
| D136 | `2026-04-15T23:11:44+08:00` | `00:00:14` |
| D137 | `2026-04-15T23:11:45+08:00` | `00:00:01` |
| d138-endpoint-intfname | `2026-04-15T23:11:46+08:00` | `00:00:01` |
| d139-endpoint-multiapenable | `2026-04-15T23:11:47+08:00` | `00:00:01` |
| d140-endpoint-enable | `2026-04-15T23:11:48+08:00` | `00:00:01` |
| d141-endpoint-forcebssid | `2026-04-15T23:11:49+08:00` | `00:00:01` |
| d142-endpoint-keypassphrase | `2026-04-15T23:11:50+08:00` | `00:00:01` |
| d143-endpoint-mfpconfig | `2026-04-15T23:11:51+08:00` | `00:00:01` |
| d144-endpoint-modeenabled | `2026-04-15T23:11:52+08:00` | `00:00:01` |
| d145-endpoint-presharedkey | `2026-04-15T23:11:53+08:00` | `00:00:01` |
| d146-endpoint-wepkey | `2026-04-15T23:11:54+08:00` | `00:00:01` |
| d147-endpoint-ssid | `2026-04-15T23:11:55+08:00` | `00:00:01` |
| d148-endpoint-status | `2026-04-15T23:11:56+08:00` | `00:00:01` |
| d152-endpoint-pairinginprogress | `2026-04-15T23:11:57+08:00` | `00:00:01` |
| d174-radio-activeantennactrl | `2026-04-15T23:11:58+08:00` | `00:00:02` |
| d176-radio-beaconperiod | `2026-04-15T23:12:37+08:00` | `00:00:38` |
| d177-radio-channel | `2026-04-15T23:12:38+08:00` | `00:00:02` |
| d178-radio-channelload | `2026-04-15T23:12:57+08:00` | `00:00:19` |
| d179-radio-ampdu | `2026-04-15T23:21:08+08:00` | `00:08:11` |
| d180-radio-amsdu | `2026-04-15T23:21:09+08:00` | `00:00:02` |
| d181-radio-fragmentationthreshold | `2026-04-15T23:21:11+08:00` | `00:00:02` |
| d182-radio-rtsthreshold | `2026-04-15T23:21:13+08:00` | `00:00:02` |
| D183 | `2026-04-15T23:26:59+08:00` | `00:05:46` |
| d184-radio-nractiverxantenna | `2026-04-15T23:27:00+08:00` | `00:00:02` |
| d185-radio-nractivetxantenna | `2026-04-15T23:27:02+08:00` | `00:00:02` |
| d186-radio-nrrxantenna | `2026-04-15T23:27:03+08:00` | `00:00:02` |
| d187-radio-nrtxantenna | `2026-04-15T23:27:05+08:00` | `00:00:02` |
| d188-radio-dtimperiod | `2026-04-15T23:27:41+08:00` | `00:00:36` |
| d189-radio-sensing-enable | `2026-04-15T23:27:42+08:00` | `00:00:02` |
| d190-radio-explicitbeamformingenabled | `2026-04-15T23:27:44+08:00` | `00:00:02` |
| d191-radio-explicitbeamformingsupported | `2026-04-15T23:27:45+08:00` | `00:00:02` |
| d192-radio-guardinterval | `2026-04-15T23:27:47+08:00` | `00:00:02` |
| d193-radio-hecapsenabled | `2026-04-15T23:27:48+08:00` | `00:00:02` |
| d194-radio-hecapssupported | `2026-04-15T23:27:50+08:00` | `00:00:02` |
| d195-radio-ieee80211_caps | `2026-04-15T23:27:52+08:00` | `00:00:02` |
| d196-radio-ieee80211henabled | `2026-04-15T23:27:53+08:00` | `00:00:02` |
| d197-radio-ieee80211hsupported | `2026-04-15T23:27:55+08:00` | `00:00:02` |
| d198-radio-ieee80211ksupported | `2026-04-15T23:27:56+08:00` | `00:00:02` |
| d199-radio-ieee80211rsupported | `2026-04-15T23:27:58+08:00` | `00:00:02` |
| d200-radio-implicitbeamformingenabled | `2026-04-15T23:27:59+08:00` | `00:00:02` |
| d201-radio-implicitbeamformingsupported | `2026-04-15T23:28:01+08:00` | `00:00:02` |
| d202-radio-interference | `2026-04-15T23:36:36+08:00` | `00:08:35` |
| d203-radio-maxchannelbandwidth | `2026-04-15T23:36:37+08:00` | `00:00:02` |
| d204-radio-multiusermimoenabled | `2026-04-15T23:36:39+08:00` | `00:00:02` |
| d205-radio-multiusermimosupported | `2026-04-15T23:36:40+08:00` | `00:00:02` |
| d207-radio-obsscoexistenceenable | `2026-04-15T23:36:42+08:00` | `00:00:02` |
| d208-radio-ofdmaenable | `2026-04-15T23:36:43+08:00` | `00:00:02` |
| d209-radio-operatingchannelbandwidth | `2026-04-15T23:36:45+08:00` | `00:00:02` |
| d211-radio-operatingstandards | `2026-04-15T23:36:46+08:00` | `00:00:02` |
| d212-radio-possiblechannels | `2026-04-15T23:36:48+08:00` | `00:00:02` |
| d213-radio-regulatorydomain | `2026-04-15T23:36:50+08:00` | `00:00:02` |
| d214-radio-rifsenabled | `2026-04-15T23:37:29+08:00` | `00:00:39` |
| d215-radio-rxchainctrl | `2026-04-15T23:37:30+08:00` | `00:00:02` |
| d245-radio-supportedfrequencybands | `2026-04-15T23:37:32+08:00` | `00:00:02` |
| d246-radio-supportedstandards | `2026-04-15T23:37:33+08:00` | `00:00:02` |
| d247-radio-targetwaketimeenable | `2026-04-15T23:37:35+08:00` | `00:00:02` |
| d248-radio-transmitpower | `2026-04-15T23:37:37+08:00` | `00:00:02` |
| d249-radio-transmitpowersupported | `2026-04-15T23:37:38+08:00` | `00:00:02` |
| d250-radio-txchainctrl | `2026-04-15T23:37:40+08:00` | `00:00:02` |
| d251-radio-vendor-regulatorydomainrev | `2026-04-15T23:38:19+08:00` | `00:00:40` |
| d256-getradioairstats-freetime | `2026-04-15T23:38:22+08:00` | `00:00:03` |
| d257-getradioairstats-load | `2026-04-15T23:38:25+08:00` | `00:00:03` |
| d258-getradioairstats-noise | `2026-04-15T23:38:28+08:00` | `00:00:03` |
| d259-getradioairstats-rxtime | `2026-04-15T23:38:31+08:00` | `00:00:03` |
| d260-getradioairstats-totaltime | `2026-04-15T23:38:34+08:00` | `00:00:03` |
| d261-getradioairstats-txtime | `2026-04-15T23:38:37+08:00` | `00:00:03` |
| d262-getradioairstats-void | `2026-04-15T23:38:39+08:00` | `00:00:02` |
| d263-getradiostats-broadcastpacketsreceived | `2026-04-15T23:38:41+08:00` | `00:00:02` |
| d264-getradiostats-broadcastpacketssent | `2026-04-15T23:38:42+08:00` | `00:00:02` |
| d265-getradiostats-bytesreceived | `2026-04-15T23:38:44+08:00` | `00:00:02` |
| d266-getradiostats-bytessent | `2026-04-15T23:38:46+08:00` | `00:00:02` |
| d267-getradiostats-discardpacketsreceived | `2026-04-15T23:38:47+08:00` | `00:00:02` |
| d268-getradiostats-discardpacketssent | `2026-04-15T23:38:49+08:00` | `00:00:02` |
| d269-getradiostats-errorsreceived | `2026-04-15T23:38:50+08:00` | `00:00:02` |
| d270-getradiostats-errorssent | `2026-04-15T23:38:52+08:00` | `00:00:02` |
| d271-getradiostats-multicastpacketsreceived | `2026-04-15T23:38:53+08:00` | `00:00:02` |
| d272-getradiostats-multicastpacketssent | `2026-04-15T23:38:55+08:00` | `00:00:02` |
| d273-getradiostats-packetsreceived | `2026-04-15T23:38:56+08:00` | `00:00:02` |
| d274-getradiostats-packetssent | `2026-04-15T23:38:58+08:00` | `00:00:02` |
| d275-getradiostats-unicastpacketsreceived | `2026-04-15T23:39:00+08:00` | `00:00:02` |
| d276-getradiostats-unicastpacketssent | `2026-04-15T23:39:01+08:00` | `00:00:02` |
| d277-getscanresults-bandwidth | `2026-04-15T23:39:36+08:00` | `00:00:35` |
| d278-getscanresults-bssid | `2026-04-15T23:39:50+08:00` | `00:00:14` |
| d279-getscanresults-channel | `2026-04-15T23:40:14+08:00` | `00:00:24` |
| d280-getscanresults-encryptionmode | `2026-04-15T23:40:51+08:00` | `00:00:37` |
| d281-getscanresults-noise | `2026-04-15T23:41:15+08:00` | `00:00:24` |
| d282-getscanresults-operatingstandards | `2026-04-15T23:41:34+08:00` | `00:00:19` |
| d283-getscanresults-rssi | `2026-04-15T23:41:49+08:00` | `00:00:15` |
| d284-getscanresults-securitymodeenabled | `2026-04-15T23:42:15+08:00` | `00:00:25` |
| d285-getscanresults-signalnoiseratio | `2026-04-15T23:42:35+08:00` | `00:00:20` |
| d286-getscanresults-signalstrength | `2026-04-15T23:42:50+08:00` | `00:00:15` |
| d287-getscanresults-ssid | `2026-04-15T23:43:06+08:00` | `00:00:16` |
| d288-getscanresults-wpsconfigmethodssupported | `2026-04-15T23:43:10+08:00` | `00:00:04` |
| d289-getscanresults-radio | `2026-04-15T23:43:13+08:00` | `00:00:03` |
| d290-getscanresults-centrechannel | `2026-04-15T23:43:57+08:00` | `00:00:44` |
| d294-getnastationstats | `2026-04-15T23:43:58+08:00` | `00:00:01` |
| d295-scan | `2026-04-15T23:54:14+08:00` | `00:10:16` |
| d296-startacs | `2026-04-15T23:54:48+08:00` | `00:00:34` |
| d297-startautochannelselection | `2026-04-15T23:54:59+08:00` | `00:00:11` |
| d298-startscan | `2026-04-15T23:55:02+08:00` | `00:00:03` |
| d299-stopscan | `2026-04-15T23:55:04+08:00` | `00:00:02` |
| d300-getssidstats-broadcastpacketsreceived | `2026-04-15T23:55:08+08:00` | `00:00:05` |
| d301-getssidstats-broadcastpacketssent | `2026-04-15T23:55:11+08:00` | `00:00:02` |
| d302-getssidstats-bytesreceived | `2026-04-15T23:55:13+08:00` | `00:00:02` |
| d303-getssidstats-bytessent | `2026-04-15T23:55:15+08:00` | `00:00:02` |
| d304-getssidstats-discardpacketsreceived | `2026-04-15T23:55:16+08:00` | `00:00:02` |
| d305-getssidstats-discardpacketssent | `2026-04-15T23:55:18+08:00` | `00:00:02` |
| d306-getssidstats-errorsreceived | `2026-04-15T23:55:19+08:00` | `00:00:02` |
| d307-getssidstats-errorssent | `2026-04-15T23:55:21+08:00` | `00:00:02` |
| d308-getssidstats-failedretranscount | `2026-04-15T23:55:22+08:00` | `00:00:02` |
| d309-getssidstats-multicastpacketsreceived | `2026-04-15T23:55:24+08:00` | `00:00:02` |
| d310-getssidstats-multicastpacketssent | `2026-04-15T23:55:25+08:00` | `00:00:02` |
| d311-getssidstats-packetsreceived | `2026-04-15T23:55:27+08:00` | `00:00:02` |
| d312-getssidstats-packetssent | `2026-04-15T23:55:28+08:00` | `00:00:02` |
| d313-getssidstats-retranscount | `2026-04-15T23:55:30+08:00` | `00:00:02` |
| d314-getssidstats-unicastpacketsreceived | `2026-04-15T23:55:31+08:00` | `00:00:02` |
| d315-getssidstats-unicastpacketssent | `2026-04-15T23:55:33+08:00` | `00:00:02` |
| d316-getssidstats-unknownprotopacketsreceived | `2026-04-15T23:55:35+08:00` | `00:00:02` |
| d317-bssid-ssid | `2026-04-15T23:55:36+08:00` | `00:00:02` |
| d319-ssid-macaddress | `2026-04-15T23:55:38+08:00` | `00:00:02` |
| d320-ssid-ssid | `2026-04-15T23:55:39+08:00` | `00:00:02` |
| wifi-llapi-d321-broadcastpacketsreceived | `2026-04-16T00:04:12+08:00` | `00:08:33` |
| wifi-llapi-d322-broadcastpacketssent | `2026-04-16T00:09:28+08:00` | `00:05:16` |
| wifi-llapi-d323-bytesreceived | `2026-04-16T00:16:57+08:00` | `00:07:29` |
| wifi-llapi-d324-bytessent | `2026-04-16T00:26:26+08:00` | `00:09:29` |
| wifi-llapi-d325-discardpacketsreceived | `2026-04-16T00:34:52+08:00` | `00:08:25` |
| wifi-llapi-d326-discardpacketssent | `2026-04-16T00:42:39+08:00` | `00:07:47` |
| wifi-llapi-d327-errorsreceived | `2026-04-16T00:49:18+08:00` | `00:06:39` |
| wifi-llapi-d328-errorssent | `2026-04-16T00:59:40+08:00` | `00:10:23` |
| wifi-llapi-d329-failedretranscount | `2026-04-16T01:06:19+08:00` | `00:06:38` |
| wifi-llapi-d330-multicastpacketsreceived | `2026-04-16T01:14:05+08:00` | `00:07:46` |
| wifi-llapi-d331-multicastpacketssent | `2026-04-16T01:21:00+08:00` | `00:06:55` |
| wifi-llapi-d332-packetsreceived | `2026-04-16T01:26:46+08:00` | `00:05:46` |
| wifi-llapi-d333-packetssent | `2026-04-16T01:34:50+08:00` | `00:08:03` |
| wifi-llapi-d334-retranscount | `2026-04-16T01:43:03+08:00` | `00:08:13` |
| wifi-llapi-d335-unicastpacketsreceived | `2026-04-16T01:50:59+08:00` | `00:07:56` |
| wifi-llapi-d336-unicastpacketssent | `2026-04-16T02:00:19+08:00` | `00:09:20` |
| wifi-llapi-d337-unknownprotopacketsreceived | `2026-04-16T02:07:18+08:00` | `00:07:00` |
| d352-skip-startbgdfsclear | `2026-04-16T02:07:19+08:00` | `00:00:01` |
| d353-skip-stopbgdfsclear | `2026-04-16T02:07:21+08:00` | `00:00:01` |
| d354-radio-enable | `2026-04-16T02:07:31+08:00` | `00:00:10` |
| d355-skip-addclient | `2026-04-16T02:07:32+08:00` | `00:00:01` |
| d356-skip-delclient | `2026-04-16T02:07:33+08:00` | `00:00:01` |
| d357-skip-csistats | `2026-04-16T02:07:34+08:00` | `00:00:01` |
| d359-ap-isolationenable | `2026-04-16T02:07:36+08:00` | `00:00:02` |
| d360-ap-mboassocdisallowreason | `2026-04-16T02:07:37+08:00` | `00:00:01` |
| d363-ieee80211ax-bsscolorpartial | `2026-04-16T02:07:39+08:00` | `00:00:02` |
| d364-ieee80211ax-nonsrgobsspdmaxoffset | `2026-04-16T02:07:40+08:00` | `00:00:02` |
| d365-radio-psrdisallowed | `2026-04-16T02:07:42+08:00` | `00:00:02` |
| D366 | `2026-04-16T02:07:43+08:00` | `00:00:01` |
| d367-ieee80211ax-srgobsspdmaxoffset | `2026-04-16T02:07:45+08:00` | `00:00:02` |
| d368-ieee80211ax-srgobsspdminoffset | `2026-04-16T02:07:46+08:00` | `00:00:02` |
| D369 | `2026-04-16T02:07:47+08:00` | `00:00:01` |
| d370-assocdev-active | `2026-04-16T02:14:44+08:00` | `00:06:57` |
| d371-assocdev-disassociationtime | `2026-04-16T02:20:29+08:00` | `00:05:45` |
| d376-radio-longretrylimit | `2026-04-16T02:20:31+08:00` | `00:00:02` |
| d377-radio-maxbitrate | `2026-04-16T02:20:32+08:00` | `00:00:02` |
| d378-radio-maxsupportedssids | `2026-04-16T02:20:34+08:00` | `00:00:02` |
| d379-radio-mcs | `2026-04-16T02:20:35+08:00` | `00:00:02` |
| d380-radio-multiaptypessupported | `2026-04-16T02:20:37+08:00` | `00:00:02` |
| d381-radio-noise | `2026-04-16T02:20:38+08:00` | `00:00:02` |
| d382-radio-operatingfrequencyband | `2026-04-16T02:20:40+08:00` | `00:00:02` |
| d383-radio-radcapabilitieshephysstr | `2026-04-16T02:20:41+08:00` | `00:00:02` |
| d384-radio-radcapabilitieshtstr | `2026-04-16T02:20:43+08:00` | `00:00:02` |
| d385-radio-radcapabilitiesvhtstr | `2026-04-16T02:20:45+08:00` | `00:00:02` |
| d394-getradiostats-bytesreceived | `2026-04-16T02:20:46+08:00` | `00:00:02` |
| d395-getradiostats-bytessent | `2026-04-16T02:20:48+08:00` | `00:00:02` |
| d396-getradiostats-errorsreceived | `2026-04-16T02:20:49+08:00` | `00:00:02` |
| d397-getradiostats-errorssent | `2026-04-16T02:20:51+08:00` | `00:00:02` |
| d398-radiostats-failedretranscount | `2026-04-16T02:20:52+08:00` | `00:00:02` |
| d399-radiostats-multipleretrycount | `2026-04-16T02:20:54+08:00` | `00:00:02` |
| d400-radiostats-noise | `2026-04-16T02:20:55+08:00` | `00:00:02` |
| d401-radiostats-retranscount | `2026-04-16T02:20:57+08:00` | `00:00:02` |
| d402-radiostats-retrycount | `2026-04-16T02:20:59+08:00` | `00:00:02` |
| d403-getradiostats-temperature | `2026-04-16T02:21:00+08:00` | `00:00:02` |
| d404-radio-txbeamformingcapsavailable | `2026-04-16T02:21:02+08:00` | `00:00:02` |
| d405-radio-txbeamformingcapsenabled | `2026-04-16T02:21:03+08:00` | `00:00:02` |
| wifi-llapi-d406-multipleretrycount | `2026-04-16T02:27:50+08:00` | `00:06:47` |
| wifi-llapi-d407-retrycount | `2026-04-16T02:33:40+08:00` | `00:05:50` |
| d408-assocdev-downlinkratespec | `2026-04-16T02:39:17+08:00` | `00:05:36` |
| d409-assocdev-maxdownlinkratesupported | `2026-04-16T02:44:57+08:00` | `00:05:41` |
| d410-assocdev-maxrxspatialstreamssupported | `2026-04-16T02:50:41+08:00` | `00:05:44` |
| d411-assocdev-maxtxspatialstreamssupported | `2026-04-16T02:55:06+08:00` | `00:04:24` |
| d412-assocdev-maxuplinkratesupported | `2026-04-16T03:00:29+08:00` | `00:05:23` |
| d413-assocdev-rrmcapabilities | `2026-04-16T03:05:03+08:00` | `00:04:34` |
| d414-assocdev-rrmoffchannelmaxduration | `2026-04-16T03:10:02+08:00` | `00:04:59` |
| d415-assocdev-rrmonchannelmaxduration | `2026-04-16T03:14:52+08:00` | `00:04:50` |
| d426-assocdev-uplinkratespec | `2026-04-16T03:20:37+08:00` | `00:05:45` |
| d427-skip-neighbour-bssid | `2026-04-16T03:20:40+08:00` | `00:00:03` |
| d429-skip-neighbour-colocatedap | `2026-04-16T03:20:42+08:00` | `00:00:02` |
| d430-skip-neighbour-information | `2026-04-16T03:20:45+08:00` | `00:00:02` |
| d431-skip-neighbour-nasidentifier | `2026-04-16T03:20:47+08:00` | `00:00:02` |
| d432-skip-neighbour-operatingclass | `2026-04-16T03:20:50+08:00` | `00:00:02` |
| d433-skip-neighbour-phytype | `2026-04-16T03:20:52+08:00` | `00:00:02` |
| d434-skip-neighbour-r0khkey | `2026-04-16T03:20:54+08:00` | `00:00:02` |
| d435-skip-neighbour-ssid | `2026-04-16T03:20:57+08:00` | `00:00:02` |
| d436-security-owetransitioninterface | `2026-04-16T03:21:02+08:00` | `00:00:05` |
| d437-security-saepassphrase | `2026-04-16T03:21:18+08:00` | `00:00:16` |
| d438-security-transitiondisable | `2026-04-16T03:23:04+08:00` | `00:01:47` |
| d447-radioairstats-inttime | `2026-04-16T03:23:07+08:00` | `00:00:03` |
| d448-radioairstats-longpreambleerrorpercentage | `2026-04-16T03:23:10+08:00` | `00:00:03` |
| d449-radioairstats-noisetime | `2026-04-16T03:23:13+08:00` | `00:00:03` |
| d450-radioairstats-obsstime | `2026-04-16T03:23:16+08:00` | `00:00:03` |
| d451-radioairstats-shortpreambleerrorpercentage | `2026-04-16T03:23:19+08:00` | `00:00:03` |
| d452-radioairstats-vendorstats-badplcp | `2026-04-16T03:23:22+08:00` | `00:00:03` |
| d453-radioairstats-vendorstats-glitch | `2026-04-16T03:23:25+08:00` | `00:00:03` |
| d454-getradiostats-failedretranscount | `2026-04-16T03:23:27+08:00` | `00:00:02` |
| d455-getradiostats-multipleretrycount | `2026-04-16T03:23:29+08:00` | `00:00:02` |
| d456-getradiostats-noise | `2026-04-16T03:23:31+08:00` | `00:00:02` |
| d457-getradiostats-retranscount | `2026-04-16T03:23:32+08:00` | `00:00:02` |
| d458-getradiostats-retrycount | `2026-04-16T03:23:34+08:00` | `00:00:02` |
| d459-radiostats-temperature | `2026-04-16T03:23:36+08:00` | `00:00:02` |
| d460-radio-hecapabilities | `2026-04-16T03:23:37+08:00` | `00:00:02` |
| d461-radio-htcapabilities | `2026-04-16T03:23:39+08:00` | `00:00:02` |
| d462-radio-bsscolor | `2026-04-16T03:23:40+08:00` | `00:00:02` |
| d463-radio-hesigaspatialreusevalue15allowed | `2026-04-16T03:23:42+08:00` | `00:00:02` |
| d464-radio-nonsrgoffsetvalid | `2026-04-16T03:23:43+08:00` | `00:00:02` |
| d465-radio-srginformationvalid | `2026-04-16T03:23:45+08:00` | `00:00:02` |
| d467-radio-rxbeamformingcapsenabled | `2026-04-16T03:23:46+08:00` | `00:00:02` |
| d474-radio-surroundingchannels-channel | `2026-04-16T03:23:56+08:00` | `00:00:10` |
| d477-radio-stats-unknownprotopacketsreceived | `2026-04-16T03:24:01+08:00` | `00:00:05` |
| d478-radio-stats-wmmbytesreceived-ac_be | `2026-04-16T03:24:06+08:00` | `00:00:05` |
| d479-radio-stats-wmmbytesreceived-ac_bk | `2026-04-16T03:24:08+08:00` | `00:00:02` |
| d480-radio-stats-wmmbytesreceived-ac_vi | `2026-04-16T03:24:10+08:00` | `00:00:02` |
| d481-getradiostats-wmm-bytesreceived-ac_vo | `2026-04-16T03:24:13+08:00` | `00:00:03` |
| d482-getradiostats-wmm-bytessent-ac_be | `2026-04-16T03:24:16+08:00` | `00:00:03` |
| d483-radio-stats-wmmbytessent-ac_bk | `2026-04-16T03:24:19+08:00` | `00:00:02` |
| d484-radio-stats-wmmbytessent-ac_vi | `2026-04-16T03:24:21+08:00` | `00:00:02` |
| d485-getradiostats-wmm-bytessent-ac_vo | `2026-04-16T03:24:24+08:00` | `00:00:03` |
| d486-radio-stats-wmmfailedbytesreceived-ac_be | `2026-04-16T03:24:27+08:00` | `00:00:02` |
| d487-radio-stats-wmmfailedbytesreceived-ac_bk | `2026-04-16T03:24:29+08:00` | `00:00:02` |
| d488-radio-stats-wmmfailedbytesreceived-ac_vi | `2026-04-16T03:24:31+08:00` | `00:00:02` |
| d489-radio-stats-wmmfailedbytesreceived-ac_vo | `2026-04-16T03:24:34+08:00` | `00:00:02` |
| d490-getradiostats-wmm-failedbytessent-ac_be | `2026-04-16T03:24:37+08:00` | `00:00:03` |
| d491-radio-stats-wmmfailedbytessent-ac_bk | `2026-04-16T03:24:39+08:00` | `00:00:02` |
| d492-radio-stats-wmmfailedbytessent-ac_vi | `2026-04-16T03:24:42+08:00` | `00:00:02` |
| d493-radio-stats-wmmfailedbytessent-ac_vo | `2026-04-16T03:24:44+08:00` | `00:00:02` |
| d494-radio-vhtcapabilities | `2026-04-16T03:24:49+08:00` | `00:00:05` |
| wifi-llapi-d495-retrycount | `2026-04-16T03:31:11+08:00` | `00:06:23` |
| d496-ssid-wmm-ac_be_stats_wmmbytesreceived_ssid | `2026-04-16T03:31:21+08:00` | `00:00:10` |
| d497-ssid-wmm-ac_bk_stats_wmmbytesreceived_ssid | `2026-04-16T03:31:23+08:00` | `00:00:02` |
| d498-ssid-wmm-ac_vi_stats_wmmbytesreceived_ssid | `2026-04-16T03:31:24+08:00` | `00:00:02` |
| d499-ssid-wmm-ac_vo_stats_wmmbytesreceived_ssid | `2026-04-16T03:31:34+08:00` | `00:00:10` |
| d500-ssid-wmm-ac_be_stats_wmmbytessent_ssid | `2026-04-16T03:31:36+08:00` | `00:00:02` |
| d501-ssid-wmm-ac_bk_stats_wmmbytessent_ssid | `2026-04-16T03:31:37+08:00` | `00:00:02` |
| d502-ssid-wmm-ac_vi_stats_wmmbytessent_ssid | `2026-04-16T03:31:42+08:00` | `00:00:05` |
| d503-ssid-wmm-ac_vo_stats_wmmbytessent_ssid | `2026-04-16T03:31:44+08:00` | `00:00:02` |
| d504-ssid-wmm-ac_be_stats_wmmfailedbytesreceived_ssid | `2026-04-16T03:31:45+08:00` | `00:00:02` |
| d505-ssid-wmm-ac_bk_stats_wmmfailedbytesreceived_ssid | `2026-04-16T03:31:51+08:00` | `00:00:06` |
| d506-ssid-wmm-ac_vi_stats_wmmfailedbytesreceived_ssid | `2026-04-16T03:31:57+08:00` | `00:00:06` |
| d507-ssid-wmm-ac_vo_stats_wmmfailedbytesreceived_ssid | `2026-04-16T03:32:03+08:00` | `00:00:06` |
| d508-ssid-wmm-ac_be_stats_wmmfailedbytessent_ssid | `2026-04-16T03:32:04+08:00` | `00:00:02` |
| d509-ssid-wmm-ac_bk_stats_wmmfailedbytessent_ssid | `2026-04-16T03:32:06+08:00` | `00:00:02` |
| d510-ssid-wmm-ac_vi_stats_wmmfailedbytessent_ssid | `2026-04-16T03:32:11+08:00` | `00:00:05` |
| d511-ssid-wmm-ac_vo_stats_wmmfailedbytessent_ssid | `2026-04-16T03:32:13+08:00` | `00:00:02` |
| d512-ssid-wmm-ac_be_stats_wmmfailedreceived | `2026-04-16T03:41:16+08:00` | `00:09:03` |
| d513-ssid-wmm-ac_bk_stats_wmmfailedreceived | `2026-04-16T03:41:21+08:00` | `00:00:05` |
| d514-ssid-wmm-ac_vi_stats_wmmfailedreceived | `2026-04-16T03:41:23+08:00` | `00:00:02` |
| d515-ssid-wmm-ac_vo_stats_wmmfailedreceived | `2026-04-16T03:41:24+08:00` | `00:00:02` |
| d516-ssid-wmm-ac_be_stats_wmmfailedsent | `2026-04-16T03:41:26+08:00` | `00:00:02` |
| d517-ssid-wmm-ac_bk_stats_wmmfailedsent | `2026-04-16T03:41:31+08:00` | `00:00:05` |
| d518-ssid-wmm-ac_vi_stats_wmmfailedsent | `2026-04-16T03:41:36+08:00` | `00:00:05` |
| d519-ssid-wmm-ac_vo_stats_wmmfailedsent | `2026-04-16T03:41:41+08:00` | `00:00:05` |
| d520-ssid-wmm-ac_be_stats_wmmpacketsreceived | `2026-04-16T03:41:50+08:00` | `00:00:10` |
| d521-ssid-wmm-ac_bk_stats_wmmpacketsreceived | `2026-04-16T03:41:55+08:00` | `00:00:05` |
| d522-ssid-wmm-ac_vi_stats_wmmpacketsreceived | `2026-04-16T03:42:00+08:00` | `00:00:05` |
| d523-ssid-wmm-ac_vo_stats_wmmpacketsreceived | `2026-04-16T03:42:10+08:00` | `00:00:10` |
| d524-ssid-wmm-ac_be_stats_wmmpacketssent | `2026-04-16T03:42:12+08:00` | `00:00:02` |
| d525-ssid-wmm-ac_bk_stats_wmmpacketssent | `2026-04-16T03:42:17+08:00` | `00:00:05` |
| d526-ssid-wmm-ac_vi_stats_wmmpacketssent | `2026-04-16T03:42:22+08:00` | `00:00:05` |
| d527-ssid-wmm-ac_vo_stats_wmmpacketssent | `2026-04-16T03:42:27+08:00` | `00:00:05` |
| d528-spectruminfo-bandwidth | `2026-04-16T03:42:30+08:00` | `00:00:03` |
| d529-spectruminfo-channel | `2026-04-16T03:42:33+08:00` | `00:00:03` |
| d530-spectruminfo-noiselevel | `2026-04-16T03:42:37+08:00` | `00:00:03` |
| d531-spectruminfo-accesspoints | `2026-04-16T03:42:41+08:00` | `00:00:04` |
| d532-spectruminfo-ourusage | `2026-04-16T03:42:45+08:00` | `00:00:03` |
| d533-spectruminfo-availability | `2026-04-16T03:42:48+08:00` | `00:00:03` |
| d575-skip-affiliatedsta-macaddress | `2026-04-16T03:42:49+08:00` | `00:00:01` |
| d576-skip-affiliatedsta-bytessent | `2026-04-16T03:42:51+08:00` | `00:00:01` |
| d577-skip-affiliatedsta-bytesreceived | `2026-04-16T03:42:52+08:00` | `00:00:01` |
| d578-skip-affiliatedsta-packetssent | `2026-04-16T03:42:53+08:00` | `00:00:01` |
| d579-skip-affiliatedsta-packetsreceived | `2026-04-16T03:42:55+08:00` | `00:00:01` |
| d580-skip-affiliatedsta-errorssent | `2026-04-16T03:42:56+08:00` | `00:00:01` |
| d581-skip-affiliatedsta-signalstrength | `2026-04-16T03:42:57+08:00` | `00:00:01` |
| d588-ssid-mldunit | `2026-04-16T03:42:59+08:00` | `00:00:02` |
| d593-wifi7aprole-emlmrsupport | `2026-04-16T03:43:00+08:00` | `00:00:02` |
| d594-wifi7aprole-emlsrsupport | `2026-04-16T03:43:02+08:00` | `00:00:02` |
| d595-wifi7aprole-strsupport | `2026-04-16T03:43:03+08:00` | `00:00:02` |
| d596-wifi7aprole-nstrsupport | `2026-04-16T03:43:05+08:00` | `00:00:02` |
| d597-wifi7starole-emlmrsupport | `2026-04-16T03:43:06+08:00` | `00:00:02` |
| d598-wifi7starole-emlsrsupport | `2026-04-16T03:43:08+08:00` | `00:00:02` |
| d599-wifi7starole-strsupport | `2026-04-16T03:43:09+08:00` | `00:00:02` |
| d600-wifi7starole-nstrsupport | `2026-04-16T03:43:11+08:00` | `00:00:02` |

## 0405 impacted testcase results

- **impacted case count**: `43` (`Pass=26`, `Failed=11`, `Mixed=3`, `Non-pass expected=3`)

| case_id | overall | result_5g | result_6g | result_24g | diagnostic_status | comment |
| --- | --- | --- | --- | --- | --- | --- |
| D006 | Pass | Pass | Pass | Pass | Pass | pass after retry (2/2) |
| D007 | Pass | Pass | Pass | Pass | Pass |  |
| D019 | Failed | Fail | Fail | Fail | Pass |  |
| D021 | Pass | Pass | Pass | Pass | Pass |  |
| D022 | Mixed | Pass | Not Supported | Pass | Pass |  |
| D024 | Pass | Pass | Pass | Pass | Pass | pass after retry (2/2) |
| D025 | Pass | Pass | Pass | Pass | Pass |  |
| D026 | Pass | Pass | Pass | Pass | Pass | pass after retry (2/2) |
| D027 | Pass | Pass | Pass | Pass | Pass |  |
| D036 | Failed | Fail | N/A | N/A | FailTest | pass_criteria not satisfied (failed after 2/2 attempts) |
| D037 | Failed | Fail | N/A | N/A | FailTest | pass_criteria not satisfied (failed after 2/2 attempts) |
| D038 | Failed | Fail | N/A | N/A | Pass |  |
| D039 | Pass | Pass | Pass | Pass | Pass |  |
| D040 | Failed | Fail | N/A | N/A | Pass |  |
| D041 | Pass | Pass | Pass | Pass | Pass |  |
| D042 | Non-pass expected | Not Supported | Not Supported | Not Supported | Pass |  |
| D043 | Pass | Pass | Pass | Pass | Pass |  |
| D044 | Pass | Pass | Pass | Pass | Pass | pass after retry (2/2) |
| D045 | Pass | Pass | Pass | Pass | Pass |  |
| D046 | Pass | Pass | Pass | Pass | Pass |  |
| D048 | Failed | Pass | Fail | Fail | Pass |  |
| D049 | Failed | Fail | N/A | N/A | Pass |  |
| D054 | Pass | Pass | Pass | Pass | Pass |  |
| D055 | Failed | Fail | Fail | Fail | Pass |  |
| D056 | Pass | Pass | Pass | Pass | Pass |  |
| D058 | Pass | Pass | Pass | Pass | Pass |  |
| D059 | Pass | Pass | Pass | Pass | Pass |  |
| D060 | Pass | Pass | Pass | Pass | Pass |  |
| D061 | Pass | Pass | Pass | Pass | Pass |  |
| D062 | Pass | Pass | Pass | Pass | Pass |  |
| D063 | Mixed | Pass | Not Supported | Not Supported | Pass |  |
| D071 | Pass | Pass | Pass | Pass | Pass |  |
| D072 | Pass | Pass | Pass | Pass | Pass | pass after retry (2/2) |
| D082 | Pass | Pass | Pass | Pass | Pass |  |
| D086 | Non-pass expected | Not Supported | Not Supported | Not Supported | Pass |  |
| D093 | Pass | Pass | Pass | Pass | Pass |  |
| D095 | Pass | Pass | Pass | Pass | Pass |  |
| D096 | Non-pass expected | Not Supported | Not Supported | Not Supported | Pass |  |
| D099 | Pass | Pass | Pass | Pass | Pass |  |
| D100 | Failed | Fail | Fail | Fail | Pass |  |
| D104 | Mixed | Pass | Not Supported | Pass | Pass |  |
| D117 | Failed | Pass | Fail | Pass | Pass |  |
| D183 | Failed | Fail | N/A | N/A | FailConfig | setup_env failed (failed after 2/2 attempts) |

## Artifacts

- baseline log: `/home/paul_chen/.copilot/session-state/aa1898bb-c265-48d1-ab97-05578cd0e697/files/0405-full-run/baseline.log`
- full run log: `/home/paul_chen/.copilot/session-state/aa1898bb-c265-48d1-ab97-05578cd0e697/files/0405-full-run/full-run.log`
- xlsx report: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/20260415_BGW720-0405_wifi_LLAPI_20260415T200953166372.xlsx`
- md report: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/bgw720-0405_wifi_llapi_20260415t200953166372.md`
- json report: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/bgw720-0405_wifi_llapi_20260415t200953166372.json`
- dut log: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/20260415T200953166372_DUT.log`
- sta log: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/20260415T200953166372_STA.log`
- agent trace dir: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T200953166372`
- telegram notify: `sent`

