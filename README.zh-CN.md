# Codex-Copilot

[![Codex Desktop](https://img.shields.io/badge/Codex-Desktop-412991?logo=openai&logoColor=white)](https://openai.com/codex/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![许可证](https://img.shields.io/badge/许可证-MIT-f59e0b)](LICENSE)

**给大任务准备的一位友好空管。** 它帮助 Codex 判断：什么时候该请子代理、什么时候该专注自己做，以及该为最终验证留下多少 token。

[English](README.md)

> 面向 macOS 或 Linux 上的 **Codex Desktop**。

## 30 秒开始

想先试试、又不想改任何设置？只安装 Skill 指令即可：

```bash
npx skills add EricArcha/Codex-Copilot --skill codex-copilot -g --copy -y
```

然后直接对 Codex 说：

```text
$codex-copilot 帮我把这个功能从头做到验证完成。
```

就这样。不会新增 agents、CLI 文件，也不会修改 Codex 设置。

## 想开启完整驾驶舱？

完整安装是可选的：它会加入六个自定义 agents、`codex-copilot` 命令，以及少量多代理所需的 Codex 受管设置。

```bash
git clone https://github.com/EricArcha/Codex-Copilot.git
cd Codex-Copilot
./bin/codex-copilot install --dry-run  # 先看看会发生什么
./bin/codex-copilot install            # 在终端确认后安装
```

安装器会在改动前展示每个文件动作和全部六项受管设置。脚本或 CI 中，请先审阅 dry-run，再加 `--yes` 确认。

<details>
<summary>会改哪些 Codex 设置？</summary>

- 开启多代理能力
- 最多同时运行 3 个子代理任务
- 使用轻量默认子代理（`gpt-5.6-luna`、low reasoning）
- 选择 standard service tier，并关闭 fast mode

安装前的值会被记录，用于安全恢复。
</details>

## 它在做什么？

```text
理解任务 → 选最小但有用的小队 → 守住 token 预算 → 独立验证 → 带着证据交付
```

Codex-Copilot 有一点固执：它宁愿把一个改动扎实地做完，也不愿让一群 agents 为了小事四处乱跑。

## 安全删除

要卸载完整工作流，请运行：

```bash
codex-copilot uninstall
```

它只删除自己安装的文件；某项设置只有在你安装后没有再修改时，才会被还原。

**手动删除 `~/.agents/skills/codex-copilot` 只会移除 Skill，不会还原 Codex 设置。** 请运行 `codex-copilot uninstall`。如果这个命令也没有了，重新 clone 本仓库后运行：

```bash
./bin/codex-copilot uninstall
```

恢复完成前请保留 `~/.codex-copilot`——里面有逐项安全还原所需的记录。

## 常用命令

```bash
codex-copilot doctor       # 都准备好了吗？
codex-copilot status       # 额度还剩多少？
codex-copilot profile show # 当前使用哪种路由风格？
```

Codex-Copilot 不会兑换用量重置额度。本地只保存私密的路由摘要：不记录提示词、代码、命令输出或原始项目路径。

## 贡献者

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
