# 项目概览

## 目标

EDH Deck Builder Agent 是一个 Commander/EDH 自动构筑工具。它把公开卡牌数据、公开 combo、规则知识和构筑评分器组合起来，生成可校验、可解释、可导出的 EDH 牌表。

## 架构

```text
用户输入
  -> 中文网页 / CLI / API
  -> BuildRequest
  -> Scryfall 本地卡库过滤
  -> Commander Spellbook combo 检索
  -> 规则知识上下文
  -> LLM 规划或本地启发式规划
  -> 评分器选牌
  -> EDH 合法性校验
  -> Markdown / decklist 输出
```

## 核心模块

- `edh_builder/api.py`：FastAPI 服务和中文网页入口。
- `edh_builder/cli.py`：命令行工具和交互式 wizard。
- `edh_builder/deck_builder.py`：构筑器、评分器、combo package、meta 定制。
- `edh_builder/repository.py`：SQLite 卡牌和 combo 查询。
- `edh_builder/scryfall.py`：Scryfall bulk 数据同步。
- `edh_builder/combo_importer.py`：Commander Spellbook / 自定义 combo 导入。
- `edh_builder/rules.py`：EDH 合法性校验。
- `edh_builder/rules_knowledge.py`：给 LLM 使用的规则上下文裁剪。
- `web/index.html`：中文网页构筑向导。

## 数据文件

- `data/edh_staples.json`：EDH 常用牌与角色白名单。
- `data/tag_rules.json`：基础标签规则。
- `data/custom_combos.jsonl`：自定义 combo。
- `data/rules_knowledge.md`：Commander、颜色认同、倾曳、免费施放、复制、combo 裁定等规则说明。

## 当前能力

- 读取本地 Scryfall 全卡数据库。
- 读取 Commander Spellbook 公开 combo。
- 校验 EDH 合法性。
- 按预算、强度、combo 偏好和 meta 环境构筑。
- 输出 combo package：组件、导师、保护、payoff。
- 默认排除 Universes Beyond / 特殊 IP 牌。
- 提供网页、CLI 和 API。

## 当前限制

- 评分器仍是启发式，不是对局模拟结果。
- 预算控制还不是严格购物车级别，仍需最终回算替换。
- 主将专属评分还不完整，个别主将会出现“合法但不像牌手”的选择。
- 公开 combo 需要进一步筛掉 setup 太重或实战条件过窄的组合。
- 还没有前端收藏、导出文件和多轮对话式精修。

## 下一步

1. 增加总价回算与自动替换。
2. 增加主将画像和专属评分配置。
3. 增加多轮精修：找弱牌、替换、重新校验。
4. 增加 Moxfield / Archidekt 导出。
5. 增加对局模拟或 goldfish 统计。
