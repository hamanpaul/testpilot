# TestPilot — Todo 追蹤

## Phase 0: 專案骨架（→ GitHub push）

| ID | 項目 | 狀態 |
|----|------|------|
| scaffold | 目錄結構、pyproject.toml | done |
| plugin-base | PluginBase ABC + PluginLoader | done |
| case-schema | YAML case schema 驗證 | done |
| testbed-config | testbed.yaml 解析 | done |
| transport-base | Transport ABC + StubTransport | done |
| skeleton-cli | 最小 CLI (--version, list-plugins) | done |
| skeleton-orchestrator | 最小 orchestrator | done |
| wifi-plugin-stub | wifi_llapi stub + 範例 cases | done |
| docs-init | docs/ 文件初始化 | done |
| github-push | git init + push GitHub | pending |

## Phase 1: Transport Layer

| ID | 項目 | 狀態 |
|----|------|------|
| serial-wrap | serialwrap UART 介面 | pending |
| adb-transport | ADB 介面 | pending |
| ssh-transport | SSH 介面 | pending |
| network-utils | ping/arping/iperf | pending |

## Phase 2: 環境管理

| ID | 項目 | 狀態 |
|----|------|------|
| topology | 拓撲圖解析 | pending |
| provisioner | 環境佈建 | pending |
| validator | 環境自檢 | pending |

## Phase 3: 核心引擎

| ID | 項目 | 狀態 |
|----|------|------|
| test-runner | 測試執行迴圈 | pending |
| monitor | 系統監控 | pending |
| reporter | 報告產生器 | pending |

## Phase 4: Wifi_LLAPI Plugin

| ID | 項目 | 狀態 |
|----|------|------|
| wifi-plugin | 完整實作 | pending |
| case-getRadioStats | getRadioStats() YAML | done |
| case-kickStation | kickStation() YAML | done |

## Phase 5: CLI 與整合

| ID | 項目 | 狀態 |
|----|------|------|
| cli-full | 完整 CLI 子命令 | pending |
| orchestrator-full | 完整編排器 | pending |
| integration-test | 端對端整合測試 | pending |
