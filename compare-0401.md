# compare-0401

## Inputs

- trace dirs (overlay order; later directories override earlier case results):
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T172957084134`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T174551843336`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T175538121906`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T231709014359`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T235952361188`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T000249620932`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T003340845889`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T005520941756`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T005633950804`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T010944709855`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T011655056430`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T012358700786`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T013010016650`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T013545364055`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T020657288045`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T021655844208`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T022541033440`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T023259417785`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T024240506323`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T025449283775`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T030202219754`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T030853360475`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T031458311484`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T032521733067`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T033856175894`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T035856845825`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T042647797154`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T044907394777`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T050318932313`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T052709875993`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T055159421076`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T060855269192`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T061743676049`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T062615392940`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T063442091882`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T064002607672`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T065809885285`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T071746618166`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T075200621380`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T080405422245`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T081301178883`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T082022613657`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T083419287730`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T085025879532`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T090437438519`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T092400687838`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T094515864676`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T095836613095`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T103130805176`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T105418577078`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T111530183752`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T112544193230`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T113456092168`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T115620062809`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T121358780961`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T122417812289`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T130448459477`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T132144592128`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T133308180539`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T135928729951`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T141305083695`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T142616419984`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T144105373183`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T145000666925`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T164447027184`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T172222999250`
- answer sheet: `/home/paul_chen/prj_arc/testpilot/0401.xlsx`
- cases dir: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/cases`
- compare rule: normalize both sides so only `Pass` stays `Pass`; all other values become `Fail`.
- row mapping rule: use case `D###` number to match `0401.xlsx` worksheet row `###`.

## Summary

| metric | value |
| --- | ---: |
| compared cases | 420 |
| full matches | 298 |
| mismatch cases | 122 |
| missing answer rows | 0 |
| metadata drift rows | 58 |

## Per-band summary

| band | matched | mismatched |
| --- | ---: | ---: |
| 5g | 303 | 117 |
| 6g | 300 | 120 |
| 2.4g | 301 | 119 |

## Mismatch table

| case_id | D-row | mapping | actual raw (5/6/2.4) | expected raw (R/S/T) | actual norm | expected norm | mismatch bands |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `wifi-llapi-D020-frequencycapabilities` | 20 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `wifi-llapi-D047-supportedhe160mcs` | 47 | exact | Not Supported / N/A / N/A | Pass / Pass / Not Supported | Fail / Fail / Fail | Pass / Pass / Fail | 5g, 6g |
| `d179-radio-ampdu` | 179 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d180-radio-amsdu` | 180 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d181-radio-fragmentationthreshold` | 181 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d182-radio-rtsthreshold` | 182 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d184-radio-nractiverxantenna` | 184 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d185-radio-nractivetxantenna` | 185 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d186-radio-nrrxantenna` | 186 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d187-radio-nrtxantenna` | 187 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d190-radio-explicitbeamformingenabled` | 190 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d191-radio-explicitbeamformingsupported` | 191 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d192-radio-guardinterval` | 192 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d193-radio-hecapsenabled` | 193 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d194-radio-hecapssupported` | 194 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d195-radio-ieee80211_caps` | 195 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d196-radio-ieee80211henabled` | 196 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d197-radio-ieee80211hsupported` | 197 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d198-radio-ieee80211ksupported` | 198 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d199-radio-ieee80211rsupported` | 199 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d200-radio-implicitbeamformingenabled` | 200 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d201-radio-implicitbeamformingsupported` | 201 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d202-radio-interference` | 202 | exact | Fail / Fail / Fail | Pass / Fail / Pass | Fail / Fail / Fail | Pass / Fail / Pass | 5g, 2.4g |
| `d203-radio-maxchannelbandwidth` | 203 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d204-radio-multiusermimoenabled` | 204 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d205-radio-multiusermimosupported` | 205 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d207-radio-obsscoexistenceenable` | 207 | exact | Fail / Fail / Fail | Not Supported / Not Supported / Pass | Fail / Fail / Fail | Fail / Fail / Pass | 2.4g |
| `d208-radio-ofdmaenable` | 208 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d209-radio-operatingchannelbandwidth` | 209 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d211-radio-operatingstandards` | 211 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d212-radio-possiblechannels` | 212 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d214-radio-rifsenabled` | 214 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d251-radio-vendor-regulatorydomainrev` | 251 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d257-getradioairstats-load` | 257 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d261-getradioairstats-txtime` | 261 | exact | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d277-getscanresults-bandwidth` | 277 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d289-getscanresults-radio` | 289 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d290-getscanresults-centrechannel` | 290 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d296-startacs` | 296 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d297-startautochannelselection` | 297 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d302-getssidstats-bytesreceived` | 302 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d308-getssidstats-failedretranscount` | 308 | exact | Pass / Pass / Pass | Not Supported / Not Supported / Not Supported | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d313-getssidstats-retranscount` | 313 | exact | Pass / Pass / Pass | Not Supported / Not Supported / Not Supported | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d316-getssidstats-unknownprotopacketsreceived` | 316 | exact | Pass / Pass / Pass | Not Supported / Not Supported / Not Supported | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `wifi-llapi-d327-errorsreceived` | 327 | exact | Pass / Pass / Pass | Skip / Skip / Skip | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `wifi-llapi-d328-errorssent` | 328 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `wifi-llapi-d329-failedretranscount` | 329 | exact | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `wifi-llapi-d334-retranscount` | 334 | exact | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `wifi-llapi-d336-unicastpacketssent` | 336 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `wifi-llapi-d337-unknownprotopacketsreceived` | 337 | exact | Pass / Pass / Pass | Skip / Skip / Skip | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d354-radio-enable` | 354 | drift | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d355-skip-addclient` | 355 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d356-skip-delclient` | 356 | exact | Skip / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d357-skip-csistats` | 357 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d359-ap-isolationenable` | 359 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d363-ieee80211ax-bsscolorpartial` | 363 | exact | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d364-ieee80211ax-nonsrgobsspdmaxoffset` | 364 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d367-ieee80211ax-srgobsspdmaxoffset` | 367 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d370-assocdev-active` | 370 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d371-assocdev-disassociationtime` | 371 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d377-radio-maxbitrate` | 377 | exact | Pass / Pass / Pass | Not Supported / Not Supported / Not Supported | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d379-radio-mcs` | 379 | exact | Pass / Pass / Pass | Skip / Skip / Skip | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d380-radio-multiaptypessupported` | 380 | exact | Pass / Pass / Pass | skip / skip / skip | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d384-radio-radcapabilitieshtstr` | 384 | exact | Pass / Pass / Pass | Pass / Not Supported / Pass | Pass / Pass / Pass | Pass / Fail / Pass | 6g |
| `d385-radio-radcapabilitiesvhtstr` | 385 | exact | Pass / Pass / Pass | Pass / Not Supported / Not Supported | Pass / Pass / Pass | Pass / Fail / Fail | 6g, 2.4g |
| `d396-getradiostats-errorsreceived` | 396 | drift | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d397-getradiostats-errorssent` | 397 | drift | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d414-assocdev-rrmoffchannelmaxduration` | 414 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d415-assocdev-rrmonchannelmaxduration` | 415 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d427-skip-neighbour-bssid` | 427 | drift | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d429-skip-neighbour-colocatedap` | 429 | drift | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d430-skip-neighbour-information` | 430 | drift | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d431-skip-neighbour-nasidentifier` | 431 | drift | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d432-skip-neighbour-operatingclass` | 432 | drift | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d433-skip-neighbour-phytype` | 433 | drift | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d434-skip-neighbour-r0khkey` | 434 | drift | Skip / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d435-skip-neighbour-ssid` | 435 | drift | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d436-security-owetransitioninterface` | 436 | exact | Pass / Pass / Pass | Not Supported / Not Supported / Not Supported | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d437-security-saepassphrase` | 437 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d438-security-transitiondisable` | 438 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d454-getradiostats-failedretranscount` | 454 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d455-getradiostats-multipleretrycount` | 455 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d474-radio-channel` | 474 | drift | Pass / Pass / Pass | Not Supported / Not Supported / Not Supported | Pass / Pass / Pass | Fail / Fail / Fail | 5g, 6g, 2.4g |
| `d477-getradiostats-unknownprotopacketsreceived` | 477 | drift | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d478-getradiostats-wmm-bytesreceived-ac_be` | 478 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d479-getradiostats-wmm-bytesreceived-ac_bk` | 479 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d480-getradiostats-wmm-bytesreceived-ac_vi` | 480 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d481-getradiostats-wmm-bytesreceived-ac_vo` | 481 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d482-getradiostats-wmm-bytessent-ac_be` | 482 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d483-getradiostats-wmm-bytessent-ac_bk` | 483 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d484-getradiostats-wmm-bytessent-ac_vi` | 484 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d485-getradiostats-wmm-bytessent-ac_vo` | 485 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d486-getradiostats-wmm-failedbytesreceived-ac_be` | 486 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d487-getradiostats-wmm-failedbytesreceived-ac_bk` | 487 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d488-getradiostats-wmm-failedbytesreceived-ac_vi` | 488 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d489-getradiostats-wmm-failedbytesreceived-ac_vo` | 489 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d490-getradiostats-wmm-failedbytessent-ac_be` | 490 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d491-getradiostats-wmm-failedbytessent-ac_bk` | 491 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d492-getradiostats-wmm-failedbytessent-ac_vi` | 492 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d493-getradiostats-wmm-failedbytessent-ac_vo` | 493 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d496-ssid-wmm-ac_be_stats_wmmbytesreceived_ssid` | 496 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d499-ssid-wmm-ac_vo_stats_wmmbytesreceived_ssid` | 499 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d502-ssid-wmm-ac_vi_stats_wmmbytessent_ssid` | 502 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d505-ssid-wmm-ac_bk_stats_wmmfailedbytesreceived_ssid` | 505 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d506-ssid-wmm-ac_vi_stats_wmmfailedbytesreceived_ssid` | 506 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d507-ssid-wmm-ac_vo_stats_wmmfailedbytesreceived_ssid` | 507 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d508-ssid-wmm-ac_be_stats_wmmfailedbytessent_ssid` | 508 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d510-ssid-wmm-ac_vi_stats_wmmfailedbytessent_ssid` | 510 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d512-ssid-wmm-ac_be_stats_wmmfailedreceived` | 512 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d513-ssid-wmm-ac_bk_stats_wmmfailedreceived` | 513 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d517-ssid-wmm-ac_bk_stats_wmmfailedsent` | 517 | exact | Pass / Fail / Pass | Pass / Pass / Pass | Pass / Fail / Pass | Pass / Pass / Pass | 6g |
| `d518-ssid-wmm-ac_vi_stats_wmmfailedsent` | 518 | exact | Pass / Fail / Fail | Pass / Pass / Pass | Pass / Fail / Fail | Pass / Pass / Pass | 6g, 2.4g |
| `d519-ssid-wmm-ac_vo_stats_wmmfailedsent` | 519 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d520-ssid-wmm-ac_be_stats_wmmpacketsreceived` | 520 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d521-ssid-wmm-ac_bk_stats_wmmpacketsreceived` | 521 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d522-ssid-wmm-ac_vi_stats_wmmpacketsreceived` | 522 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d523-ssid-wmm-ac_vo_stats_wmmpacketsreceived` | 523 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d524-ssid-wmm-ac_be_stats_wmmpacketssent` | 524 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d525-ssid-wmm-ac_bk_stats_wmmpacketssent` | 525 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d526-ssid-wmm-ac_vi_stats_wmmpacketssent` | 526 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d588-ssid-mldunit` | 588 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d600-wifi7starole-nstrsupport` | 600 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |

