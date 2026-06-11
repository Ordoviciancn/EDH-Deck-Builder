# EDH Deck Builder 项目说明

## 项目目标

EDH Deck Builder 是一个面向万智牌 Commander/EDH 的自动构筑基础工程。项目目标是把公开卡牌数据库、Commander 合法性规则、公开/自创 combo 知识库和 LLM 智能体组合起来，生成可解释、可校验、可导出的 100 张 EDH 套牌。

当前版本重点完成“基础设施”：

- 本地同步 Scryfall Oracle 全卡数据库。
- 读取 Commander 合法/禁用信息。
- 执行 EDH 基础合法性校验。
- 建立卡牌角色标签、combo 种子库和构筑评分骨架。
- 提供 CLI 与 FastAPI 接口。
- 预留 LLM 智能体规划入口。

## 数据来源

### Scryfall

主要卡牌数据来自 Scryfall Bulk Data：

- 卡名
- 法术力费用
- 法术力值
- 颜色认同
- 牌张类别
- Oracle 文本
- Commander 合法性
- 价格
- 图片链接

同步命令：

```powershell
python -m edh_builder.cli sync-scryfall
```

如果已经下载过 Scryfall JSON，可以从本地文件导入：

```powershell
python -m edh_builder.cli import-scryfall-file ".cache\scryfall-oracle-cards.json"
```

### Combo 数据

自创 combo 和外部公开 combo 统一使用 JSONL 格式：

```json
{"name":"Isochron Dramatic Mana","cards":["Isochron Scepter","Dramatic Reversal"],"result":"Infinite untaps and mana when nonland mana sources produce at least three mana.","source":"seed/custom","tags":["infinite","mana","artifact"]}
```

本地种子文件：

```text
data/custom_combos.jsonl
```

同步本地 combo：

```powershell
python -m edh_builder.cli sync-combos
```

后续可以接入 Commander Spellbook 或其他公开 combo 导出源，只要转换成相同 JSONL 格式即可。

当前项目已经支持 Commander Spellbook bulk JSON：

```powershell
python -m edh_builder.cli sync-spellbook
```

如果 `.cache\spellbook-variants.json` 已经存在，可以直接导入：

```powershell
python -m edh_builder.cli import-spellbook-file ".cache\spellbook-variants.json"
```

导入后会写入本地 SQLite 的 `combos` 表，来源标记为：

```text
commander-spellbook
```

本地查询公开 combo：

```powershell
python -m edh_builder.cli search-combos --identity GU --theme "storm mana" --limit 10
```

## 智能体构筑流程

当前构筑器的工作流：

```text
用户输入
  -> 解析主将、主题、预算、强度、combo 偏好
  -> 从本地 Scryfall SQLite 读取主将
  -> 按 Commander 合法性、颜色认同、预算过滤全卡池
  -> 按主将颜色认同与主题读取 combo 知识库
  -> 选择 combo package：组件、导师、保护、payoff
  -> 根据用户 meta 调整角色配额和评分
  -> LLM 或本地启发式生成构筑计划
  -> 按角色配额选择卡牌
  -> 执行 EDH 合法性校验
  -> 输出 Markdown 或可导入 decklist
```

评分器会综合考虑：

- EDHREC 排名：优先真实 Commander 使用率高的牌。
- 角色适配：ramp、draw、removal、wipe、protection、tutor、combo、wincon 分别有独立判断。
- 常用牌清单：`data/edh_staples.json` 存放成熟 EDH 构筑常见核心牌。
- 主将协同：例如倾曳主将会提高高费瞬间/法术、delve、storm、cascade 牌的权重。
- 预算压力：低预算构筑会惩罚高价牌，并避免公开 combo 组件绕过预算限制。
- 地牌质量：优先多色地、功能地和合理数量的基本地，避免只因文本关键词塞入低质量地。

## 交互式构筑

用户可以使用 wizard 命令让智能体不断询问构筑要求：

```powershell
python -m edh_builder.cli wizard
```

当前会询问主将、核心主题、预算、目标强度、combo 偏好、是否允许无限 combo、meta 类型、meta 补充说明，以及必须加入/必须排除的牌。

## Combo 体系化

构筑器会把公开 combo 扩展为 combo package：

```text
components: 组合技核心组件
tutors: 找组件的导师或 transmute 牌
protection: 保护 combo 的反击或保护咒语
payoffs: 无限法术力、storm 或抓牌后的终结牌
```

Markdown 输出会展示本次选中的 combo package，方便用户继续追问和调整。

## Meta 定制

meta profile 会调整配额和评分：

