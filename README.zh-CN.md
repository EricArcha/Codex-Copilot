# Codex-Copilot

[![运行环境](https://img.shields.io/badge/运行环境-Codex%20Desktop-412991?logo=openai&logoColor=white)](https://openai.com/codex/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![依赖](https://img.shields.io/badge/依赖-仅标准库-0f766e)](pyproject.toml)
[![许可证](https://img.shields.io/badge/许可证-MIT-f59e0b)](LICENSE)

**给复杂 Codex 工作准备的一座更冷静的驾驶舱。** Codex-Copilot 将实现、委派、额度与独立验证收束为一条审慎的交付路径，让「去做吧」不会变成「上下文去哪了？」

[English](README.md)

> **仅支持 Codex Desktop。** 当前版本面向 macOS 或 Linux 上的 Codex Desktop；其额度感知路由和自定义代理流程依赖 Desktop 环境，暂不支持独立 CLI 部署。

## 简介

一个仅供 Codex Desktop 使用的 Skill 与 CLI：通过配额感知路由、边界明确的子代理和独立验证，编排复杂开发工作。

## 为什么使用 Codex-Copilot？

- **守住交付终点**：预留足够的证据与审查能力，确认改动真正完成。
- **有意识地使用上下文**：只在新视角能带来价值时，才委派范围明确的工作。
- **把额度当作护栏**：根据可用额度选择路线，但绝不悄悄跳过必要验证。
- **保持指标私密**：本地指标不记录提示词、代码、路径、命令、日志或模型回复。

## 安装

需要 Python 3.11+，以及 macOS 或 Linux 上较新的 Codex CLI：

```bash
./bin/codex-copilot install
```

默认安装使用复制文件，以获得稳定的 Codex 兼容性。修改本源码仓库后，重新运行安装器即可部署更新；可用 `--dry-run` 预览操作。

```bash
./bin/codex-copilot doctor
./bin/codex-copilot status
```

本地开发时可以使用实时同步模式：

```bash
./bin/codex-copilot install --mode symlink
```

**注意：**Codex 可能拒绝符号链接形式的自定义代理配置，并报告 `agent type is currently not available`。建议优先使用默认复制模式；如需恢复，运行 `codex-copilot install --mode copy`、重启 Codex Desktop，并开启新任务。详见 [Codex 兼容性问题](https://github.com/openai/codex/issues/40131)。

安装器会将 Skill 放入 `~/.agents/skills`，在 `~/.codex/agents` 安装六个自定义代理，提供 `~/.local/bin/codex-copilot`，并安全地向 `~/.codex/config.toml` 合并少量受管配置。

## 交付路径

```text
理解范围  →  检查额度  →  路由工作  →  实现  →  独立验证
```

Codex-Copilot 对最后一步有意保持严格：实现通过，不等于已经完成独立审查的交付。

## 使用

为获得最可预测的行为，请显式调用 Skill：

```text
$codex-copilot implement this feature and verify it end to end.
```

在新的 CLI 会话中进行额度预检：

```bash
codex-copilot launch
codex-copilot launch --level complex
codex-copilot launch --level critical -- --cd /path/to/project
codex-copilot profile set premium
codex-copilot launch --profile premium --level critical
```

Codex-Copilot 从不兑换额度重置；当额度不足以保留必要测试与审查时，它会暂停高成本工作并报告自然刷新时间。

## 命令

```text
codex-copilot install [--mode copy|symlink] [--dry-run]
codex-copilot uninstall [--dry-run]
codex-copilot doctor [--json]
codex-copilot status [--json] [--refresh]
codex-copilot launch [--level routine|complex|critical] [--dry-run] [--override-quota] [-- <codex args>]
codex-copilot metrics [--days N] [--json]
codex-copilot trace [--run RUN_ID] [--json]
codex-copilot profile list|show|set <conservative|balanced|premium>
```

运行时状态存放在 `~/.codex-copilot`。指标仅在本地保存，且不含提示词、代码、原始路径、命令、日志或模型回复。

## 委派治理

每次子代理委派都会经过本地额度闸门。它会刷新额度、将子代理上限视为一次运行中的累计预算，并在允许探索前预留最终审查名额。追踪记录只保存声明的代理策略与通用生命周期状态，使用不透明 UUID 运行 ID；不保存任务内容或代理输出。超过预算必须获得用户明确授权，并在追踪中标记。

若 app-server 刷新暂时失败，闸门只能复用自身最近一次成功的 app-server 快照（60 秒 TTL），并标记为 `cache-fallback`；调用方不能自行提供额度分档或快照。

## 配置与额度

`balanced` 是默认配置：当 5 小时窗口至少剩余 50%、周窗口至少剩余 35% 时，L1/L2 工作可使用一个 Luna scout 和一个独立 Terra reviewer。受限额度（30%/20%）会将唯一名额留给审查。`conservative` 保持低成本路线；`premium` 仅在 L3 根任务与其保留的最终审查中使用 Astra，并且必须显式选择。

## 卸载

```bash
codex-copilot uninstall
```

卸载只会移除安装清单中记录的工件。只有当前配置仍与已安装值一致时才恢复受管配置；之后的用户修改会被保留。