## Mismatch details

### wifi-llapi-D020-frequencycapabilities

- case file: `D020_frequencycapabilities.yaml`
- answer row: `20`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `FrequencyCapabilities`
- workbook metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `FrequencyCapabilities`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to GW. 2. Verify Associated Station FrequencyCapabilities: root@prplOS:~# ubus-cli WiFi.? | grep FrequencyCapabilities= WiFi.AccessPoint.1.AssociatedDevice.1.FrequencyCapabilities="2.4GHz,5GHz,6GHz" WiFi.AccessPoi...
- 0401 H excerpt: wl -i wl0 sta_info ${STA_MAC} Frequency Bands Supported: 2.4G 5G 6G
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/wifi-llapi-D020-frequencycapabilities.json`

### wifi-llapi-D047-supportedhe160mcs

- case file: `D047_supportedhe160mcs.yaml`
- answer row: `47`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `SupportedHe160MCS`
- workbook metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `SupportedHe160MCS`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Not Supported` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Not Supported`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Fail`
- mismatch bands: `5g, 6g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T235952361188/wifi-llapi-D047-supportedhe160mcs.json`

### d179-radio-ampdu

- case file: `D179_ampdu.yaml`
- answer row: `179`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverConfig.` / `Ampdu`
- workbook metadata: `WiFi.Radio.{i}.DriverConfig.` / `Ampdu`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to GW 2. Set GW AMPDU to 1 =enable root@prplOS:/# ubus-cli WiFi.Radio.1.DriverConfig.Ampdu=1 > WiFi.Radio.1.DriverConfig.Ampdu=1 WiFi.Radio.1.DriverConfig. WiFi.Radio.1.DriverConfig.Ampdu=1 3. Run Iperf3 from stat...
- 0401 H excerpt: AMPDU = Enable root@prplOS:/# wl -i wlx ampdu 1 AMPDU = Disable root@prplOS:/# wl -i wlx ampdu 0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d179-radio-ampdu.json`

### d180-radio-amsdu

- case file: `D180_amsdu.yaml`
- answer row: `180`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverConfig.` / `Amsdu`
- workbook metadata: `WiFi.Radio.{i}.DriverConfig.` / `Amsdu`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Get Amsdu default value: root@prplOS:/# ubus-cli WiFi.Radio.*.DriverConfig.Amsdu? > WiFi.Radio.*.DriverConfig.Amsdu? WiFi.Radio.1.DriverConfig.Amsdu=-1 WiFi.Radio.2.DriverConfig.Amsdu=-1 WiFi.Radio.3.DriverConfig.Amsdu=-1
- 0401 H excerpt: wl -i wl0 amsdu wl -i wl1 amsdu wl -i wl2 amsdu root@prplOS:/# iw phy phy0 info | grep -i msdu Max AMSDU length: 3839 bytes root@prplOS:/# iw phy phy1 info | grep -i msdu root@prplOS:/# iw phy phy2 info | grep -i msdu Max AMSDU length: 3...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d180-radio-amsdu.json`

### d181-radio-fragmentationthreshold

- case file: `D181_fragmentationthreshold.yaml`
- answer row: `181`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverConfig.` / `FragmentationThreshold`
- workbook metadata: `WiFi.Radio.{i}.DriverConfig.` / `FragmentationThreshold`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Set Fragmentation Threshold to 1500 root@prplOS:/# ubus-cli WiFi.Radio.*.DriverConfig.FragmentationThreshold=1500 > WiFi.Radio.*.DriverConfig.FragmentationThreshold=1500 WiFi.Radio.1.DriverConfig. WiFi.Radio.1.DriverConfig.Fragmentati...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 fragthresh 1500 (0x5dc) root@prplOS:/# wl -i wl1 fragthresh 1500 (0x5dc) root@prplOS:/# wl -i wl2 fragthresh 1500 (0x5dc)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d181-radio-fragmentationthreshold.json`

### d182-radio-rtsthreshold

- case file: `D182_rtsthreshold.yaml`
- answer row: `182`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverConfig.` / `RtsThreshold`
- workbook metadata: `WiFi.Radio.{i}.DriverConfig.` / `RtsThreshold`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Set RtsThreshold "ex. 1500 root@prplOS:/# ubus-cli WiFi.Radio.*.DriverConfig.RtsThreshold=1500 > WiFi.Radio.*.DriverConfig.RtsThreshold=1500 WiFi.Radio.1.DriverConfig. WiFi.Radio.1.DriverConfig.RtsThreshold=1500 WiFi.Radio.2.DriverCon...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 rtsthresh 1500 (0x5dc) root@prplOS:/# wl -i wl1 rtsthresh 1500 (0x5dc) root@prplOS:/# wl -i wl2 rtsthresh 1500 (0x5dc)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d182-radio-rtsthreshold.json`

### d184-radio-nractiverxantenna

- case file: `D184_nractiverxantenna.yaml`
- answer row: `184`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrActiveRxAntenna`
- workbook metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrActiveRxAntenna`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check GW Radio DriverStatus.NrActiveRxAntenna: root@prplOS:/# ubus-cli WiFi.Radio.*.DriverStatus.NrActiveRxAntenna? > WiFi.Radio.*.DriverStatus.NrActiveRxAntenna? WiFi.Radio.1.DriverStatus.NrActiveRxAntenna=-1 WiFi.Radio.2.DriverStatu...
- 0401 H excerpt: wl -i wl0 rxchain root@prplOS:/# wl -i wl0 rxchain 15 (0xf) root@prplOS:/# wl -i wl1 rxchain 15 (0xf) root@prplOS:/# wl -i wl2 rxchain 15 (0xf) Value Hex Meaning 1 0x1 1×1 (chain 0 only) 3 0x3 2×2 (chains 0–1) 7 0x7 3×3 (chains 0–2) 15 0...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d184-radio-nractiverxantenna.json`

### d185-radio-nractivetxantenna

- case file: `D185_nractivetxantenna.yaml`
- answer row: `185`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrActiveTxAntenna`
- workbook metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrActiveTxAntenna`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check GW Radio DriverStatus.NrActiveTxAntenna root@prplOS:/# ubus-cli WiFi.Radio.*.DriverStatus.NrActiveTxAntenna? > WiFi.Radio.*.DriverStatus.NrActiveTxAntenna? WiFi.Radio.1.DriverStatus.NrActiveTxAntenna=-1 WiFi.Radio.2.DriverStatus...
- 0401 H excerpt: wl -i wl0 txchain root@prplOS:/# wl -i wl0 txchain 15 (0xf) root@prplOS:/# wl -i wl1 txchain 15 (0xf) root@prplOS:/# wl -i wl2 txchain 15 (0xf) Value Hex Meaning 1 0x1 1×1 (chain 0 only) 3 0x3 2×2 (chains 0–1) 7 0x7 3×3 (chains 0–2) 15 0...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d185-radio-nractivetxantenna.json`

### d186-radio-nrrxantenna

- case file: `D186_nrrxantenna.yaml`
- answer row: `186`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrRxAntenna`
- workbook metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrRxAntenna`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check GW Radio DriverStatus.NrRxAntenna root@prplOS:/# ubus-cli WiFi.Radio.*.DriverStatus.NrRxAntenna? > WiFi.Radio.*.DriverStatus.NrRxAntenna? WiFi.Radio.1.DriverStatus.NrRxAntenna=4 WiFi.Radio.2.DriverStatus.NrRxAntenna=4 WiFi.Radio...
- 0401 H excerpt: wl -i wl0 rxchain root@prplOS:/# wl -i wl0 rxchain 15 (0xf) root@prplOS:/# wl -i wl1 rxchain 15 (0xf) root@prplOS:/# wl -i wl2 rxchain 15 (0xf) Value Hex Meaning 1 0x1 1×1 (chain 0 only) 3 0x3 2×2 (chains 0–1) 7 0x7 3×3 (chains 0–2) 15 0...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d186-radio-nrrxantenna.json`

### d187-radio-nrtxantenna

- case file: `D187_nrtxantenna.yaml`
- answer row: `187`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrTxAntenna`
- workbook metadata: `WiFi.Radio.{i}.DriverStatus.` / `NrTxAntenna`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check GW Radio DriverStatus.NrTxAntenna: root@prplOS:/# ubus-cli WiFi.Radio.*.DriverStatus.NrTxAntenna? > WiFi.Radio.*.DriverStatus.NrTxAntenna? WiFi.Radio.1.DriverStatus.NrTxAntenna=4 WiFi.Radio.2.DriverStatus.NrTxAntenna=4 WiFi.Radi...
- 0401 H excerpt: wl -i wl0 txchain root@prplOS:/# wl -i wl0 txchain 15 (0xf) root@prplOS:/# wl -i wl1 txchain 15 (0xf) root@prplOS:/# wl -i wl2 txchain 15 (0xf) Value Hex Meaning 1 0x1 1×1 (chain 0 only) 3 0x3 2×2 (chains 0–1) 7 0x7 3×3 (chains 0–2) 15 0...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d187-radio-nrtxantenna.json`

### d190-radio-explicitbeamformingenabled

- case file: `D190_explicitbeamformingenabled.yaml`
- answer row: `190`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `ExplicitBeamFormingEnabled`
- workbook metadata: `WiFi.Radio.{i}.` / `ExplicitBeamFormingEnabled`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check API default value: root@prplOS:/# ubus-cli WiFi.Radio.*.ExplicitBeamFormingEnabled? > WiFi.Radio.*.ExplicitBeamFormingEnabled? WiFi.Radio.1.ExplicitBeamFormingEnabled=1 WiFi.Radio.2.ExplicitBeamFormingEnabled=1 WiFi.Radio.3.Expl...
- 0401 H excerpt: (API=1) root@prplOS:/# wl -i wl0 txbf 1 root@prplOS:/# wl -i wl1 txbf 1 root@prplOS:/# wl -i wl2 txbf 1 (API=0) root@prplOS:/# wl -i wl0 txbf 0 root@prplOS:/# wl -i wl1 txbf 0 root@prplOS:/# wl -i wl2 txbf 0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d190-radio-explicitbeamformingenabled.json`

### d191-radio-explicitbeamformingsupported

- case file: `D191_explicitbeamformingsupported.yaml`
- answer row: `191`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `ExplicitBeamFormingSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `ExplicitBeamFormingSupported`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read-only API, defines whether each radio supported ExplicitBeamForming. Check API value and compare with driver return value: root@prplOS:/# ubus-cli WiFi.Radio.*.ExplicitBeamFormingSupported? > WiFi.Radio.*.ExplicitBeamFormingSuppor...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d191-radio-explicitbeamformingsupported.json`

### d192-radio-guardinterval