- creature：提高去除和清场需求。
- combo：提高反击、保护、导师和低费互动。
- control：提高抽牌、保护、不可反击/闪现类牌权重。
- graveyard：提高坟场针对权重。
- artifact：提高神器/结界去除权重。
- stax：提高低费 ramp 与永久物去除需求。

角色配额位于：

```text
edh_builder/deck_builder.py
```

基础角色包括：

- lands
- ramp
- draw
- removal
- wipe
- protection
- tutor
- combo_piece
- wincon
- synergy
- flex

## LLM 配置

项目使用 OpenAI 兼容接口。没有配置 API key 时，会自动退回本地启发式构筑计划。

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4.1-mini"
```

LLM 入口：

```text
edh_builder/llm_agent.py
```

LLM 负责生成结构化计划，例如：

```json
{
  "strategy": "Cascade value plan around Quandrix, the Proof",
  "desired_tags": ["ramp", "draw", "combo_piece", "wincon"],
  "combo_cards": ["Isochron Scepter", "Dramatic Reversal", "Brain Freeze"],
  "avoid_cards": [],
  "role_weights": {}
}
```

## CLI 示例

初始化数据库：

```powershell
python -m edh_builder.cli init-db
```

搜索卡牌：

```powershell
python -m edh_builder.cli search "Quandrix, the Proof"
```

构筑套牌：

```powershell
python -m edh_builder.cli build `
  --commander "Quandrix, the Proof" `
  --theme "cascade high power budget combo" `
  --budget 100 `
  --format markdown
```

输出 Moxfield/Archidekt 可用文本：

```powershell
python -m edh_builder.cli build `
  --commander "Quandrix, the Proof" `
  --theme "cascade high power budget combo" `
  --budget 100 `
  --format decklist
```

## API 示例

启动服务：

```powershell
uvicorn edh_builder.api:app --reload
```

请求：

```http
POST /decks/build
Content-Type: application/json

{
  "commander": "Quandrix, the Proof",
  "theme": "cascade high power budget combo",
  "budget": 100,
  "power_level": 7,
  "allow_infinite": true
}
```

返回内容包括：

- commander
- plan
- validation_errors
- markdown
- decklist

## 本地文件说明

以下文件会保留在本机，但不会进入 Git：

```text
edh_builder.sqlite3
.cache/
```

原因：

- SQLite 是本地生成数据库，体积会随同步数据增长。
- `.cache/` 存放下载的 Scryfall JSON，当前文件约 176 MB。

## 当前限制

- 构筑评分已加入 EDHREC 排名、预算压力、combo package 和 meta 定制，但仍是启发式，尚未接入真实对局数据。
- 已支持 Commander Spellbook bulk JSON 导入，但还没有做增量同步和 UI 展示。
- 尚未区分纸质牌、Arena 数字专属、Universes Beyond、银边/acorn 等用户偏好过滤。
- 尚未实现细粒度预算优化，例如按总价动态替换。
- 标签系统目前基于简单文本规则，后续应升级为嵌入检索和人工标签混合方案。

## 下一步路线图

1. 增加数据过滤器：排除数字专属、acorn、Universes Beyond、指定系列。
2. 接入公开 combo 数据源，并按颜色认同和主将协同评分。
3. 改造构筑器为多轮局部搜索：先生成，再替换弱牌。
4. 增加预算优化器：确保总价不超过用户预算，而不是只按单卡价格粗过滤。
5. 增加导出格式：Moxfield、Archidekt、MTGO、纯 Markdown。
6. 为 FastAPI 增加前端页面或 Swagger 工作流示例。
7. 增加更多规则测试：partner、background、basic land 例外、特殊指挥官文本。

## Rules Knowledge for LLM

LLM planning now receives a curated rules context from:

```text
data/rules_knowledge.md
```

The context covers Commander deck construction, color identity, cascade, free casting, spell copies, combo validation, interaction categories, and meta-aware deckbuilding. It is loaded through:

```text
edh_builder/rules_knowledge.py
```

The loader trims sections according to the commander and theme. For example, a Quandrix/cascade request receives the Cascade and Quandrix-specific sections in addition to general Commander and combo rules.

Preview from CLI:

```powershell
python -m edh_builder.cli rules-context --commander "Quandrix, the Proof" --theme "cascade storm combo"
```

Preview from API:

```text
POST /rules/context
```

## Chinese Web Wizard

The local FastAPI service now serves a Chinese deckbuilding wizard at:

```text
http://127.0.0.1:8000/
```

The page exposes the same questioning process as the CLI wizard: commander, theme, budget, power level, combo preference, meta profile, meta notes, required cards, excluded cards, and whether Universes Beyond / special IP cards are allowed. No commander is pre-filled.
