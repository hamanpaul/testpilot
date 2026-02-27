# TestPilot — 嵌入式裝置自動化測試站框架

## 問題與目標

建立一套 plugin-based 測試自動化框架（`~/testpilot/`），以 orchestrator + plugin + YAML descriptor 三層架構，
支援多裝置協調測試（DUT、STA、EndpointPC），初期實作 Wifi_LLAPI plugin，後續可擴展至 QoS LLAPI、
WFA Sigma/QT、CDRouter、EasyMesh 等測試類型。

靈感來自 OpenClaw 的「龍蝦架構」，但核心轉為嵌入式硬體測試站的自動化駕駛。

---

## 架構設計

```
                    ┌─────────────────────┐
                    │    TestPilot CLI     │
                    │  (testpilot run ...) │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Orchestrator      │
                    │  ┌───────────────┐  │
                    │  │ Plugin Loader │  │
                    │  │ Test Planner  │  │
                    │  │ Monitor       │  │
                    │  │ Reporter      │  │
                    │  └───────────────┘  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │ wifi_llapi │   │ qos_llapi  │   │  sigma_qt  │  ← plugins/
     │  plugin    │   │  plugin    │   │  plugin    │
     └─────┬──────┘   └────────────┘   └────────────┘
           │
     cases/*.yaml     ← test case descriptors
           │
     ┌─────▼──────────────────────────────────┐
     │           Transport Layer              │
     │  serial_wrap │ adb │ ssh │ network     │
     └─────────────────────────────────────────┘
           │              │            │
         [DUT]          [STA]     [EndpointPC]
```

## 技術選型

| 項目 | 選擇 | 理由 |
|------|------|------|
| 語言 | Python 3.11+ | host-side orchestration, 豐富的 serial/adb/ssh 生態 |
| 套件管理 | pyproject.toml + uv | 使用者已有 uv |
| 描述檔 | YAML | 可讀性高，適合多行指令與拓撲描述 |
| 日誌 | Python logging + structured JSON log | 便於事後分析 |
| 報告 | Markdown + JSON | 人讀 + 機讀 |

## 目錄結構

```
~/testpilot/
├── pyproject.toml
├── AGENTS.md
├── README.md
├── docs/
│   ├── plan.md                       # 本計畫文件
│   ├── phases/                       # 各 phase 說明與驗收標準
│   │   ├── phase0-scaffold.md
│   │   ├── phase1-transport.md
│   │   ├── phase2-env.md
│   │   ├── phase3-engine.md
│   │   ├── phase4-wifi-plugin.md
│   │   └── phase5-cli.md
│   ├── todos.md                      # 全 todo 追蹤表
│   └── plugin-dev-guide.md           # Plugin 開發指南
├── src/
│   └── testpilot/
│       ├── __init__.py
│       ├── cli.py                    # CLI entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── orchestrator.py       # 主編排器：載入 plugin、排程測試、協調監控
│       │   ├── plugin_base.py        # PluginBase ABC：定義 plugin 介面
│       │   ├── plugin_loader.py      # 動態發現與載入 plugins/
│       │   ├── test_runner.py        # 測試執行迴圈：env_setup → execute → verify → report
│       │   ├── test_planner.py       # 解析 YAML case → 產生執行計畫
│       │   ├── monitor.py            # 系統狀態監控（溫度/CPU/RAM/RSSI）
│       │   └── reporter.py           # 報告產生器（Markdown + JSON）
│       ├── transport/
│       │   ├── __init__.py
│       │   ├── base.py               # Transport ABC
│       │   ├── serial_wrap.py        # UART/serial（包裝 serialwrap）
│       │   ├── adb.py                # ADB 介面（手機/STA 控制）
│       │   ├── ssh.py                # SSH 介面（EndpointPC/遠端裝置）
│       │   └── network.py            # 網路工具（ping/iperf/arping）
│       ├── env/
│       │   ├── __init__.py
│       │   ├── topology.py           # 拓撲圖：裝置角色與連線關係
│       │   ├── provisioner.py        # 環境佈建：依 YAML 設定 DUT/STA
│       │   └── validator.py          # 環境自檢：驗證連線/服務就緒
│       └── schema/
│           ├── __init__.py
│           └── case_schema.py        # YAML case schema 驗證
├── plugins/
│   └── wifi_llapi/
│       ├── __init__.py
│       ├── plugin.py                 # WifiLlapiPlugin(PluginBase)
│       └── cases/
│           ├── _template.yaml        # Case 範本
│           ├── getRadioStats.yaml    # 實際 test case
│           └── kickStation.yaml      # 實際 test case
├── configs/
│   ├── testbed.yaml                  # 測試台拓撲定義（DUT IP/port, STA, EndpointPC）
│   └── defaults.yaml                 # 全域預設值（timeout, retry, bands）
├── reports/                          # 自動產生的測試報告（.gitignore）
└── tests/                            # 單元測試
    ├── test_plugin_loader.py
    ├── test_case_schema.py
    └── test_topology.py
```

