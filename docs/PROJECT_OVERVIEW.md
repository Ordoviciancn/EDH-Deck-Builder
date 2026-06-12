# 项目概览

## 目标

EDH Deck Builder Agent 是一个 Commander/EDH 自动构筑工具。它把本地全卡数据、公开 combo、规则知识、颜色轮、功能比例和单卡评分组合起来，生成可校验、可解释、可导出的 EDH 牌表。

## 架构

```text
用户输入
  -> 中文网页 / CLI / API
  -> BuildRequest
  -> Scryfall 本地卡库过滤
  -> Commander Spellbook combo 检索
  -> 本地规则型 combo 合成
  -> 规则知识上下文
  -> LLM 规划或本地启发式规划
  -> 颜色轮/比例/预算/meta 评分器选牌
  -> EDH 合法性校验
  -> Markdown / decklist 输出
```

## 核心模块

- `edh_builder/api.py`：FastAPI 服务和中文网页入口。
- `edh_builder/cli.py`：命令行工具和交互式 wizard。
- `edh_builder/deck_builder.py`：构筑器、评分器、颜色轮、功能比例、combo package、meta 定制。
- `edh_builder/repository.py`：SQLite 卡牌和 combo 查询。
- `edh_builder/scryfall.py`：Scryfall bulk 数据同步。
- `edh_builder/combo_importer.py`：Commander Spellbook / 自定义 combo 导入。
- `edh_builder/rules.py`：EDH 合法性校验。
- `edh_builder/rules_knowledge.py`：给 LLM 使用的规则上下文裁剪。
- `edh_builder/exporters.py`：分组牌表、构筑审计和单卡理由导出。
- `web/index.html`：中文网页构筑向导。

## 数据文件

- `data/edh_staples.json`：EDH 常用牌与角色白名单。
- `data/tag_rules.json`：基础标签规则。
- `data/custom_combos.jsonl`：自定义 combo。
- `data/rules_knowledge.md`：Commander、颜色认同、倾曳、免费施放、复制、combo 裁定等规则说明。

## 当前能力

- 读取本地 Scryfall 全卡数据库。
- 读取 Commander Spellbook 公开 combo。
- 从本地卡库按规则模板合成候选 combo。
- 校验 EDH 合法性。
- 按预算、强度、combo 偏好和 meta 环境构筑。
- 按颜色轮和功能比例约束选牌。
- 输出 combo package：组件、导师、保护、payoff、来源和规则逻辑。
- 输出构筑审计：目标比例、实际比例、曲线、颜色源和已知价格。
- 输出每张牌的投入理由。
- 默认排除 Universes Beyond / 特殊 IP 牌。
- 提供网页、CLI 和 API。

## 当前限制

- 评分器仍是启发式，不是完整对局模拟结果。
- 总价控制使用已知 Scryfall 价格，缺价牌仍需要人工复核。
- 自构 combo 目前覆盖常见规则模板，复杂三卡以上 loop 还需要扩展。
- 主将专属评分还可以继续细化。
- 还没有 Moxfield / Archidekt 文件级导出和多轮自动换牌精修。

## 下一步

1. 增加多轮“找弱牌、换牌、重新校验”的迭代器。
2. 扩展本地规则型 combo 模板。
3. 增加主将专属评分配置。
4. 增加 Moxfield / Archidekt 导出。
5. 增加 goldfish 统计和起手评估。