- case file: `D192_guardinterval.yaml`
- answer row: `192`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `GuardInterval`
- workbook metadata: `WiFi.Radio.{i}.` / `GuardInterval`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: Setting value: ["400nsec'","800nsec","1xLTF_0.8us","1xLTF_1.6us","2xLTF_0.8us","2xLTF_1.6us","4xLTF_0.8us","4xLTF_1.6us","Auto"] 1. Get GI Default value root@prplOS:/# ubus-cli WiFi.Radio.*.GuardInterval? > WiFi.Radio.*.GuardInterval? Wi...
- 0401 H excerpt: BRCM: CSP CS00012439197 -- root@prplOS:/# wl -i wl0 nrate eht mcs 13 Nss 4 Tx Exp 0 bw160 2xLTF GI 0.8us auto root@prplOS:/# wl -i wl0 sgi_tx -1
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d192-radio-guardinterval.json`

### d193-radio-hecapsenabled

- case file: `D193_hecapsenabled.yaml`
- answer row: `193`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `HeCapsEnabled`
- workbook metadata: `WiFi.Radio.{i}.` / `HeCapsEnabled`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Try enabled all supporting HE capablitities for all readios: root@prplOS:/# ubus-cli 'WiFi.Radio.*.HeCapsEnabled="DL_OFDMA,UL_OFDMA,DL_MUMIMO,UL_MUMIMO"' 2. Check the settings: root@prplOS:/# ubus-cli WiFi.Radio.*.HeCapsEnabled? > WiF...
- 0401 H excerpt: wl -i wl[x] he features root@prplOS:/# wl -i wl0 he features 63 (0x3f) root@prplOS:/# wl -i wl1 he features 63 (0x3f) root@prplOS:/# wl -i wl2 he features 63 (0x3f)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d193-radio-hecapsenabled.json`

### d194-radio-hecapssupported

- case file: `D194_hecapssupported.yaml`
- answer row: `194`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `HeCapsSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `HeCapsSupported`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read supported He Capability for all radios: root@prplOS:/# ubus-cli WiFi.Radio.*.HeCapsSupported? > WiFi.Radio.*.HeCapsSupported? WiFi.Radio.1.HeCapsSupported="DL_OFDMA,UL_OFDMA,DL_MUMIMO,UL_MUMIMO" WiFi.Radio.2.HeCapsSupported="DL_O...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d194-radio-hecapssupported.json`

### d195-radio-ieee80211_caps

- case file: `D195_ieee80211_caps.yaml`
- answer row: `195`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `IEEE80211_Caps`
- workbook metadata: `WiFi.Radio.{i}.` / `IEEE80211_Caps`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Get Radio Default value of IEEE80211_Caps root@prplOS:/# ubus-cli WiFi.Radio.*.IEEE80211_Caps? > WiFi.Radio.*.IEEE80211_Caps? WiFi.Radio.1.IEEE80211_Caps="160MHz UAPSD WEP TKIP AES AES_CCM SAE EXPL_BF IMPL_BF MU_MIMO DFS_OFFLOAD OWE S...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 cap ap sta wet led wme 802.11d 802.11h rm cac mbss8 ampdu ampdu_tx ampdu_rx amsdurx amsdutx rxchain_pwrsave wds dwds vht-prop-rates multi-user-beamformer single-user-beamformer multi-user-beamformee single-user-b...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d195-radio-ieee80211_caps.json`

### d196-radio-ieee80211henabled

- case file: `D196_ieee80211henabled.yaml`
- answer row: `196`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `IEEE80211hEnabled`
- workbook metadata: `WiFi.Radio.{i}.` / `IEEE80211hEnabled`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check API default value: root@prplOS:/# ubus-cli WiFi.Radio.*.IEEE80211hEnabled? > WiFi.Radio.*.IEEE80211hEnabled? WiFi.Radio.1.IEEE80211hEnabled=1 WiFi.Radio.2.IEEE80211hEnabled=0 WiFi.Radio.3.IEEE80211hEnabled=0 2. Compare with driv...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 spect Loose interpretation of 11h spec - may join non 11h AP. root@prplOS:/# wl -i wl1 spect Off root@prplOS:/# wl -i wl2 spect Off root@prplOS:/# wl -i wl0 radar 1 root@prplOS:/# wl -i wl1 radar 0 root@prplOS:/#...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d196-radio-ieee80211henabled.json`

### d197-radio-ieee80211hsupported

- case file: `D197_ieee80211hsupported.yaml`
- answer row: `197`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `IEEE80211hSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `IEEE80211hSupported`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read-only API, defines whether each radio supported 802.11h standard. Check the API value and compare them with driver capability and packets' tag from radio beacons: ubus-cli WiFi.Radio.*.IEEE80211hSupported? > WiFi.Radio.*.IEEE80211...
- 0401 H excerpt: wl -i wl0 cap | grep 802.11h ap sta wet led wme 802.11d 802.11h rm cac mbss8 ampdu ampdu_tx ampdu_rx amsdurx amsdutx rxchain_pwrsave wds dwds vht-prop-rates multi-user-beamformer single-user-beamformer multi-user-beamformee single-user-b...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d197-radio-ieee80211hsupported.json`

### d198-radio-ieee80211ksupported

- case file: `D198_ieee80211ksupported.yaml`
- answer row: `198`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `IEEE80211kSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `IEEE80211kSupported`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read-only API, defines whether each radio supported 802.11k standard. Check the API value and compare them with driver capability and packets' tag from radio beacons: root@prplOS:/# ubus-cli WiFi.Radio.*.IEEE80211kSupported? > WiFi.Ra...
- 0401 H excerpt: (RM Enable Capabilities included in beacon packet, IE: 70)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d198-radio-ieee80211ksupported.json`

### d199-radio-ieee80211rsupported

- case file: `D199_ieee80211rsupported.yaml`
- answer row: `199`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `IEEE80211rSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `IEEE80211rSupported`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read-only API, defines whether each radio supported 802.11r standard. Check the API value and compare them with driver capability and packets' tag from radio beacons: root@prplOS:/# ubus-cli WiFi.Radio.*.IEEE80211rSupported? > WiFi.Ra...
- 0401 H excerpt: (Fast Transition / Mability Domain included in beacon packet, IE: 54)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d199-radio-ieee80211rsupported.json`

### d200-radio-implicitbeamformingenabled

- case file: `D200_implicitbeamformingenabled.yaml`
- answer row: `200`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `ImplicitBeamFormingEnabled`
- workbook metadata: `WiFi.Radio.{i}.` / `ImplicitBeamFormingEnabled`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check API default value: root@prplOS:/# ubus-cli WiFi.Radio.*.ImplicitBeamFormingEnabled? > WiFi.Radio.*.ImplicitBeamFormingEnabled? WiFi.Radio.1.ImplicitBeamFormingEnabled=1 WiFi.Radio.2.ImplicitBeamFormingEnabled=1 WiFi.Radio.3.Impl...
- 0401 H excerpt: (API=1) root@prplOS:/# wl -i wl0 txbf_imp 1 root@prplOS:/# wl -i wl1 txbf_imp 1 root@prplOS:/# wl -i wl2 txbf_imp 1 (API=0) root@prplOS:/# wl -i wl0 txbf_imp 0 root@prplOS:/# wl -i wl1 txbf_imp 0 root@prplOS:/# wl -i wl2 txbf_imp 0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d200-radio-implicitbeamformingenabled.json`

### d201-radio-implicitbeamformingsupported

- case file: `D201_implicitbeamformingsupported.yaml`
- answer row: `201`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `ImplicitBeamFormingSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `ImplicitBeamFormingSupported`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read-only API, defines whether each radio supported ImplicitBeamForming. Check API value and compare with driver return value: root@prplOS:/# ubus-cli WiFi.Radio.*.ImplicitBeamFormingSupported? > WiFi.Radio.*.ImplicitBeamFormingSuppor...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d201-radio-implicitbeamformingsupported.json`

### d202-radio-interference

- case file: `D202_interference.yaml`
- answer row: `202`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `Interference`
- workbook metadata: `WiFi.Radio.{i}.` / `Interference`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Fail` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Fail` / `Pass`
- mismatch bands: `5g, 2.4g`
- 0401 G excerpt: 1. Check API default value: root@prplOS:/# ubus-cli WiFi.Radio.*.Interference? > WiFi.Radio.*.Interference? WiFi.Radio.1.Interference=0 WiFi.Radio.2.Interference=0 WiFi.Radio.3.Interference=0
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d202-radio-interference.json`

### d203-radio-maxchannelbandwidth

- case file: `D203_maxchannelbandwidth.yaml`
- answer row: `203`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `MaxChannelBandwidth`
- workbook metadata: `WiFi.Radio.{i}.` / `MaxChannelBandwidth`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: Usage: wl bw_cap <2g|5g|6g> [<cap>] 2g|5g|6g - Requested band cap: 0x1 - 20MHz 0x3 - 20/40MHz 0x7 - 20/40/80MHz 0xf - 20/40/80/160MHz 0x1f - 20/40/80/160/320MHz 0xff - Unrestricted root@prplOS:~# root@prplOS:~# wl -i wl0 bw_cap 5g 0xf ro...
- 0401 H excerpt: wl -i wl0 bw_cap Usage: wl bw_cap <2g|5g|6g> [<cap>] 2g|5g|6g - Requested band cap: 0x1 - 20MHz 0x3 - 20/40MHz 0x7 - 20/40/80MHz 0xf - 20/40/80/160MHz 0x1f - 20/40/80/160/320MHz 0xff - Unrestricted root@prplOS:/# wl bw_cap 5g 0xf root@pr...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d203-radio-maxchannelbandwidth.json`

### d204-radio-multiusermimoenabled

- case file: `D204_multiusermimoenabled.yaml`
- answer row: `204`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `MultiUserMIMOEnabled`
- workbook metadata: `WiFi.Radio.{i}.` / `MultiUserMIMOEnabled`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check MIMO enabled or not root@prplOS:/# ubus-cli WiFi.Radio.*.MultiUserMIMOEnabled? > WiFi.Radio.*.MultiUserMIMOEnabled? WiFi.Radio.1.MultiUserMIMOEnabled=1 WiFi.Radio.2.MultiUserMIMOEnabled=1 WiFi.Radio.3.MultiUserMIMOEnabled=1 2. C...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 mu_features 1 root@prplOS:/# wl -i wl1 mu_features 1 root@prplOS:/# wl -i wl1 mu_features 1
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d204-radio-multiusermimoenabled.json`

### d205-radio-multiusermimosupported

- case file: `D205_multiusermimosupported.yaml`
- answer row: `205`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `MultiUserMIMOSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `MultiUserMIMOSupported`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read-only API, defines whether each radio supported MU-MIMO. Check API value and compare with driver return value: root@prplOS:/# ubus-cli WiFi.Radio.*.MultiUserMIMOSupported? > WiFi.Radio.*.MultiUserMIMOSupported? WiFi.Radio.1.MultiU...
- 0401 H excerpt: wl -i wl0 he features
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d205-radio-multiusermimosupported.json`

### d207-radio-obsscoexistenceenable

- case file: `D207_obsscoexistenceenable.yaml`
- answer row: `207`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `ObssCoexistenceEnable`
- workbook metadata: `WiFi.Radio.{i}.` / `ObssCoexistenceEnable`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Not Supported` / `Not Supported` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Fail` / `Fail` / `Pass`
- mismatch bands: `2.4g`
- 0401 G excerpt: 1.ubus-cli WiFi.Radio.3.ObssCoexistenceEnable=1 2.ubus-cli WiFi.Radio.3.OperatingChannelBandwidth="40MHz” 3.wl -i wl2 status shows 20MHz 4.ubus-cli WiFi.Radio.3.ObssCoexistenceEnable=0 5.wl -i wl2 status shows 40MHz
- 0401 H excerpt: root@prplOS:/# wl -i wl0 obss_coex 0 root@prplOS:/# wl -i wl1 obss_coex 0 root@prplOS:/# wl -i wl2 obss_coex 1
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d207-radio-obsscoexistenceenable.json`

