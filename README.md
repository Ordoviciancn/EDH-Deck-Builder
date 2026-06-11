# EDH Builder Agent

一个用于自动构筑万智牌 Commander/EDH 套牌的基础工程。它把公开卡牌数据库、Commander 合法性规则、公开/自创 combo 知识库和 LLM 智能体拆成可替换模块，方便后续继续接入更强的评分模型和对局模拟。

## 当前能力

- 从 Scryfall Bulk Data 获取全卡 Oracle 数据，并写入本地 SQLite。
- 基于 Scryfall `legalities.commander` 获取 Commander 禁用/合法状态。
- 校验 EDH 基础规则：100 张、singleton、颜色认同、Commander 合法性、禁卡。
- 通过 EDHREC 排名、本地常用牌清单、角色规则和主题协同综合评分。
- 接入公开 combo 和自创 combo 的统一 JSONL 存储。
- 提供 LLM 智能体接口：有 API key 时让 LLM 生成构筑计划；无 key 时使用启发式构筑。
- 支持 combo 体系化：从公开 combo 中选择组件，并补充导师、保护和 payoff。
- 支持 meta 定制：creature/combo/control/graveyard/artifact/stax 等环境会改变配额和评分。
- 提供 CLI 和 FastAPI 入口。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 下载并索引 Scryfall Oracle Cards，全量文件较大，首次运行需要等待
python -m edh_builder.cli sync-scryfall

# 查看指挥官候选
python -m edh_builder.cli search "Muldrotha, the Gravetide"

# 构筑一套 EDH 套牌
python -m edh_builder.cli build --commander "Muldrotha, the Gravetide" --theme "graveyard value recursion" --budget 300

# 交互式构筑向导，会逐步询问预算、强度、combo 偏好和 meta
python -m edh_builder.cli wizard
```

启动 API：

```powershell
uvicorn edh_builder.api:app --reload
```

## LLM 配置

默认支持 OpenAI 兼容接口：

```powershell
$env:OPENAI_API_KEY="你的 key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4.1-mini"
```

如果不配置，系统会走本地启发式构筑流程，不会中断。

## Combo 数据

公开 combo 可通过 Commander Spellbook bulk JSON 接入。同步命令：

```powershell
python -m edh_builder.cli sync-spellbook
```

如果已经下载了 bulk JSON，可以从本地缓存导入：

```powershell
python -m edh_builder.cli import-spellbook-file ".cache\spellbook-variants.json"
```

查看某个颜色组合/主题下的公开 combo：

```powershell
python -m edh_builder.cli search-combos --identity GU --theme "storm mana" --limit 10
```

估算 decklist 当前已知美元价格：

```powershell
python -m edh_builder.cli estimate-deck ".cache\last-deck.txt"
```

自创 combo 或其他公开来源也可以使用统一 JSONL 格式：

```json
{"name":"Example Loop","cards":["Card A","Card B"],"result":"Infinite mana","source":"custom","tags":["infinite","mana"]}
```

自创 combo 放在 `data/custom_combos.jsonl`。

## 数据源说明

- Scryfall Bulk Data: https://scryfall.com/docs/api/bulk-data
- Scryfall Card Objects: https://scryfall.com/docs/api/cards
- Commander Rules: https://mtgcommander.net/index.php/rules/
- Commander Spellbook: https://commanderspellbook.com/about/
