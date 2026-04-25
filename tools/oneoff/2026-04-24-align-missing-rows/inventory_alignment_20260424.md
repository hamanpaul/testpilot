# Inventory alignment report

- generated_at: `2026-04-25T06:30:40.788124+00:00`
- mode: `dry-run`
- actions: `17`

## Actions

| kind | row | from | to | fields_changed |
| --- | --- | --- | --- | --- |
| rename | 66 | D068_discoverymethodenabled_accesspoint_fils.yaml | D066_discoverymethodenabled_accesspoint_fils.yaml | `{"id": ["wifi-llapi-D068-discoverymethodenabled-accesspoint-fils", "wifi-llapi-D066-discoverymethodenabled-accesspoint-fils"], "source.row": [68, 66]}` |
| rename | 67 | D068_discoverymethodenabled_accesspoint_upr.yaml | D067_discoverymethodenabled_accesspoint_upr.yaml | `{"id": ["wifi-llapi-D068-discoverymethodenabled-accesspoint-upr", "wifi-llapi-D067-discoverymethodenabled-accesspoint-upr"], "source.row": [68, 67]}` |
| rename | 109 | D115_getstationstats_accesspoint.yaml | D109_getstationstats.yaml | `{"id": ["wifi-llapi-D115-getstationstats-accesspoint", "wifi-llapi-D109-getstationstats"], "source.row": [115, 109]}` |
| rename | 110 | D115_getstationstats_active.yaml | D110_getstationstats_active.yaml | `{"id": ["wifi-llapi-D115-getstationstats-active", "wifi-llapi-D110-getstationstats-active"], "source.row": [115, 110]}` |
| rename | 111 | D115_getstationstats_associationtime.yaml | D111_getstationstats_associationtime.yaml | `{"id": ["wifi-llapi-D115-getstationstats-associationtime", "wifi-llapi-D111-getstationstats-associationtime"], "source.row": [115, 111]}` |
| rename | 112 | D115_getstationstats_authenticationstate.yaml | D112_getstationstats_authenticationstate.yaml | `{"id": ["wifi-llapi-D115-getstationstats-authenticationstate", "wifi-llapi-D112-getstationstats-authenticationstate"], "source.row": [115, 112]}` |
| rename | 113 | D115_getstationstats_avgsignalstrength.yaml | D113_getstationstats_avgsignalstrength.yaml | `{"id": ["wifi-llapi-D115-getstationstats-avgsignalstrength", "wifi-llapi-D113-getstationstats-avgsignalstrength"], "source.row": [115, 113]}` |
| rename | 114 | D115_getstationstats_avgsignalstrengthbychain.yaml | D114_getstationstats_avgsignalstrengthbychain.yaml | `{"id": ["wifi-llapi-D115-getstationstats-avgsignalstrengthbychain", "wifi-llapi-D114-getstationstats-avgsignalstrengthbychain"], "source.row": [115, 114]}` |
| move | 407 | D495_retrycount_ssid_stats_basic.yaml | D407_retrycount_ssid_stats.yaml | `{"id": ["wifi-llapi-d495-retrycount-basic", "wifi-llapi-D407-retrycount"], "source.row": [495, 407]}` |
| metadata | 495 | D495_retrycount_ssid_stats_verified.yaml | D495_retrycount_ssid_stats_verified.yaml | `{"source.row": [362, 495]}` |
| delete | None | D096_uapsdenable.yaml | None | `{}` |
| delete | None | D097_vendorie.yaml | None | `{}` |
| delete | None | D100_wmmenable.yaml | None | `{}` |
| delete | None | D102_configmethodssupported.yaml | None | `{}` |
| delete | None | D106_relaycredentialsenable.yaml | None | `{}` |
| delete | None | D474_channel_radio_37.yaml | None | `{}` |
| create | 428 | _template.yaml | D428_channel_neighbour.yaml | `{"id": [null, "wifi-llapi-D428-channel-neighbour"], "source.api": [null, "Channel"], "source.object": [null, "WiFi.AccessPoint.{i}.Neighbour.{i}."], "source.row": [null, 428]}` |

## Post state

_not-run_
