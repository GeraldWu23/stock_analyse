# 从取数到结论：可拆开的步骤和命令

这个项目有两套东西叠在一起：

1. **本仓库持仓管线**（`portfolio/`）：账本、现价、ETF 篮子、财报/K 线、本地 66 评委规则。**不调用大模型。**
2. **stock-deep-analyzer 插件**（`.cursor/plugins/stock-deep-analyzer`，UZI-Skill）：个股 22 维采集、机构建模、规则骨架分、HTML 报告。脚本可以单独跑；**深度档中间要大模型介入。**

上面再套一层 **agent skill**（`.cursor/skills/`）：人说 `/portfolio-deep-analysis` 或 `/stock-deep-analyzer:analyze-stock` 时，由模型决定先跑哪条命令、再写结论。Skill 本身不是命令。

下面每一步尽量只做一件事，可以单独重跑。命令都从**仓库根目录**出发。Python 用当前环境里的解释器（`python` / `python3` / `.venv/bin/python`）。

---

## 怎么分类

| 类型 | 含义 | 谁在算 |
| --- | --- | --- |
| **取数** | 拉公开行情/财报/成分，或用公式打分 | 脚本。不编故事 |
| **规则打分** | 读已落地的 JSON，按写死的规则出分 | 脚本。不是大模型 |
| **大模型分析** | 读 JSON、检索、写判断、覆盖评委、出建议表 | Agent。没有一条「分析.exe」 |

ETF / LOF 是篮子：**不要**走个股 66 评委、不要走个股 DCF。

---

## A. 本仓库持仓管线（不大模型）

账本不靠命令生成。改份额只在用户明确说已成交之后。

| 编号 | 环节 | 类型 | 命令 | 产物 |
| --- | --- | --- | --- | --- |
| A0 | 看账本 | 取数（本地文件） | `sed -n '1,80p' portfolio/HOLDINGS.md`（真实）或 `sed -n '1,80p' portfolio/simulated/HOLDINGS.md`（模拟） | 份额、成本、现金。机器副本：`portfolio/holdings.json` / `portfolio/simulated/holdings.json` |
| A1 | 只刷新现价/昨收 | 取数 | `python -m portfolio.collect --quotes-only` | `portfolio/collected/latest.json`（及当日 `YYYY-MM-DD.json`）。市值 = 份额 × 现价；今日盈亏 = (现价 − 昨收) × 份额 |
| A1s | 同上，模拟仓 | 取数 | `python -m portfolio.collect --simulated --quotes-only` | 同一目录，账户字段为模拟仓 |
| A2 | 现价 + ETF 篮子 | 取数 | `python -m portfolio.collect` | 在 A1 基础上加 IOPV、溢折价、前十大（定期报告，不是每日 PCF） |
| A2s | 同上，模拟仓 | 取数 | `python -m portfolio.collect --simulated` | 同上 |
| A3 | 只拉一只 | 取数 | `python -m portfolio.collect --name 南方航空`（可再加 `--quotes-only`） | `latest.json` 里只有这一行 |
| A4 | 个股财报 + K 线 | 取数 | `python -m portfolio.collect --fundamentals`（可加 `--name 南方航空`） | `portfolio/collected/<代码>/raw_data.json`。ETF 自动跳过 |
| A5 | 本地 66 评委 | 规则打分 | `python -m portfolio.judges` 或 `python -m portfolio.judges --name 南方航空` | `portfolio/collected/judges-latest.json`；笔记 `portfolio/analysis/judges-YYYY-MM-DD.md` 或 `南方航空-规则引擎-YYYY-MM-DD.md` |
| A6 | 一只股票三步打包 | 取数 + 规则 | `python -m portfolio.analyze --name 南方航空` | 连续做 A1（该名）→ A4 → A5 |

**现价链路（A1/A2，脚本内，不是另开进程）：**

- 港股：腾讯 `r_hk` → 新浪 → 东财 → Yahoo
- A 股：东财 → 腾讯/新浪 → Yahoo
- ETF：东财（IOPV/篮子）→ 现价空了再用腾讯/新浪

只盯盘、不写持仓快照：仓库根目录的 `python fetch_quotes.py` 或 `python schedule_quotes.py --cron "..."`。那是定时器，**不要**代替 `portfolio.collect`。`conda activate` 之后请用 `python`，不要用系统 `python3`（macOS 常指向 CommandLineTools，找不到仓库里的脚本）。

A5 读的是 A4 的 `raw_data.json`。没有缓存会直接报错，不会偷偷再去网上拉。

---

