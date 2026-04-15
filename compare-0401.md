# compare-0401

## Inputs

- trace dirs (overlay order; later directories override earlier case results):
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T113008433351`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T132144592128`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T133308180539`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T175538121906`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T172957084134`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T174551843336`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T023259417785`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T135928729951`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T141305083695`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T142616419984`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T052709875993`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T144105373183`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T145000666925`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T020657288045`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T021655844208`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T235952361188`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T000249620932`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T164447027184`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T130448459477`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T055159421076`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T060855269192`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T022541033440`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T061743676049`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T062615392940`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T024240506323`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T063442091882`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T064002607672`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260412T231709014359`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T065809885285`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T071746618166`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T025449283775`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T075200621380`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T080405422245`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T081301178883`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T082022613657`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T083419287730`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T085025879532`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T003340845889`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T090437438519`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T092400687838`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T094515864676`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T030202219754`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T030853360475`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T095836613095`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T031458311484`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T032521733067`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T103130805176`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T105418577078`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T111530183752`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T112544193230`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T113456092168`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T115620062809`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T121358780961`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T122417812289`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T033856175894`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T035856845825`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T042647797154`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T044907394777`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T172222999250`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T111010511593`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T111624033199`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T111633789177`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T111643078674`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T111652454052`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T050318932313`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T133109929684`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T134150940705`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T140146826061`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T142054369177`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T143051719431`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T145819251839`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T150830713390`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T151631032947`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T152334632094`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T160329947246`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T161411193999`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T162439231118`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T163235194291`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T164038591687`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T165000634858`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T165326740351`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T170152736726`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T170500384375`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T171246046906`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T172459100474`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T175434503053`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T180934010938`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T200750384793`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T202052779232`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T234216396870`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T235120551775`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T203711056772`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T204926308849`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T205741105862`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T210918023652`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T214055064676`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T215500799545`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T222507260531`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T231646005774`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T212842198251`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T001339062028`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T003139523643`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T004006392874`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T004735420726`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T011605260076`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T023436252245`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T024522159981`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T025452242101`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T030233578785`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T030842726735`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T031551881401`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T032303445635`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T033619882302`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T035709687496`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T041252016188`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T042845374104`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T044008021410`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T045340433281`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T050448284344`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T051545233691`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T054920871826`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T061648225671`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T063258768736`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T070258045824`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T071500138827`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T073336901222`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T074042045965`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T074830179441`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T005520941756`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T010944709855`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T011655056430`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T012358700786`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T080003753294`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T013010016650`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T013545364055`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T081114606106`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T082800519654`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T084649232463`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T091144122493`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T092125550117`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T095013796898`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T100014840516`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T102002805516`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T103321898419`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T104126818390`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T105002687631`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T111152637870`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T112139068980`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T112956993038`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260413T005633950804`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T114636190262`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T120604251884`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T121734070494`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T122638329144`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T123614258535`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T125611587722`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T132948443340`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T134510589533`
  - `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260415T135941582307`
- answer sheet: `/home/paul_chen/prj_arc/testpilot/0401.xlsx`
- cases dir: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/cases`
- compare rule: normalize both sides so only `Pass` stays `Pass`; all other values become `Fail`.
- row mapping rule: use case `D###` number to match `0401.xlsx` worksheet row `###`.

## Summary

| metric | value |
| --- | ---: |
| compared cases | 420 |
| full matches | 385 |
| mismatch cases | 35 |
| missing answer rows | 0 |
| metadata drift rows | 43 |

## Per-band summary

| band | matched | mismatched |
| --- | ---: | ---: |
| 5g | 387 | 33 |
| 6g | 385 | 35 |
| 2.4g | 387 | 33 |

## Mismatch table

| case_id | D-row | mapping | actual raw (5/6/2.4) | expected raw (R/S/T) | actual norm | expected norm | mismatch bands |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `wifi-llapi-D020-frequencycapabilities` | 20 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `wifi-llapi-D047-supportedhe160mcs` | 47 | exact | Not Supported / N/A / N/A | Pass / Pass / Not Supported | Fail / Fail / Fail | Pass / Pass / Fail | 5g, 6g |
| `d181-radio-fragmentationthreshold` | 181 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d182-radio-rtsthreshold` | 182 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d204-radio-multiusermimoenabled` | 204 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d211-radio-operatingstandards` | 211 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d277-getscanresults-bandwidth` | 277 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d289-getscanresults-radio` | 289 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d290-getscanresults-centrechannel` | 290 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d302-getssidstats-bytesreceived` | 302 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d355-skip-addclient` | 355 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d356-skip-delclient` | 356 | exact | Skip / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d357-skip-csistats` | 357 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d359-ap-isolationenable` | 359 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d371-assocdev-disassociationtime` | 371 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d414-assocdev-rrmoffchannelmaxduration` | 414 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d415-assocdev-rrmonchannelmaxduration` | 415 | exact | Fail / N/A / N/A | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d454-getradiostats-failedretranscount` | 454 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d481-getradiostats-wmm-bytesreceived-ac_vo` | 481 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d482-getradiostats-wmm-bytessent-ac_be` | 482 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d485-getradiostats-wmm-bytessent-ac_vo` | 485 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d490-getradiostats-wmm-failedbytessent-ac_be` | 490 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
| `d508-ssid-wmm-ac_be_stats_wmmfailedbytessent_ssid` | 508 | exact | Fail / Fail / Fail | Pass / Pass / Pass | Fail / Fail / Fail | Pass / Pass / Pass | 5g, 6g, 2.4g |
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
- trace: `/home/paul_chen/prj_arc/testpilot/plugins/wifi_llapi/reports/agent_trace/20260414T165000634858/d204-radio-multiusermimoenabled.json`

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
