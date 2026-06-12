# EDH Deck Builder Agent

万智牌 Commander/EDH 自动构筑智能体。项目使用本地 Scryfall 全卡数据库、Commander Spellbook 公开 combo、本地规则型 combo 合成、Commander 合法性校验、规则知识上下文和启发式评分器，生成可解释的 100 张 EDH 牌表。

## 功能

- 同步 Scryfall Oracle 全卡数据到本地 SQLite。
- 同步 Commander Spellbook 公开 combo。
- 根据本地卡库按规则模板合成候选 combo。
- 校验 EDH 基础合法性：100 张、singleton、颜色认同、Commander 合法性、禁卡。
- 按主将、预算、强度、combo 偏好和 meta 环境构筑。
- 按颜色轮、功能比例、曲线、预算和 meta 对单卡评分。
- 输出构筑审计：目标比例、实际比例、非地曲线、颜色源、已知价格。
- 输出每张牌的投入理由。
- 默认排除 Universes Beyond / 特殊 IP 牌，可手动允许。
- 提供中文网页、CLI 和 FastAPI。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 数据同步

首次使用需要同步卡牌数据库：

```powershell
python -m edh_builder.cli sync-scryfall
```

同步公开 combo：

```powershell
python -m edh_builder.cli sync-spellbook
```

如果已经有缓存文件，可以本地导入：

```powershell
python -m edh_builder.cli import-scryfall-file ".cache\scryfall-oracle-cards.json"
python -m edh_builder.cli import-spellbook-file ".cache\spellbook-variants.json"
```

## 运行网页

```powershell
uvicorn edh_builder.api:app --reload
```

打开：

```text
http://127.0.0.1:8000/
```

网页会询问主将、主题、预算、强度、combo 偏好、meta 环境、必带牌、排除牌，以及是否允许特殊 IP 牌。

## 接入 LLM

不配置 API 时，工具会使用本地 fallback 规划和评分器。配置 LLM API 后，模型会参与构筑规划阶段。

默认支持 OpenAI，也支持 OpenAI-compatible `/chat/completions` 格式的服务，例如 DeepSeek、OpenRouter、Moonshot/Kimi、SiliconFlow 等。

复制配置模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，填入自己的 API key：

```text
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

检查当前是否已接入：

```powershell
python -m edh_builder.cli llm-status
```

修改 `.env` 后需要重启网页服务。

其他兼容服务示例：

```text
# DeepSeek
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# OpenRouter
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-your-openrouter-key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4.1-mini
```

旧版 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 仍然兼容。

## CLI 用法

交互式构筑：

```powershell
python -m edh_builder.cli wizard
```

直接构筑：

```powershell
python -m edh_builder.cli build `
  --commander "Muldrotha, the Gravetide" `
  --theme "graveyard value recursion" `
  --budget 300 `
  --power-level 7 `
  --combo-preference balanced `
  --meta-profile graveyard `
  --format markdown
```

查询公开 combo：

```powershell
python -m edh_builder.cli search-combos --identity GU --theme "storm mana" --limit 10
```

查看 LLM 规则上下文：

```powershell
python -m edh_builder.cli rules-context --commander "Muldrotha, the Gravetide" --theme "graveyard recursion"
```

估算牌表价格：

```powershell
python -m edh_builder.cli estimate-deck ".cache\last-deck.txt"
```

## API

接口文档：

```text
http://127.0.0.1:8000/docs
```

主要接口：

```text
POST /decks/build
POST /rules/context
GET  /cards/search
GET  /health
```

`/decks/build` 请求示例：

```json
{
  "commander": "Muldrotha, the Gravetide",
  "theme": "graveyard value recursion",
  "budget": 300,
  "power_level": 7,
  "allow_infinite": true,
  "combo_preference": "balanced",
  "meta_profile": "graveyard",
  "meta_notes": "graveyard decks and creature decks are common",
  "allow_universes_beyond": false,
  "must_include": [],
  "avoid": []
}
```

## 本地文件

不会进入 Git：

```text
edh_builder.sqlite3
.cache/
dist/
```

源码与配置：

```text
edh_builder/
data/
web/
tests/
docs/
```

## 打包

运行测试并生成干净 zip：

```powershell
.\scripts\package.ps1
```

产物会写入 `dist/`，不会包含本地数据库、缓存和旧打包文件。

## 数据源

- Scryfall Bulk Data: https://scryfall.com/docs/api/bulk-data
- Scryfall Card Objects: https://scryfall.com/docs/api/cards
- Commander Rules: https://mtgcommander.net/index.php/rules/
- Magic Comprehensive Rules: https://magic.wizards.com/en/rules
- Commander Spellbook: https://commanderspellbook.com/

## 当前定位

这是一个可运行的初版 EDH 构筑智能体。它现在会给出每张牌的投入理由，并用颜色轮、功能比例、预算、meta 和 combo 机会成本来约束构筑。它仍然是启发式构筑器，不是完整对局模拟器；高强度牌表仍建议人工复核和多轮精修。