## B. 插件个股管线（脚本取数 / 规则 + 可选大模型）

先进入插件再跑 Python（路径不要猜）：

```bash
cd .cursor/plugins/stock-deep-analyzer
```

缓存和报告默认 gitignore：

- 数据：`skills/deep-analysis/scripts/.cache/<ticker>/`
- HTML：`skills/deep-analysis/scripts/reports/`

### B1. 取数（可单维拆开）

| 编号 | 环节 | 类型 | 命令 | 产物 |
| --- | --- | --- | --- | --- |
| B1.0 | 装依赖 | 环境 | `python -m pip install -r .cursor/plugins/stock-deep-analyzer/requirements.txt` | 当前环境里的 akshare / yfinance 等 |
| B1.1 | 单维采集 | 取数 | `cd .cursor/plugins/stock-deep-analyzer/skills/deep-analysis/scripts && python fetch_basic.py 600029.SH` | 该 fetcher 写入 `.cache/`。同类：`fetch_financials.py`、`fetch_kline.py`、`fetch_lhb.py` 等共约 22 个 |
| B1.2 | Stage 1（采集+建模+骨架分） | 取数 + 规则 | `cd .cursor/plugins/stock-deep-analyzer/skills/deep-analysis/scripts && python -c "from run_real_test import stage1; stage1('600029.SH')"` | `raw_data.json`、建模结果、`dimensions.json`、`panel.json`（规则骨架，还不是大模型评语） |
| B1.3 | CLI 一把出报告（lite/medium） | 取数 + 规则 + 模板 | `python .cursor/plugins/stock-deep-analyzer/run.py 600029.SH --depth lite --no-browser` | HTML。评委是规则引擎，**没有** role-play |
| B1.4 | CLI medium（默认「分析 XX」） | 同上 | `python .cursor/plugins/stock-deep-analyzer/run.py 600029.SH --no-browser` | 更全的 HTML，仍可不经大模型 |

`stage1` 内部顺序：Task 1（22 维）→ Task 1.5（DCF/Comps/LBO 等公式）→ Task 2（维度分）→ Task 3（66 人规则骨架）。这些都是脚本。

ETF/LOF/可转债：`stage1` 应返回 `non_stock_security`，**到此停止**，不要硬跑评委。

### B2. 大模型分析（插件 deep 档，插在 stage1 和 stage2 之间）

没有单独的「大模型二进制」。对应的是 **agent 动作**；需要落地时用下面的写文件 / 再组装命令。

| 编号 | 环节 | 类型 | 对应命令或动作 | 产物 |
| --- | --- | --- | --- | --- |
| B2.1 | 读骨架、决定要不要补数据 | 大模型 | 读 `.cache/<ticker>/panel.json`、`raw_data.json`、`_data_gaps.json` | 无；决定 B2.2 / B2.3 |
| B2.2 | Playwright 补洞（可选） | 取数 | 在 `scripts/` 下按 skill 调 `autofill_via_playwright`（`UZI_PLAYWRIGHT_FORCE=1`） | 回填 `.cache/<ticker>/` |
| B2.3 | 四组评委 role-play | 大模型 | `/stock-deep-analyzer:analyze-stock 600029.SH` 或 `/stock-deep-analyzer:panel-only 600029.SH`（agent 按 skill 拆 4 组并行） | 覆盖后的 `panel.json` 字段（signal/score/headline/reasoning） |
| B2.4 | 写定性闭环 | 大模型 | 把 `agent_analysis.json` 写进 `.cache/<ticker>/`（schema 见 analyze-stock 命令） | 缺这个文件时 deep 档不算完成 |
| B2.5 | 组装最终报告 | 规则/模板 | `cd .cursor/plugins/stock-deep-analyzer/skills/deep-analysis/scripts && python -c "from run_real_test import stage2; print(stage2('600029.SH'))"` | HTML 路径。只拼已有 JSON，不再拉行情 |

`run.py --depth deep` **不能**当成「一条命令跑完深度分析」。deep 必须经过 B2.3–B2.4 再 B2.5。

其它 slash 都是 B 的切片，不是第三条管线：

| 用户命令 | 主要落在 | 脚本入口（若有） |
| --- | --- | --- |
| `/stock-deep-analyzer:quick-scan 600029` | B1 精简 + 少量规则 | `run.py <ticker> --depth lite --no-browser` |
| `/stock-deep-analyzer:dcf 600519` | 取数 + 公式 DCF；假设审查是大模型 | 见 `.cursor/commands/dcf.md` / `compute_*.py` |
| `/stock-deep-analyzer:scan-trap <ticker>` | 取数 + 规则 8 信号；叙述是大模型 | trap-detector skill |
| `/stock-deep-analyzer:panel-only <ticker>` | B1 基础取数 + B2.3 | 先 `fetch_basic.py` / `fetch_financials.py` |