## Test Case YAML Schema

```yaml
# plugins/wifi_llapi/cases/getRadioStats.yaml
id: wifi-llapi-getRadioStats
name: "getRadioStats() BroadcastPacketsReceived counter"
version: "1.0"
source:
  report: "6.3.0GA_prplware_v403_LLAPI_Test_Report.xlsx"
  sheet: "Wifi_LLAPI"
  row: 191
  object: "WiFi.Radio.{i}."
  api: "getRadioStats()"

platform:
  prplos: "4.0.3"
  bdk: "6.3.1"

# --- 拓撲與連線 ---
topology:
  links:
    - from: STA
      to: DUT
      band: "5g"                       # 可為 2.4g / 5g / 6g
    - from: DUT
      to: EndpointPC
      interface: eth1

  devices:
    DUT:
      role: ap
      transport: serial               # 透過 serialwrap 控制
      config:
        - iface: "5g"
          mode: ap
          ssid: "{{SSID_5G}}"
          key: "{{KEY_5G}}"
          mlo: false
        - iface: wan
          type: ethernet
          port: eth0
        - iface: lan
          type: ethernet
          port: eth1

    STA:
      role: sta
      transport: adb                   # 透過 adb 控制手機
      config:
        - iface: "5g"
          mode: sta
          ssid: "{{SSID_5G}}"
          key: "{{KEY_5G}}"

    EndpointPC:
      role: endpoint
      transport: ssh
      config:
        - iface: eth0
          speed: "1G"

# --- 環境驗證 ---
env_verify:
  - action: ping
    from: STA
    to: DUT
    expect: pass
  - action: ping
    from: DUT
    to: EndpointPC
    expect: pass

# --- 測試步驟 ---
steps:
  - id: record_initial
    action: exec
    target: DUT
    command: |
      ubus-cli "WiFi.Radio.*.getRadioStats()" | grep BroadcastPacketsReceived
    capture: initial_counters

  - id: generate_traffic
    action: exec
    target: STA
    command: |
      arping -I {{STA_WIFI_IF}} -c 200 {{DUT_IP}}
    depends_on: record_initial
    timeout: 60

  - id: record_final
    action: exec
    target: DUT
    command: |
      ubus-cli "WiFi.Radio.*.getRadioStats()" | grep BroadcastPacketsReceived
    capture: final_counters
    depends_on: generate_traffic

# --- 通過條件 ---
pass_criteria:
  - field: final_counters.BroadcastPacketsReceived
    operator: ">"
    reference: initial_counters.BroadcastPacketsReceived
    description: "BroadcastPacketsReceived 計數器應在產生廣播流量後增加"

# --- 測試頻段 ---
bands: ["5g", "6g", "2.4g"]           # 需對三個頻段分別測試
```

## Testbed 設定檔

```yaml
# configs/testbed.yaml
testbed:
  name: "lab-bench-1"

  devices:
    DUT:
      serial:
        port: /dev/ttyUSB0
        baud: 115200
        login_prompt: "login:"
        credentials:
          user: admin
      network:
        mgmt_ip: 192.168.11.1
      platform:
        os: prplOS
        version: "4.0.3"
        vendor: broadcom
        bdk: "6.3.1"

    STA_PHONE:
      type: android
      adb_serial: "XXXXXXXXXXXXX"
      wifi_iface: wlan0

    EndpointPC:
      ssh:
        host: 192.168.11.111
        user: tester
        key: ~/.ssh/id_rsa
      iface: enx00e04c6858eb

  variables:
    SSID_5G: "TestPilot_5G"
    KEY_5G: "testpass123"
    SSID_24G: "TestPilot_24G"
    KEY_24G: "testpass123"
```

## Plugin 介面定義

