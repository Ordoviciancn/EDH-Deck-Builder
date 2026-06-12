from __future__ import annotations

from collections import defaultdict

from .models import Deck


def to_plain_text(deck: Deck) -> str:
    lines = ["Commander", f"1 {deck.commander.name}", "", "Deck"]
    for entry in sorted(deck.cards, key=lambda item: (item.role, item.card.name)):
        lines.append(f"1 {entry.card.name}")
    return "\n".join(lines)


def to_grouped_markdown(deck: Deck, validation_errors: list[str], plan: dict) -> str:
    groups: dict[str, list[str]] = defaultdict(list)
    for entry in deck.cards:
        groups[entry.role].append(entry.card.name)

    lines = [
        f"# {deck.commander.name} EDH Deck",
        "",
        f"Strategy: {plan.get('strategy', '')}",
        f"Meta: {plan.get('meta_profile', 'balanced')} {plan.get('meta_notes', '')}".strip(),
        "",
        "## Commander",
        f"- 1 {deck.commander.name}",
        "",
    ]
    _append_combo_package(lines, plan.get("combo_package"))
    _append_build_audit(lines, plan)
    _append_role_groups(lines, groups)
    _append_card_reasons(lines, deck)
    _append_validation(lines, validation_errors)
    return "\n".join(lines)


def _append_combo_package(lines: list[str], combo_package: dict | None) -> None:
    if not combo_package:
        return
    lines.extend(
        [
            "## 组合技包",
            f"- 名称: {combo_package.get('name', '')}",
            f"- 来源: {combo_package.get('source', 'public')}",
            f"- 组件: {', '.join(combo_package.get('components', []))}",
            f"- 结果: {combo_package.get('result', '')}",
            f"- 规则逻辑: {', '.join(combo_package.get('rules_logic', [])) or '公开 combo 记录'}",
            f"- 导师: {', '.join(combo_package.get('tutors', [])) or 'None'}",
            f"- 保护: {', '.join(combo_package.get('protection', [])) or 'None'}",
            f"- 终结: {', '.join(combo_package.get('payoffs', [])) or 'None'}",
            "",
        ]
    )


def _append_build_audit(lines: list[str], plan: dict) -> None:
    role_targets = plan.get("role_targets") or {}
    deck_stats = plan.get("deck_stats") or {}
    combo_search = plan.get("combo_search") or {}
    color_wheel = plan.get("color_wheel") or []
    if not (role_targets or deck_stats or color_wheel):
        return

    lines.append("## 构筑审计")
    if role_targets:
        lines.append("- 目标功能比例: " + ", ".join(f"{role} {count}" for role, count in sorted(role_targets.items())))
    if deck_stats.get("role_counts"):
        lines.append("- 实际功能比例: " + ", ".join(f"{role} {count}" for role, count in sorted(deck_stats["role_counts"].items())))
    if deck_stats.get("nonland_curve"):
        lines.append("- 非地曲线: " + ", ".join(f"{mana}费 {count}" for mana, count in deck_stats["nonland_curve"].items()))
    if deck_stats.get("estimated_color_sources"):
        lines.append("- 估算颜色源: " + ", ".join(f"{color} {count}" for color, count in deck_stats["estimated_color_sources"].items()))
    if "known_price_usd" in deck_stats:
        lines.append(f"- 已知价格合计: ${deck_stats['known_price_usd']}")
    if combo_search:
        lines.append(
            f"- Combo 搜索: 公开候选 {combo_search.get('public_candidates', 0)}，"
            f"本地规则自构候选 {combo_search.get('synthesized_candidates', 0)}"
        )
    for item in color_wheel:
        lines.append(
            f"- 颜色轮 {item.get('color')}/{item.get('name')}: "
            f"{', '.join(item.get('primary_roles', []))}；{item.get('deckbuilding_note', '')}"
        )
    lines.append("")


def _append_role_groups(lines: list[str], groups: dict[str, list[str]]) -> None:
    for role, names in sorted(groups.items()):
        lines.append(f"## {role} ({len(names)})")
        lines.extend(f"- 1 {name}" for name in sorted(names))
        lines.append("")


def _append_card_reasons(lines: list[str], deck: Deck) -> None:
    lines.append("## 单卡投入理由")
    for entry in sorted(deck.cards, key=lambda item: (item.role, item.card.name)):
        lines.append(f"- {entry.card.name} [{entry.role}]: {entry.reason}")
    lines.append("")


def _append_validation(lines: list[str], validation_errors: list[str]) -> None:
    lines.append("## Validation")
    if validation_errors:
        lines.extend(f"- ERROR: {error}" for error in validation_errors)
    else:
        lines.append("- Pass")