### d208-radio-ofdmaenable

- case file: `D208_ofdmaenable.yaml`
- answer row: `208`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `OfdmaEnable`
- workbook metadata: `WiFi.Radio.{i}.` / `OfdmaEnable`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check OfdmaEnable root@prplOS:/tmp# ubus-cli WiFi.Radio.*.OfdmaEnable? > WiFi.Radio.*.OfdmaEnable? WiFi.Radio.1.OfdmaEnable=1 WiFi.Radio.2.OfdmaEnable=1 WiFi.Radio.3.OfdmaEnable=1 2. Capture Beacon and make sure the following bits map...
- 0401 H excerpt: root@prplOS:~# wl -i wl0 he features 63 (0x3f) root@prplOS:~# wl -i wl1 he features 63 (0x3f) root@prplOS:~# wl -i wl2 he features 63 (0x3f) 63 (decimal) = 0x3f (hex) 0x3f in binary = 0011 1111 That means bits 0–5 are set, and higher bit...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d208-radio-ofdmaenable.json`

### d209-radio-operatingchannelbandwidth

- case file: `D209_operatingchannelbandwidth.yaml`
- answer row: `209`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `OperatingChannelBandwidth`
- workbook metadata: `WiFi.Radio.{i}.` / `OperatingChannelBandwidth`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check MaxChannelBandwidth for each radio: root@prplOS:/# ubus-cli WiFi.Radio.*.MaxChannelBandwidth? > WiFi.Radio.*.MaxChannelBandwidth? WiFi.Radio.1.MaxChannelBandwidth="160MHz" WiFi.Radio.2.MaxChannelBandwidth="320MHz" WiFi.Radio.3.M...
- 0401 H excerpt: wl -i wl[x] status wl -i wl0 status ... Chanspec: 5GHz channel [ch] 20MHz 40MHz 80MHz 160MHz wl -i wl1 status ... Chanspec: 6GHz channel [ch] 20MHz 40MHz 80MHz 160MHz 320MHz wl -i wl2 status ... Chanspec: 2.4GHz channel [ch] 20MHz 40MHz ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d209-radio-operatingchannelbandwidth.json`

### d211-radio-operatingstandards

- case file: `D211_operatingstandards.yaml`
- answer row: `211`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `OperatingStandards`
- workbook metadata: `WiFi.Radio.{i}.` / `OperatingStandards`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Try change all radio to BE standard: ubus-cli WiFi.Radio.1.OperatingStandards=be ubus-cli WiFi.Radio.2.OperatingStandards=be ubus-cli WiFi.Radio.3.OperatingStandards=be 2. Check standard: root@prplOS:/# ubus-cli WiFi.Radio.*.Operating...
- 0401 H excerpt: [BE] wl -i wl[i] status wl -i wl[i] nmode wl -i wl[i] vhtmode wl -i wl[i] he features wl -i wl[i] eht features root@prplOS:/# wl -i wl0 status SSID: "AAA_ATnT-wl0" Mode: Managed RSSI: 0 dBm SNR: 0 dB noise: -99 dBm Channel: 36 BSSID: 64:...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d211-radio-operatingstandards.json`

### d212-radio-possiblechannels

- case file: `D212_possiblechannels.yaml`
- answer row: `212`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `PossibleChannels`
- workbook metadata: `WiFi.Radio.{i}.` / `PossibleChannels`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check the list of channels supported by each radio: root@prplOS:/# ubus-cli WiFi.Radio.*.PossibleChannels? > WiFi.Radio.*.PossibleChannels? WiFi.Radio.1.PossibleChannels="36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136...
- 0401 H excerpt: wl -i wl0 chanspecs 36 (0xd024) 40 (0xd028) 44 (0xd02c) 48 (0xd030) 52 (0xd034) 56 (0xd038) 60 (0xd03c) 64 (0xd040) 100 (0xd064) 104 (0xd068) 108 (0xd06c) 112 (0xd070) 116 (0xd074) 120 (0xd078) 124 (0xd07c) 128 (0xd080) 132 (0xd084) 136 ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d212-radio-possiblechannels.json`

### d214-radio-rifsenabled

- case file: `D214_rifsenabled.yaml`
- answer row: `214`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `RIFSEnabled`
- workbook metadata: `WiFi.Radio.{i}.` / `RIFSEnabled`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check the API default value for all radio: root@prplOS:/# ubus-cli WiFi.Radio.*.RIFSEnabled? > WiFi.Radio.*.RIFSEnabled? WiFi.Radio.1.RIFSEnabled="Default" WiFi.Radio.2.RIFSEnabled="Default" WiFi.Radio.3.RIFSEnabled="Default" 2. Modif...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d214-radio-rifsenabled.json`

### d251-radio-vendor-regulatorydomainrev

- case file: `D251_regulatorydomain_radio_vendor.yaml`
- answer row: `251`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Vendor.` / `RegulatoryDomain`
- workbook metadata: `WiFi.Radio.{i}.Vendor.` / `RegulatoryDomain`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Get API default value: root@prplOS:/# ubus-cli WiFi.Radio.*.Vendor.Brcm.RegulatoryDomainRev? > WiFi.Radio.*.Vendor.Brcm.RegulatoryDomainRev? WiFi.Radio.1.Vendor.Brcm.RegulatoryDomainRev=0 WiFi.Radio.2.Vendor.Brcm.RegulatoryDomainRev=0...
- 0401 H excerpt: wl -i wl0 country wl -i wl1 country wl -i wl2 country root@prplOS:/# wl -i wl0 country #a (#a/0) <unknown> root@prplOS:/# wl -i wl1 country #a (#a/0) <unknown> root@prplOS:/# wl -i wl2 country #a (#a/0) <unknown>
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d251-radio-vendor-regulatorydomainrev.json`

### d257-getradioairstats-load

- case file: `D257_getradioairstats_load.yaml`
- answer row: `257`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `getRadioAirStats()`
- workbook metadata: `WiFi.Radio.{i}.` / `getRadioAirStats()`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d257-getradioairstats-load.json`

### d261-getradioairstats-txtime

- case file: `D261_getradioairstats_txtime.yaml`
- answer row: `261`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `getRadioAirStats()`
- workbook metadata: `WiFi.Radio.{i}.` / `getRadioAirStats()`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Fail` / `Fail` / `Fail`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d261-getradioairstats-txtime.json`

### d277-getscanresults-bandwidth

- case file: `D277_getscanresults_bandwidth.yaml`
- answer row: `277`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `getScanResults()`
- workbook metadata: `WiFi.Radio.{i}.` / `getScanResults()`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Setup another AP as a data collecting target, try collect the target's Wi-Fi air radio info. Compare the actual value and API returned value. [5GHz] ubus-cli "WiFi.Radio.*.getScanResults()" | grep -i 1C:F4:3F:73:C7 * -A 15 -B1 { BSSID...
- 0401 H excerpt: [2.4GHz] root@prplOS:/# iw dev wl2 scan | grep 1c:f4:3f:73:c7:40 -A150 BSS 1c:f4:3f:73:c7:40(on wl2) TSF: 14499627031 usec (0d, 04:01:39) freq: 2472 beacon interval: 100 TUs capability: ESS Privacy ShortPreamble ShortSlotTime APSD RadioM...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d277-getscanresults-bandwidth.json`

### d289-getscanresults-radio

- case file: `D289_getscanresults_radio.yaml`
- answer row: `289`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `getScanResults()`
- workbook metadata: `WiFi.Radio.{i}.` / `getScanResults()`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d289-getscanresults-radio.json`

### d290-getscanresults-centrechannel

- case file: `D290_getscanresults_centrechannel.yaml`
- answer row: `290`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `getScanResults()`
- workbook metadata: `WiFi.Radio.{i}.` / `getScanResults()`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d290-getscanresults-centrechannel.json`

### d296-startacs

- case file: `D296_startacs.yaml`
- answer row: `296`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `startACS()`
- workbook metadata: `WiFi.Radio.{i}.` / `startACS()`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Try call API function: root@prplOS:/# ubus-cli "WiFi.Radio.1.startACS()" > WiFi.Radio.1.startACS() ERROR: call (null) failed with status 1 - unknown error WiFi.Radio.1.startACS() returned [ "" ] root@prplOS:/# ubus-cli "WiFi.Radio.2.s...
- 0401 H excerpt: logread | grep ACS iw dev wl0 info iw dev wl1 info iw dev wl2 info
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d296-startacs.json`

### d297-startautochannelselection

- case file: `D297_startautochannelselection.yaml`
- answer row: `297`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `startAutoChannelSelection()`
- workbook metadata: `WiFi.Radio.{i}.` / `startAutoChannelSelection()`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Try call API function: root@prplOS:/# ubus-cli "WiFi.Radio.*.startAutoChannelSelection()" > WiFi.Radio.*.startAutoChannelSelectio() ERROR: call (null) failed with status 3 - function not found WiFi.Radio.1.startAutoChannelSelectio() r...
- 0401 H excerpt: iw dev wl0 info iw dev wl1 info iw dev wl2 info
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d297-startautochannelselection.json`

### d302-getssidstats-bytesreceived

- case file: `D302_getssidstats_bytesreceived.yaml`
- answer row: `302`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- workbook metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to SSID4, SSID6 and SSID8 2. Run Ping between Station and check BytesReceived root@prplOS:/# ubus-cli "WiFi.SSID.?" | grep \.BytesReceived= WiFi.SSID.4.Stats.BytesReceived=1647695 WiFi.SSID.6.Stats.BytesReceived=2...
- 0401 H excerpt: cat /proc/net/dev | grep wl0 root@prplOS:/# cat /proc/net/dev Inter-| Receive | Transmit face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed wl0: 1647695 6411 0 14 0 0 0 196...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d302-getssidstats-bytesreceived.json`

### d308-getssidstats-failedretranscount

- case file: `D308_getssidstats_failedretranscount.yaml`
- answer row: `308`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- workbook metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Not Supported` / `Not Supported` / `Not Supported`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to GW 2. Run Iperf overnight between station 3. Get stats ubus-cli "WiFi.SSID."? | grep FailedRetransCount
- 0401 H excerpt: cat /proc/net/dev | grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d308-getssidstats-failedretranscount.json`

### d313-getssidstats-retranscount

- case file: `D313_getssidstats_retranscount.yaml`
- answer row: `313`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- workbook metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Not Supported` / `Not Supported` / `Not Supported`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to GW SSID4, SSID6 and SSID8 2. Run Iperf overnight between station 3. Get stats RetransCount root@prplOS:/# ubus-cli "WiFi.SSID.8.getSSIDStats()" | grep \.RetransCount RetransCount = 0, root@prplOS:/# ubus-cli "W...
- 0401 H excerpt: cat /proc/net/dev | grep wl0 /proc/net/dev does not have 802.11-specific retry counters
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d313-getssidstats-retranscount.json`