---

## C. 全部持仓深度分析（skill，取数命令 + 大模型结论）

触发：`/portfolio-deep-analysis`。默认**真实持仓**。只出建议，不改账本。

| 编号 | 环节 | 类型 | 命令或动作 | 产物 |
| --- | --- | --- | --- | --- |
| C0 | 定账本 | 取数（本地） | 同 A0。未指明则真实仓 | 纳入名单 + 账本日期 |
| C1 | 刷新组合 | 取数 | 真实：`python -m portfolio.collect`；模拟：`python -m portfolio.collect --simulated` | `portfolio/collected/latest.json` |
| C2 | 个股财报 | 取数 | `python -m portfolio.collect --fundamentals` | 各 `collected/<ticker>/raw_data.json` |
| C3 | 个股规则票（可选对照） | 规则 | `python -m portfolio.judges --name 南方航空`（每只股票一条，ETF 跳过） | `portfolio/analysis/*-规则引擎-*.md` |
| C4 | 个股深析 | 大模型 | 每只股票一个并行任务；可读 A4/C2 缓存，**不要**把 ETF 丢进 B 的 66 评委。完整个股插件路径才是 B1.2→B2→B2.5 | 论点、估值、触发、失效 |
| C5 | ETF/篮子深析 | 大模型 | 每只或每组 ETF 一个任务；数据用 C1 的成分/溢折价，禁止个股 DCF | 指数、穿透、角色、仓位区间 |
| C6 | 交叉审查 | 大模型 | 四路并行：价值/成长、宏观/技术、中式价投/量化、游资/科技（不适用则跳过） | 分歧本身要保留 |
| C7 | 数据复核 | 大模型 | 独立任务勾稽期间、单位、PE/PB、成分合计 | 冲突则降为「观察」 |
| C8 | 组合建议 | 大模型 | 无脚本。按 skill 输出券商表 + 行动表 + 「尚未执行任何交易」 | 对话里的结论 |

C4–C8 **没有** `python -m portfolio.advice`。要复现结论，只能重跑 C1–C3 再让 agent 走 skill，或重开 `/portfolio-deep-analysis`。

建议本地先切到同时带 skill 和腾讯现价的分支，例如 `cursor/update-simulated-holdings-93b4`，不要从空的 `main` 开跑。

---

## 推荐串法（解耦重跑）

**只看今天涨跌、不动研究**

```bash
python -m portfolio.collect --quotes-only
# 看 portfolio/collected/latest.json 或终端表
```

**一只持仓股票，全程无大模型**

```bash
python -m portfolio.collect --name 南方航空 --quotes-only
python -m portfolio.collect --name 南方航空 --fundamentals
python -m portfolio.judges --name 南方航空
# 或一条：python -m portfolio.analyze --name 南方航空
```

**一只票要插件 HTML，不要大模型评语**

```bash
python .cursor/plugins/stock-deep-analyzer/run.py 600029.SH --no-browser
```

**一只票要深度（脚本 + 大模型）**

```bash
cd .cursor/plugins/stock-deep-analyzer/skills/deep-analysis/scripts
python -c "from run_real_test import stage1; stage1('600029.SH')"
# 然后 agent：role-play → 写 agent_analysis.json
python -c "from run_real_test import stage2; print(stage2('600029.SH'))"
```

**整本账户建议**

```bash
python -m portfolio.collect
python -m portfolio.collect --fundamentals
# 可选：python -m portfolio.judges
# 然后 /portfolio-deep-analysis 做 C4–C8
```

---

## 不要混的边界

| 不要 | 原因 |
| --- | --- |
| 对 ETF 跑 `portfolio.judges` / 插件 `stage1` 评委 | 规则是个股财务，篮子对不上 |
| 用持仓盈亏代替今日盈亏 | 今日盈亏只用昨收 |
| 用 `run.py --depth deep` 代替 B2 | deep 必须有 agent 写 `agent_analysis.json` |
| 用 `schedule_quotes.py` 当 `collect` | 调度不写组合快照、不拉篮子 |
| 大模型改 `HOLDINGS.md` 份额 | 除非用户说已经成交 |
| 指望远程仓库里有 `collected/` | 该目录 gitignore，必须本地重跑 A1–A4 |

不是持牌投顾意见。
