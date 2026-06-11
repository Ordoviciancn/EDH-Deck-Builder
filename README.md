# EDH Builder Agent

一个用于自动构筑万智牌 Commander/EDH 套牌的基础工程。它把公开卡牌数据库、Commander 合法性规则、公开/自创 combo 知识库和 LLM 智能体拆成可替换模块，方便后续继续接入更强的评分模型和对局模拟。

## 当前能力

- 从 Scryfall Bulk Data 获取全卡 Oracle 数据，并写入本地 SQLite。
- 基于 Scryfall `legalities.commander` 获取 Commander 禁用/合法状态。
- 校验 EDH 基础规则：100 张、singleton、颜色认同、Commander 合法性、禁卡。
- 通过本地标签规则识别 ramp、draw、removal、wipe、tutor、combo、wincon 等角色。
- 接入公开 combo 和自创 combo 的统一 JSONL 存储。
- 提供 LLM 智能体接口：有 API key 时让 LLM 生成构筑计划；无 key 时使用启发式构筑。
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

公开 combo 可通过导入器接入 Commander Spellbook 或其他公开来源，当前基础工程保留统一格式：

```json
{"name":"Example Loop","cards":["Card A","Card B"],"result":"Infinite mana","source":"custom","tags":["infinite","mana"]}
```

自创 combo 放在 `data/custom_combos.jsonl`。

## 数据源说明

- Scryfall Bulk Data: https://scryfall.com/docs/api/bulk-data
- Scryfall Card Objects: https://scryfall.com/docs/api/cards
- Commander Rules: https://mtgcommander.net/index.php/rules/
- Commander Spellbook: https://commanderspellbook.com/about/