### d316-getssidstats-unknownprotopacketsreceived

- case file: `D316_getssidstats_unknownprotopacketsreceived.yaml`
- answer row: `316`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- workbook metadata: `WiFi.SSID.{i}.` / `getSSIDStats()`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Not Supported` / `Not Supported` / `Not Supported`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /proc/net/dev | grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d316-getssidstats-unknownprotopacketsreceived.json`

### wifi-llapi-d327-errorsreceived

- case file: `D327_errorsreceived_ssid_stats.yaml`
- answer row: `327`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.` / `ErrorsReceived`
- workbook metadata: `WiFi.SSID.{i}.Stats.` / `ErrorsReceived`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Skip` / `Skip` / `Skip`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /proc/net/dev | grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/wifi-llapi-d327-errorsreceived.json`

### wifi-llapi-d328-errorssent

- case file: `D328_errorssent_ssid_stats.yaml`
- answer row: `328`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.` / `ErrorsSent`
- workbook metadata: `WiFi.SSID.{i}.Stats.` / `ErrorsSent`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: setup_env failed (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /proc/net/dev | grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/wifi-llapi-d328-errorssent.json`

### wifi-llapi-d329-failedretranscount

- case file: `D329_failedretranscount_ssid_stats.yaml`
- answer row: `329`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.` / `FailedRetransCount`
- workbook metadata: `WiFi.SSID.{i}.Stats.` / `FailedRetransCount`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Fail` / `Fail` / `Fail`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /proc/net/dev | grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/wifi-llapi-d329-failedretranscount.json`

### wifi-llapi-d334-retranscount

- case file: `D334_retranscount_ssid_stats.yaml`
- answer row: `334`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.` / `RetransCount`
- workbook metadata: `WiFi.SSID.{i}.Stats.` / `RetransCount`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Fail` / `Fail` / `Fail`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect one WiFi station to SSID4, SSID6 and SSID8 of the GW (DUT) 2. Run Iperf from Station to GW and between Station 3. Setup neighbour GW near the GW (DUT) 4. Place Neighbor GW nearby 5. Set same channel + bandwidth 6. Connect STA(...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/wifi-llapi-d334-retranscount.json`

### wifi-llapi-d336-unicastpacketssent

- case file: `D336_unicastpacketssent.yaml`
- answer row: `336`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.` / `UnicastPacketsSent`
- workbook metadata: `WiFi.SSID.{i}.Stats.` / `UnicastPacketsSent`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: setup_env failed (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to GW SSID4, SSID6 and SSID8 2. Run Ping between station's 3. Get stats Unicast packet sent root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.UnicastPacketsSent? > WiFi.SSID.*.Stats.UnicastPacketsSent? WiFi.SSID.1.Stats.U...
- 0401 H excerpt: cat /proc/net/dev | grep wl0 root@prplOS:/# cat /proc/net/dev Inter-| Receive | Transmit face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed wl0: 99866942 866493 0 20 0 0 0 ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/wifi-llapi-d336-unicastpacketssent.json`

### wifi-llapi-d337-unknownprotopacketsreceived

- case file: `D337_unknownprotopacketsreceived_ssid_stats.yaml`
- answer row: `337`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.` / `UnknownProtoPacketsReceived`
- workbook metadata: `WiFi.SSID.{i}.Stats.` / `UnknownProtoPacketsReceived`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Skip` / `Skip` / `Skip`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /proc/net/dev | grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/wifi-llapi-d337-unknownprotopacketsreceived.json`

### d354-radio-enable

- case file: `D354_enable_radio.yaml`
- answer row: `354`
- mapping status: `drift`
- source metadata: `WiFi.Radio.{i}.` / `Enable`
- workbook metadata: `WiFi.Radio.{i}.Sensing.` / `Enable`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Check API default value: root@prplOS:/# ubus-cli WiFi.Radio.*.Sensing.Enable? > WiFi.Radio.*.Sensing.Enable? WiFi.Radio.1.Sensing.Enable=1 WiFi.Radio.2.Sensing.Enable=1 WiFi.Radio.3.Sensing.Enable=1 2. Modify the value to 0: ubus-cli ...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d354-radio-enable.json`

### d355-skip-addclient

- case file: `D355_addclient.yaml`
- answer row: `355`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Sensing.` / `addClient()`
- workbook metadata: `WiFi.Radio.{i}.Sensing.` / `addClient()`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Try add a sensing client by API: (5G) ubus-cli "WiFi.Radio.1.Sensing.addClient(MACAddress='A0:29:42:60:23:BD', MonitorInterval=100)" ubus-cli "WiFi.Radio.1.Sensing.addClient(MACAddress='14:85:7F:20:18:44', MonitorInterval=10)" (6G) ub...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d355-skip-addclient.json`

### d356-skip-delclient

- case file: `D356_delclient.yaml`
- answer row: `356`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Sensing.` / `delClient()`
- workbook metadata: `WiFi.Radio.{i}.Sensing.` / `delClient()`
- final status: `Pass`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Skip` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Try delete an added client: root@prplOS:/# ubus-cli "WiFi.Radio.*.Sensing.delClient(MACAddress='a0:29:42:60:23:be')" > WiFi.Radio.*.Sensing.delClient(MACAddress='a0:29:42:60:23:be') WiFi.Radio.1.Sensing.delClient() returned [ "" ] WiF...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d356-skip-delclient.json`

### d357-skip-csistats

- case file: `D357_csistats.yaml`
- answer row: `357`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Sensing.` / `csiStats()`
- workbook metadata: `WiFi.Radio.{i}.Sensing.` / `csiStats()`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Record the API counters in the beginning: root@prplOS:/# ubus-cli "WiFi.Radio.*.Sensing.csiStats()" > WiFi.Radio.*.Sensing.csiStats() WiFi.Radio.1.Sensing.csiStats() returned [ { M2MTransmitCounter = 0, NullFrameAckFailCounter = 0, Nu...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d357-skip-csistats.json`

### d359-ap-isolationenable

- case file: `D359_isolationenable.yaml`
- answer row: `359`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.` / `IsolationEnable`
- workbook metadata: `WiFi.AccessPoint.{i}.` / `IsolationEnable`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station to the Radio 2. Run ping between Station - by default isolation = disable so ping is OK -Enable Isolation ubus-cli WiFi.AccessPoint.5.IsolationEnable=1 --Ping between station should failed after enable Isolati...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d359-ap-isolationenable.json`

### d363-ieee80211ax-bsscolorpartial

- case file: `D363_bsscolorpartial.yaml`
- answer row: `363`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.IEEE80211ax.` / `BssColorPartial`
- workbook metadata: `WiFi.Radio.{i}.IEEE80211ax.` / `BssColorPartial`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Fail` / `Fail` / `Fail`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d363-ieee80211ax-bsscolorpartial.json`

### d364-ieee80211ax-nonsrgobsspdmaxoffset

- case file: `D364_nonsrgobsspdmaxoffset.yaml`
- answer row: `364`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.IEEE80211ax.` / `NonSRGOBSSPDMaxOffset`
- workbook metadata: `WiFi.Radio.{i}.IEEE80211ax.` / `NonSRGOBSSPDMaxOffset`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 he nsrg_pdmax
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d364-ieee80211ax-nonsrgobsspdmaxoffset.json`

### d367-ieee80211ax-srgobsspdmaxoffset

- case file: `D367_srgobsspdmaxoffset.yaml`
- answer row: `367`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.IEEE80211ax.` / `SRGOBSSPDMaxOffset`
- workbook metadata: `WiFi.Radio.{i}.IEEE80211ax.` / `SRGOBSSPDMaxOffset`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 he srg_pdmax
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d367-ieee80211ax-srgobsspdmaxoffset.json`

### d370-assocdev-active

- case file: `D370_active.yaml`
- answer row: `370`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `Active`
- workbook metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `Active`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station to GW 2. Check Associated Device Status root@prplOS:/# ubus-cli WiFi.AccessPoint.*.AssociatedDevice.*.? | grep -E 'Activ e|MAC' WiFi.AccessPoint.1.AssociatedDevice.11.Active=1 WiFi.AccessPoint.1.AssociatedDevice.1...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 assoclist assoclist 34:19:4D:A4:B5:09 assoclist 12:E3:C4:78:7B:6F assoclist 42:B7:35:6A:17:8E root@prplOS:/# wl -i wl1 assoclist assoclist 38:06:E6:92:B0:4A root@prplOS:/# wl -i wl2 assoclist assoclist E4:60:17:E...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d370-assocdev-active.json`

### d371-assocdev-disassociationtime

- case file: `D371_disassociationtime.yaml`
- answer row: `371`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `DisassociationTime`
- workbook metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `DisassociationTime`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station to GW 2. Check Associated Device Status 3. Disconnect Wifi Station from GW 4. Check Associated Device DisassociationTime root@prplOS:/# ubus-cli WiFi.AccessPoint.*.AssociatedDevice.*.? | grep -E 'Activ root@prplOS...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 assoclist root@prplOS:/# wl -i wl1 assoclist root@prplOS:/# wl -i wl2 assoclist
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d371-assocdev-disassociationtime.json`

### d377-radio-maxbitrate

- case file: `D377_maxbitrate.yaml`
- answer row: `377`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `MaxBitRate`
- workbook metadata: `WiFi.Radio.{i}.` / `MaxBitRate`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Not Supported` / `Not Supported` / `Not Supported`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Read-only API, defines max bitrate for each radio: ubus-cli WiFi.Radio.*.MaxBitRate? > WiFi.Radio.*.MaxBitRate? WiFi.Radio.1.MaxBitRate=0 WiFi.Radio.2.MaxBitRate=0 WiFi.Radio.3.MaxBitRate=0
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d377-radio-maxbitrate.json`

### d379-radio-mcs

- case file: `D379_mcs.yaml`
- answer row: `379`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `MCS`
- workbook metadata: `WiFi.Radio.{i}.` / `MCS`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Skip` / `Skip` / `Skip`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Verify MCS of the Radio root@prplOS:/# ubus-cli WiFi.Radio.*.MCS? > WiFi.Radio.*.MCS? WiFi.Radio.1.MCS=0 WiFi.Radio.2.MCS=0 WiFi.Radio.3.MCS=0
- 0401 H excerpt: root@prplOS:/# wl -i wl0 status SSID: "5G-123" Mode: Managed RSSI: 0 dBm SNR: 0 dB noise: -92 dBm Channel: 48/160 BSSID: 64:75:DA:4E:51:75 Capability: ESS RRM Beacon Interval: 100 msecs Supported Rates: [ 6(b) 9 12 18 24(b) 36 48 54 ] Ex...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d379-radio-mcs.json`

### d380-radio-multiaptypessupported

- case file: `D380_multiaptypessupported.yaml`
- answer row: `380`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `MultiAPTypesSupported`
- workbook metadata: `WiFi.Radio.{i}.` / `MultiAPTypesSupported`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `skip` / `skip` / `skip`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Get MultiAP type Supported mode root@prplOS:/# ubus-cli WiFi.Radio.*.MultiAPTypesSupported? > WiFi.Radio.*.MultiAPTypesSupported? WiFi.Radio.1.MultiAPTypesSupported="FronthaulBSS,BackhaulBSS,BackhaulSTA" WiFi.Radio.2.MultiAPTypesSuppo...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d380-radio-multiaptypessupported.json`

### d384-radio-radcapabilitieshtstr

- case file: `D384_radcapabilitieshtstr.yaml`
- answer row: `384`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `RadCapabilitiesHTStr`
- workbook metadata: `WiFi.Radio.{i}.` / `RadCapabilitiesHTStr`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Pass` / `Not Supported` / `Pass`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Pass` / `Fail` / `Pass`
- mismatch bands: `6g`
- 0401 G excerpt: 1. get RadCapabilitiesHTStr root@prplOS:/# ubus-cli WiFi.Radio.*.RadCapabilitiesHTStr? > WiFi.Radio.*.RadCapabilitiesHTStr? WiFi.Radio.1.RadCapabilitiesHTStr="CAP_40,SHORT_GI_20,SHORT_GI_40,MODE_40" WiFi.Radio.2.RadCapabilitiesHTStr="" W...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d384-radio-radcapabilitieshtstr.json`

### d385-radio-radcapabilitiesvhtstr

- case file: `D385_radcapabilitiesvhtstr.yaml`
- answer row: `385`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `RadCapabilitiesVHTStr`
- workbook metadata: `WiFi.Radio.{i}.` / `RadCapabilitiesVHTStr`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Pass` / `Not Supported` / `Not Supported`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Pass` / `Fail` / `Fail`
- mismatch bands: `6g, 2.4g`
- 0401 G excerpt: 1. get RadCapabilitiesVHTStr root@prplOS:/# ubus-cli WiFi.Radio.*.RadCapabilitiesVHTStr? > WiFi.Radio.*.RadCapabilitiesVHTStr? WiFi.Radio.1.RadCapabilitiesVHTStr="RX_LDPC,SGI_80,SGI_160,SU_BFR,SU_BFE,LINK_ADAPT_CAP" WiFi.Radio.2.RadCapab...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d385-radio-radcapabilitiesvhtstr.json`

### d396-getradiostats-errorsreceived

- case file: `D396_errorsreceived_radio_stats.yaml`
- answer row: `396`
- mapping status: `drift`
- source metadata: `WiFi.Radio.{i}.` / `getRadioStats()`
- workbook metadata: `WiFi.Radio.{i}.Stats.` / `ErrorsReceived`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /proc/net/dev |grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d396-getradiostats-errorsreceived.json`

### d397-getradiostats-errorssent

- case file: `D397_errorssent_radio_stats.yaml`
- answer row: `397`
- mapping status: `drift`
- source metadata: `WiFi.Radio.{i}.` / `getRadioStats()`
- workbook metadata: `WiFi.Radio.{i}.Stats.` / `ErrorsSent`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /proc/net/dev |grep wl0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d397-getradiostats-errorssent.json`

### d414-assocdev-rrmoffchannelmaxduration

- case file: `D414_rrmoffchannelmaxduration.yaml`
- answer row: `414`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `RrmOffChannelMaxDuration`
- workbook metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `RrmOffChannelMaxDuration`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to GW with one station 802.11k Enable and the other one 802.11k Disable. 2. Verify Station station 802.11k Enable Check whether RRM is ON or OFF using: wl sta_info <MAC> | grep -i rrm If 802.11k Enable then you wi...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d414-assocdev-rrmoffchannelmaxduration.json`

### d415-assocdev-rrmonchannelmaxduration

- case file: `D415_rrmonchannelmaxduration.yaml`
- answer row: `415`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `RrmOnChannelMaxDuration`
- workbook metadata: `WiFi.AccessPoint.{i}.AssociatedDevice.{i}.` / `RrmOnChannelMaxDuration`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi Station to GW with one station 802.11k Enable and the other one 802.11k Disable. 2. Verify Station station 802.11k Enable Check whether RRM is ON or OFF using: wl sta_info <MAC> | grep -i rrm If 802.11k Enable then you wi...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d415-assocdev-rrmonchannelmaxduration.json`

### d427-skip-neighbour-bssid

- case file: `D427_bssid_accesspoint_neighbour.yaml`
- answer row: `427`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `BSSID`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `BSSID`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Reset GW to Default then check Neighbour entry root@prplOS:/# ubus-cli WiFi.AccessPoint.1.? | grep Neighbour root@prplOS:/# 2. Add Neighbour entry root@prplOS:/# ubus-cli "WiFi.AccessPoint.1.setNeighbourAP(BSSID="AA:BB:CC:DD:EE :01",C...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d427-skip-neighbour-bssid.json`

### d429-skip-neighbour-colocatedap

- case file: `D429_colocatedap.yaml`
- answer row: `429`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `ColocatedAP`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `ColocatedAP`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d429-skip-neighbour-colocatedap.json`

### d430-skip-neighbour-information

- case file: `D430_information.yaml`
- answer row: `430`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `Information`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `Information`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d430-skip-neighbour-information.json`

### d431-skip-neighbour-nasidentifier

- case file: `D431_nasidentifier.yaml`
- answer row: `431`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `NASIdentifier`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `NASIdentifier`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d431-skip-neighbour-nasidentifier.json`

### d432-skip-neighbour-operatingclass

- case file: `D432_operatingclass.yaml`
- answer row: `432`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `OperatingClass`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `OperatingClass`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d432-skip-neighbour-operatingclass.json`

### d433-skip-neighbour-phytype

- case file: `D433_phytype.yaml`
- answer row: `433`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `PhyType`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `PhyType`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d433-skip-neighbour-phytype.json`

### d434-skip-neighbour-r0khkey

- case file: `D434_r0khkey.yaml`
- answer row: `434`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `R0KHKey`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `R0KHKey`
- final status: `Pass`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Skip` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d434-skip-neighbour-r0khkey.json`

### d435-skip-neighbour-ssid

- case file: `D435_ssid_accesspoint_neighbour.yaml`
- answer row: `435`
- mapping status: `drift`
- source metadata: `WiFi.AccessPoint.{i}.Neighbour.` / `SSID`
- workbook metadata: `WiFi.AccessPoint.{i}.Neighbour.{i}.` / `SSID`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `N/A` / `N/A`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d435-skip-neighbour-ssid.json`

### d436-security-owetransitioninterface

- case file: `D436_owetransitioninterface.yaml`
- answer row: `436`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.Security.` / `OWETransitionInterface`
- workbook metadata: `WiFi.AccessPoint.{i}.Security.` / `OWETransitionInterface`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Not Supported` / `Not Supported` / `Not Supported`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Set OWETransitionInterface root@prplOS:~# ubus-cli WiFi.AccessPoint.1.Security.OWETransitionInterface=DEFAULT_W L1_1 > WiFi.AccessPoint.1.Security.OWETransitionInterface=DEFAULT_WL1_1 WiFi.AccessPoint.1.Security. WiFi.AccessPoint.1.Se...
- 0401 H excerpt: root@prplOS:~# cat /tmp/wl0_hapd.conf |grep owe_transition_ifname root@prplOS:~# cat /tmp/wl1_hapd.conf |grep owe_transition_ifname root@prplOS:~# cat /tmp/wl2_hapd.conf |grep owe_transition_ifname
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d436-security-owetransitioninterface.json`

### d437-security-saepassphrase

- case file: `D437_saepassphrase.yaml`
- answer row: `437`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.Security.` / `SAEPassphrase`
- workbook metadata: `WiFi.AccessPoint.{i}.Security.` / `SAEPassphrase`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Set Security ModeEnabled=WPA3-Personal ubus-cli WiFi.AccessPoint.*.Security.ModeEnabled=WPA3-Personal 2. Set Security SAEPassphrase=1234567890 ubus-cli WiFi.AccessPoint.*.Security.SAEPassphrase=1234567890
- 0401 H excerpt: cat /tmp/wl0_hapd.conf |grep sae_password root@prplOS:/# cat /tmp/wl0_hapd.conf |grep sae_password sae_password=1234567890 root@prplOS:/# cat /tmp/wl1_hapd.conf |grep sae_password sae_password=1234567890 root@prplOS:/# cat /tmp/wl2_hapd....
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d437-security-saepassphrase.json`

### d438-security-transitiondisable

- case file: `D438_transitiondisable.yaml`
- answer row: `438`
- mapping status: `exact`
- source metadata: `WiFi.AccessPoint.{i}.Security.` / `TransitionDisable`
- workbook metadata: `WiFi.AccessPoint.{i}.Security.` / `TransitionDisable`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: cat /tmp/wl0_hapd.conf |grep transition_disable
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d438-security-transitiondisable.json`

### d454-getradiostats-failedretranscount

- case file: `D454_failedretranscount_radio_stats.yaml`
- answer row: `454`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `getRadioStats()`
- workbook metadata: `WiFi.Radio.{i}.` / `getRadioStats()`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Record counters at start: root@prplOS:/# ubus-cli "WiFi.Radio.*.getRadioStats()" | grep MultipleRetryCount MultipleRetryCount = 0, MultipleRetryCount = 0, MultipleRetryCount = 0, root@prplOS:/# ubus-cli "WiFi.Radio.*.getRadioStats()" ...
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d454-getradiostats-failedretranscount.json`

### d455-getradiostats-multipleretrycount

- case file: `D455_multipleretrycount_radio_stats.yaml`
- answer row: `455`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.` / `getRadioStats()`
- workbook metadata: `WiFi.Radio.{i}.` / `getRadioStats()`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d455-getradiostats-multipleretrycount.json`

### d474-radio-channel

- case file: `D474_channel_radio_37.yaml`
- answer row: `474`
- mapping status: `drift`
- source metadata: `WiFi.Radio.{i}.` / `Channel`
- workbook metadata: `WiFi.Radio.{i}.ScanResults.SurroundingChannels.{i}.` / `Channel`
- final status: `Pass`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Pass` / `Pass`
- expected raw: `Not Supported` / `Not Supported` / `Not Supported`
- actual normalized: `Pass` / `Pass` / `Pass`
- expected normalized: `Fail` / `Fail` / `Fail`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d474-radio-channel.json`

### d477-getradiostats-unknownprotopacketsreceived

- case file: `D477_unknownprotopacketsreceived_radio_stats.yaml`
- answer row: `477`
- mapping status: `drift`
- source metadata: `WiFi.Radio.{i}.` / `getRadioStats()`
- workbook metadata: `WiFi.Radio.{i}.Stats.` / `UnknownProtoPacketsReceived`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d477-getradiostats-unknownprotopacketsreceived.json`

### d478-getradiostats-wmm-bytesreceived-ac_be

- case file: `D478_ac_be_stats_wmmbytesreceived_radio.yaml`
- answer row: `478`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_BE`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M" 3. Verify Radio Stats.WmmBytesReceived.AC_BE root@prplOS:/# ubus-cli WiFi.Radio.*.? | grep WmmBytesReceived.AC_BE ...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 wme_counters AC_BE: tx frames: 23176 bytes: 6830889 failed frames: 0 failed bytes: 0 rx frames: 17703 bytes: 26181728 failed frames: 0 failed bytes: 0 root@prplOS:/# wl -i wl1 wme_counters AC_BE: tx frames: 26313...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d478-getradiostats-wmm-bytesreceived-ac_be.json`

### d479-getradiostats-wmm-bytesreceived-ac_bk

- case file: `D479_ac_bk_stats_wmmbytesreceived_radio.yaml`
- answer row: `479`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_BK`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0x20" 3. Verify Radio Stats.WmmBytesReceived.AC_BK root@prplOS:/# ubus-cli WiFi.Radio.*.? | grep WmmBytesRece...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 wme_counters AC_BE: tx frames: 23711 bytes: 7015133 failed frames: 0 failed bytes: 0 rx frames: 17734 bytes: 26185565 failed frames: 0 failed bytes: 0 root@prplOS:/# wl -i wl1 wme_counters AC_BE: tx frames: 27022...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d479-getradiostats-wmm-bytesreceived-ac_bk.json`

### d480-getradiostats-wmm-bytesreceived-ac_vi

- case file: `D480_ac_vi_stats_wmmbytesreceived_radio.yaml`
- answer row: `480`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_VI`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0x88" 3. Verify Radio Stats.WmmBytesReceived.AC_VI root@prplOS:/# ubus-cli WiFi.Radio.*.? | grep WmmBytesRece...
- 0401 H excerpt: wl -i wl0 wme_counters root@prplOS:/# wl -i wl0 wme_counters AC_VI: tx frames: 0 bytes: 0 failed frames: 0 failed bytes: 0 rx frames: 17205 bytes: 26495350 failed frames: 0 failed bytes: 0 root@prplOS:/# wl -i wl1 wme_counters AC_VI: tx ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d480-getradiostats-wmm-bytesreceived-ac_vi.json`

### d481-getradiostats-wmm-bytesreceived-ac_vo

- case file: `D481_ac_vo_stats_wmmbytesreceived_radio.yaml`
- answer row: `481`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_VO`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesReceived.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0xB8" 3. Verify Radio Stats.WmmBytesReceived.AC_VO root@prplOS:/# ubus-cli WiFi.Radio.*.? | grep WmmBytesRece...
- 0401 H excerpt: wl -i wl0 wme_counters root@prplOS:/# wl -i wl0 wme_counters AC_VO: tx frames: 8 bytes: 3541 failed frames: 0 failed bytes: 0 rx frames: 17345 bytes: 26447627 failed frames: 0 failed bytes: 0 root@prplOS:/# wl -i wl1 wme_counters AC_VO: ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d481-getradiostats-wmm-bytesreceived-ac_vo.json`

### d482-getradiostats-wmm-bytessent-ac_be

- case file: `D482_ac_be_stats_wmmbytessent_radio.yaml`
- answer row: `482`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_BE`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF between Station "iperf3 -c 192.168.1.1 -u -b 20M " 3. Execute command ubus-cli "WiFi.Radio.*.getRadioStats()" 4. Verify Radio Stats.WmmBytesR...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 wme_counters AC_BE: tx frames: 36796 bytes: 39571906 failed frames: 341 failed bytes: 79808 root@prplOS:/# wl -i wl1 wme_counters AC_BE: tx frames: 33627 bytes: 14116150 failed frames: 0 failed bytes: 0 root@prpl...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d482-getradiostats-wmm-bytessent-ac_be.json`

### d483-getradiostats-wmm-bytessent-ac_bk

- case file: `D483_ac_bk_stats_wmmbytessent_radio.yaml`
- answer row: `483`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_BK`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF iperf3 -c 192.168.1.1 -u -b 20M --tos 0x20 3. Execute command ubus-cli "WiFi.Radio.*.getRadioStats()" 4. Verify Radio Stats.WmmBytesSent.AC_B...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 wme_counters AC_BK: tx frames: 6824 bytes: 25882414 failed frames: 0 failed bytes: 0 root@prplOS:/# wl -i wl1 wme_counters AC_BK: tx frames: 6243 bytes: 22243076 failed frames: 0 failed bytes: 0 root@prplOS:/# wl...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d483-getradiostats-wmm-bytessent-ac_bk.json`

### d484-getradiostats-wmm-bytessent-ac_vi

- case file: `D484_ac_vi_stats_wmmbytessent_radio.yaml`
- answer row: `484`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_VI`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0x88" 3. Execute command ubus-cli "WiFi.Radio.*.getRadioStats()" 4. Verify Radio Stats.WmmBytesSent.AC_VI...
- 0401 H excerpt: wl -i wl0 wme_counters root@prplOS:/# wl -i wl0 wme_counters AC_VI: tx frames: 17265 bytes: 25861532 failed frames: 0 failed bytes: 0 root@prplOS:/# wl -i wl0 wme_counters AC_VI: tx frames: 4352 bytes: 6517858 failed frames: 0 failed byt...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d484-getradiostats-wmm-bytessent-ac_vi.json`

### d485-getradiostats-wmm-bytessent-ac_vo

- case file: `D485_ac_vo_stats_wmmbytessent_radio.yaml`
- answer row: `485`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_VO`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmBytesSent.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0xB8" 3. Execute command ubus-cli "WiFi.Radio.*.getRadioStats()" 4. Verify Radio Stats.WmmBytesSent.AC_VO...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 wme_counters AC_VO: tx frames: 17268 bytes: 25862027 failed frames: 2 failed bytes: 104 root@prplOS:/# wl -i wl1 wme_counters AC_VO: tx frames: 6 bytes: 972 failed frames: 0 failed bytes: 0 root@prplOS:/# wl -i w...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d485-getradiostats-wmm-bytessent-ac_vo.json`

### d486-getradiostats-wmm-failedbytesreceived-ac_be

- case file: `D486_ac_be_stats_wmmfailedbytesreceived_radio.yaml`
- answer row: `486`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_BE`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_BE" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_BE" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_BE" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d486-getradiostats-wmm-failedbytesreceived-ac_be.json`

### d487-getradiostats-wmm-failedbytesreceived-ac_bk

- case file: `D487_ac_bk_stats_wmmfailedbytesreceived_radio.yaml`
- answer row: `487`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_BK`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_BK" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_BK" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_BK" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d487-getradiostats-wmm-failedbytesreceived-ac_bk.json`

### d488-getradiostats-wmm-failedbytesreceived-ac_vi

- case file: `D488_ac_vi_stats_wmmfailedbytesreceived_radio.yaml`
- answer row: `488`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_VI`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_VI" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_VI" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_VI" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d488-getradiostats-wmm-failedbytesreceived-ac_vi.json`

### d489-getradiostats-wmm-failedbytesreceived-ac_vo

- case file: `D489_ac_vo_stats_wmmfailedbytesreceived_radio.yaml`
- answer row: `489`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_VO`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedBytesReceived.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_VO" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_VO" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_VO" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d489-getradiostats-wmm-failedbytesreceived-ac_vo.json`

### d490-getradiostats-wmm-failedbytessent-ac_be

- case file: `D490_ac_be_stats_wmmfailedbytessent_radio.yaml`
- answer row: `490`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_BE`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_BE" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_BE" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_BE" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d490-getradiostats-wmm-failedbytessent-ac_be.json`

### d491-getradiostats-wmm-failedbytessent-ac_bk

- case file: `D491_ac_bk_stats_wmmfailedbytessent_radio.yaml`
- answer row: `491`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_BK`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_BK" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_BK" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_BK" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d491-getradiostats-wmm-failedbytessent-ac_bk.json`

### d492-getradiostats-wmm-failedbytessent-ac_vi

- case file: `D492_ac_vi_stats_wmmfailedbytessent_radio.yaml`
- answer row: `492`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_VI`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_VI" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_VI" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_VI" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d492-getradiostats-wmm-failedbytessent-ac_vi.json`

### d493-getradiostats-wmm-failedbytessent-ac_vo

- case file: `D493_ac_vo_stats_wmmfailedbytessent_radio.yaml`
- answer row: `493`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_VO`
- workbook metadata: `WiFi.Radio.{i}.Stats.WmmFailedbytesSent.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Fail`
- attempts used: `2`
- runtime comment: pass_criteria not satisfied (failed after 2/2 attempts)
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: wl -i wl0 wme_counters | grep -A2 "AC_VO" | grep -E 'tx frames|rx frames' wl -i wl1 wme_counters | grep -A2 "AC_VO" | grep -E 'tx frames|rx frames' wl -i wl2 wme_counters | grep -A2 "AC_VO" | grep -E 'tx frames|rx frames'
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d493-getradiostats-wmm-failedbytessent-ac_vo.json`

### d496-ssid-wmm-ac_be_stats_wmmbytesreceived_ssid

- case file: `D496_ac_be_stats_wmmbytesreceived_ssid.yaml`
- answer row: `496`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmBytesReceived.` / `AC_BE`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmBytesReceived.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF between Station "iperf3 -c 192.168.1.1 -u -b 20M " 3. Verify SSID Stats WmmBytesReceived.AC_BE root@prplOS:/# ubus-cli WiFi.SSID.6.? | grep R...
- 0401 H excerpt: root@prplOS:/# ubus-cli "WiFi.Radio.*.getRadioStats()"? > WiFi.Radio.*.getRadioStats()? WiFi.Radio.1.getRadioStats() returned [ { WmmBytesReceived = { AC_BE = 31127479,
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d496-ssid-wmm-ac_be_stats_wmmbytesreceived_ssid.json`

### d499-ssid-wmm-ac_vo_stats_wmmbytesreceived_ssid

- case file: `D499_ac_vo_stats_wmmbytesreceived_ssid.yaml`
- answer row: `499`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmBytesReceived.` / `AC_VO`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmBytesReceived.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0xB8" 3. Verify SSID stats WmmBytesReceived.AC_VO root@prplOS:/# ubus-cli WiFi.SSID.6.? | grep Received.A...
- 0401 H excerpt: AC_VO: tx frames: 3 bytes: 495 failed frames: 0 failed bytes: 0 rx frames: 60 bytes: 3881 failed frames: 0 failed bytes: 0 foward frames: 0 bytes: 0 tx frames time expired: 0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d499-ssid-wmm-ac_vo_stats_wmmbytesreceived_ssid.json`

### d502-ssid-wmm-ac_vi_stats_wmmbytessent_ssid

- case file: `D502_ac_vi_stats_wmmbytessent_ssid.yaml`
- answer row: `502`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmBytesSent.` / `AC_VI`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmBytesSent.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0x88" 3. Verify SSID stats WmmBytesSent.AC_VI=0 root@prplOS:/# ubus-cli WiFi.SSID.6.Stats.WmmBytesSent.AC_VI?...
- 0401 H excerpt: AC_VI: tx frames: 17268 bytes: 25867464 failed frames: 0 failed bytes: 0 rx frames: 41129 bytes: 63338410 failed frames: 0 failed bytes: 0
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d502-ssid-wmm-ac_vi_stats_wmmbytessent_ssid.json`

### d505-ssid-wmm-ac_bk_stats_wmmfailedbytesreceived_ssid

- case file: `D505_ac_bk_stats_wmmfailedbytesreceived_ssid.yaml`
- answer row: `505`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedBytesReceived.` / `AC_BK`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedBytesReceived.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d505-ssid-wmm-ac_bk_stats_wmmfailedbytesreceived_ssid.json`

### d506-ssid-wmm-ac_vi_stats_wmmfailedbytesreceived_ssid

- case file: `D506_ac_vi_stats_wmmfailedbytesreceived_ssid.yaml`
- answer row: `506`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedBytesReceived.` / `AC_VI`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedBytesReceived.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d506-ssid-wmm-ac_vi_stats_wmmfailedbytesreceived_ssid.json`

### d507-ssid-wmm-ac_vo_stats_wmmfailedbytesreceived_ssid

- case file: `D507_ac_vo_stats_wmmfailedbytesreceived_ssid.yaml`
- answer row: `507`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedBytesReceived.` / `AC_VO`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedBytesReceived.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d507-ssid-wmm-ac_vo_stats_wmmfailedbytesreceived_ssid.json`

### d508-ssid-wmm-ac_be_stats_wmmfailedbytessent_ssid

- case file: `D508_ac_be_stats_wmmfailedbytessent_ssid.yaml`
- answer row: `508`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedbytesSent.` / `AC_BE`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedbytesSent.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d508-ssid-wmm-ac_be_stats_wmmfailedbytessent_ssid.json`

### d510-ssid-wmm-ac_vi_stats_wmmfailedbytessent_ssid

- case file: `D510_ac_vi_stats_wmmfailedbytessent_ssid.yaml`
- answer row: `510`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedbytesSent.` / `AC_VI`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedbytesSent.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d510-ssid-wmm-ac_vi_stats_wmmfailedbytessent_ssid.json`

### d512-ssid-wmm-ac_be_stats_wmmfailedreceived

- case file: `D512_ac_be_stats_wmmfailedreceived.yaml`
- answer row: `512`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedReceived.` / `AC_BE`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedReceived.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d512-ssid-wmm-ac_be_stats_wmmfailedreceived.json`

### d513-ssid-wmm-ac_bk_stats_wmmfailedreceived

- case file: `D513_ac_bk_stats_wmmfailedreceived.yaml`
- answer row: `513`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedReceived.` / `AC_BK`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedReceived.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d513-ssid-wmm-ac_bk_stats_wmmfailedreceived.json`

### d517-ssid-wmm-ac_bk_stats_wmmfailedsent

- case file: `D517_ac_bk_stats_wmmfailedsent.yaml`
- answer row: `517`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedSent.` / `AC_BK`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedSent.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Fail` / `Pass`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Pass` / `Fail` / `Pass`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `6g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d517-ssid-wmm-ac_bk_stats_wmmfailedsent.json`

### d518-ssid-wmm-ac_vi_stats_wmmfailedsent

- case file: `D518_ac_vi_stats_wmmfailedsent.yaml`
- answer row: `518`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedSent.` / `AC_VI`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedSent.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Pass` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Pass` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d518-ssid-wmm-ac_vi_stats_wmmfailedsent.json`

### d519-ssid-wmm-ac_vo_stats_wmmfailedsent

- case file: `D519_ac_vo_stats_wmmfailedsent.yaml`
- answer row: `519`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmFailedSent.` / `AC_VO`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmFailedSent.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d519-ssid-wmm-ac_vo_stats_wmmfailedsent.json`

### d520-ssid-wmm-ac_be_stats_wmmpacketsreceived

- case file: `D520_ac_be_stats_wmmpacketsreceived.yaml`
- answer row: `520`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_BE`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF between Station "iperf3 -c 192.168.1.1 -u -b 20M " 3. Verify SSID Stats WmmPacketsReceived root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.WmmPacke...
- 0401 H excerpt: === wl0 === AC_BE: tx frames: 45499 bytes: 36437621 failed frames: 0 failed bytes: 0 rx frames: 18129 bytes: 26231742 failed frames: 0 failed bytes: 0 === wl1 === AC_BE: tx frames: 50782 bytes: 37665998 failed frames: 0 failed bytes: 0 r...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d520-ssid-wmm-ac_be_stats_wmmpacketsreceived.json`

### d521-ssid-wmm-ac_bk_stats_wmmpacketsreceived

- case file: `D521_ac_bk_stats_wmmpacketsreceived.yaml`
- answer row: `521`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_BK`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF iperf3 -c 192.168.1.1 -u -b 20M --tos 0x20 3. Verify SSID stats WmmPacketsReceived.AC_BK root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.WmmPackets...
- 0401 H excerpt: === wl0 === AC_BK: tx frames: 19670 bytes: 51820236 failed frames: 0 failed bytes: 0 rx frames: 17259 bytes: 26199340 failed frames: 0 failed bytes: 0 === wl1 === AC_BK: tx frames: 39877 bytes: 103534322 failed frames: 0 failed bytes: 0 ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d521-ssid-wmm-ac_bk_stats_wmmpacketsreceived.json`

### d522-ssid-wmm-ac_vi_stats_wmmpacketsreceived

- case file: `D522_ac_vi_stats_wmmpacketsreceived.yaml`
- answer row: `522`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_VI`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0x88" 3. Verify SSID stats WmmPacketsReceived.AC_VI=0 root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.WmmPacketsRec...
- 0401 H excerpt: === wl0 === AC_VI: tx frames: 34558 bytes: 51766446 failed frames: 0 failed bytes: 0 rx frames: 17205 bytes: 26495350 failed frames: 0 failed bytes: 0 === wl1 === AC_VI: tx frames: 34536 bytes: 51733490 failed frames: 0 failed bytes: 0 r...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d522-ssid-wmm-ac_vi_stats_wmmpacketsreceived.json`

### d523-ssid-wmm-ac_vo_stats_wmmpacketsreceived

- case file: `D523_ac_vo_stats_wmmpacketsreceived.yaml`
- answer row: `523`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_VO`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmPacketsReceived.` / `AC_VO`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0xB8" 3. Verify SSID stats WmmPacketsReceived.AC_VO root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.WmmPacketsR...
- 0401 H excerpt: === wl0 === AC_VO: tx frames: 34553 bytes: 51750513 failed frames: 0 failed bytes: 0 rx frames: 17428 bytes: 26453929 failed frames: 0 failed bytes: 0 === wl1 === AC_VO: tx frames: 51806 bytes: 77598569 failed frames: 0 failed bytes: 0 r...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d523-ssid-wmm-ac_vo_stats_wmmpacketsreceived.json`

### d524-ssid-wmm-ac_be_stats_wmmpacketssent

- case file: `D524_ac_be_stats_wmmpacketssent.yaml`
- answer row: `524`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmPacketsSent.` / `AC_BE`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmPacketsSent.` / `AC_BE`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF between Station "iperf3 -c 192.168.1.1 -u -b 20M " 3. Verify SSID Stats.WmmPacketsSent.AC_BE root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.WmmPac...
- 0401 H excerpt: === wl0 === AC_BE: tx frames: 45499 bytes: 36437621 failed frames: 0 failed bytes: 0 rx frames: 18129 bytes: 26231742 failed frames: 0 failed bytes: 0 === wl1 === AC_BE: tx frames: 50782 bytes: 37665998 failed frames: 0 failed bytes: 0 r...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d524-ssid-wmm-ac_be_stats_wmmpacketssent.json`

### d525-ssid-wmm-ac_bk_stats_wmmpacketssent

- case file: `D525_ac_bk_stats_wmmpacketssent.yaml`
- answer row: `525`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmPacketsSent.` / `AC_BK`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmPacketsSent.` / `AC_BK`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect two WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF iperf3 -c 192.168.1.1 -u -b 20M --tos 0x20 3. Verify SSID stats WmmPacketsSent.AC_BK root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.WmmPacketsSent...
- 0401 H excerpt: === wl0 === AC_BK: tx frames: 19670 bytes: 51820236 failed frames: 0 failed bytes: 0 rx frames: 17259 bytes: 26199340 failed frames: 0 failed bytes: 0 === wl1 === AC_BK: tx frames: 39877 bytes: 103534322 failed frames: 0 failed bytes: 0 ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d525-ssid-wmm-ac_bk_stats_wmmpacketssent.json`

### d526-ssid-wmm-ac_vi_stats_wmmpacketssent

- case file: `D526_ac_vi_stats_wmmpacketssent.yaml`
- answer row: `526`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.Stats.WmmPacketsSent.` / `AC_VI`
- workbook metadata: `WiFi.SSID.{i}.Stats.WmmPacketsSent.` / `AC_VI`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Connect WiFi station (use another WiFi7 GW as station with built-in IPERF3) 2. Run IPERF "iperf3 -c <server> -u -b 20M --tos 0x88" 3. Verify SSID stats WmmPacketsSent.AC_VI=0 root@prplOS:/# ubus-cli WiFi.SSID.*.Stats.WmmPacketsSent.AC...
- 0401 H excerpt: === wl0 === AC_VI: tx frames: 34558 bytes: 51766446 failed frames: 0 failed bytes: 0 rx frames: 17205 bytes: 26495350 failed frames: 0 failed bytes: 0 === wl1 === AC_VI: tx frames: 34536 bytes: 51733490 failed frames: 0 failed bytes: 0 r...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d526-ssid-wmm-ac_vi_stats_wmmpacketssent.json`

### d588-ssid-mldunit

- case file: `D588_mldunit.yaml`
- answer row: `588`
- mapping status: `exact`
- source metadata: `WiFi.SSID.{i}.` / `MLDUnit`
- workbook metadata: `WiFi.SSID.{i}.` / `MLDUnit`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: 1. Power ON the GW 2. Verify MLDUnit root@prplOS:/# ubus-cli WiFi.SSID.*.MLDUnit? > WiFi.SSID.*.MLDUnit? WiFi.SSID.1.MLDUnit=-1 WiFi.SSID.2.MLDUnit=-1 WiFi.SSID.3.MLDUnit=-1 WiFi.SSID.4.MLDUnit=0 WiFi.SSID.5.MLDUnit=-1 WiFi.SSID.6.MLDUni...
- 0401 H excerpt: root@prplOS:/# wl -i wl0 mld_unit 0 root@prplOS:/# wl -i wl1 mld_unit 0 root@prplOS:/# wl -i wl2 mld_unit 0 root@prplOS:/# wl -i wl1 mlo scb_stats 02:10:5E:8B:5B:00 [VER 2] STA 02:10:5E:8B:5B:00 link_id : 0 1 2 Tx Stats: tx_pkts_acked : ...
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d588-ssid-mldunit.json`

### d600-wifi7starole-nstrsupport

- case file: `D600_nstrsupport_capabilities_wifi7starole.yaml`
- answer row: `600`
- mapping status: `exact`
- source metadata: `WiFi.Radio.{i}.Capabilities.WiFi7STARole.` / `NSTRSupport`
- workbook metadata: `WiFi.Radio.{i}.Capabilities.WiFi7STARole.` / `NSTRSupport`
- final status: `Fail`
- evaluation verdict: `Pass`
- attempts used: `1`
- actual raw: `Fail` / `Fail` / `Fail`
- expected raw: `Pass` / `Pass` / `Pass`
- actual normalized: `Fail` / `Fail` / `Fail`
- expected normalized: `Pass` / `Pass` / `Pass`
- mismatch bands: `5g, 6g, 2.4g`
- 0401 G excerpt: (empty)
- 0401 H excerpt: (empty)
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351/d600-wifi7starole-nstrsupport.json`