```python
# src/testpilot/core/plugin_base.py
from abc import ABC, abstractmethod

class PluginBase(ABC):
    """所有測試 plugin 的抽象基底類別"""

    @property
    @abstractmethod
    def name(self) -> str:
        """plugin 名稱，如 'wifi_llapi'"""

    @property
    @abstractmethod
    def version(self) -> str:
        """plugin 版本"""

    @abstractmethod
    def discover_cases(self) -> list[dict]:
        """掃描 cases/ 目錄，回傳所有 test case 描述"""

    @abstractmethod
    def setup_env(self, case: dict, topology) -> bool:
        """依 case 描述佈建測試環境"""

    @abstractmethod
    def verify_env(self, case: dict, topology) -> bool:
        """環境自檢"""

    @abstractmethod
    def execute(self, case: dict, step: dict, topology) -> dict:
        """執行單一測試步驟"""

    @abstractmethod
    def evaluate(self, case: dict, results: dict) -> bool:
        """依 pass_criteria 評估測試結果"""

    @abstractmethod
    def teardown(self, case: dict, topology) -> None:
        """清理測試環境"""
```

## 測試執行流程

```
Orchestrator.run(plugin, cases):
  for case in cases:
    1. plugin.setup_env(case)     ── 佈建 DUT/STA/EndpointPC
    2. plugin.verify_env(case)    ── 環境自檢（ping, 連線確認）
    3. monitor.start(case)        ── 啟動背景監控（溫度/CPU/RAM/RSSI）
    4. for step in case.steps:
         result = plugin.execute(case, step)
         results[step.id] = result
    5. passed = plugin.evaluate(case, results)
    6. monitor.stop()
    7. report = reporter.generate(case, results, monitor.events)
    8. plugin.teardown(case)
    9. if passed: → 下一條 case
       else:     → 記錄失敗分析，產生報告，繼續或中止（依策略）
```

## 監控子系統

```python
# monitor 在背景 thread 定期採集（不干擾測試）
class Monitor:
    metrics = ["temperature", "cpu_usage", "memory", "traffic", "rssi"]
    interval = 10  # seconds
    # 異常時不中斷測試，僅記錄事件
    # 測試結束後 anomalies 寫入報告備註
```

## 報告格式

```
reports/
  2026-02-27T09-30_wifi-llapi_getRadioStats_v1.0.md
  2026-02-27T09-30_wifi-llapi_getRadioStats_v1.0.json
```

報告內容：
- 測試摘要（case ID, 版本, 時間, 結果）
- 環境資訊（platform, testbed topology）
- 測試步驟與執行結果（每步的 command, output, timing）
- 通過/失敗判定與分析
- 系統監控摘要與異常事件
- 失敗時的分析（條件、重現步驟、可能原因）

---

## 實作計畫（Todos）

所有計畫文件、phase 說明與 todo 追蹤都放在 `~/testpilot/docs/` 底下。

### Phase 0: 專案骨架 → 完成後 git init + push GitHub
1. **scaffold** — 建立 `~/testpilot/` 完整目錄結構、pyproject.toml、git init
2. **plugin-base** — 實作 `PluginBase` ABC 與 `PluginLoader`
3. **case-schema** — 定義 YAML case schema 與驗證邏輯
4. **testbed-config** — testbed.yaml 設定檔解析
5. **transport-base** — Transport ABC（stub 實作）
6. **skeleton-cli** — 最小 CLI entry point（`testpilot --version`、`testpilot list-plugins`）
7. **skeleton-orchestrator** — 最小 orchestrator（載入 plugin、列出 cases）
8. **wifi-plugin-stub** — wifi_llapi plugin stub + 一條範例 case YAML
9. **docs-init** — docs/plan.md、docs/todos.md、docs/phases/phase0-scaffold.md
10. **github-push** — .gitignore、README.md、AGENTS.md、git init、建立 GitHub repo、push

### Phase 1: Transport Layer
11. **serial-wrap** — serialwrap 介面封裝
12. **adb-transport** — ADB 介面封裝
13. **ssh-transport** — SSH 介面封裝
14. **network-utils** — ping/arping/iperf 工具

### Phase 2: 環境管理
15. **topology** — 拓撲圖解析與裝置管理
16. **provisioner** — 環境佈建（依 YAML 設定 DUT/STA）
17. **validator** — 環境自檢

### Phase 3: 核心引擎
18. **test-runner** — 測試執行迴圈
19. **monitor** — 系統狀態監控
20. **reporter** — 報告產生器

### Phase 4: Wifi_LLAPI Plugin
21. **wifi-plugin** — WifiLlapiPlugin 完整實作
22. **case-getRadioStats** — getRadioStats() test case YAML
23. **case-kickStation** — kickStation() test case YAML

### Phase 5: CLI 與整合
24. **cli-full** — testpilot CLI 完整子命令（run/list/report）
25. **orchestrator-full** — 主編排器完整整合
26. **integration-test** — 端對端整合測試（mock transport）
