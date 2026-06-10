from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from generate_lmi_daily import build_output  # noqa: E402
from generate_lmi_daily_review import unfinished_candidates  # noqa: E402
from generate_lmi_weekly_review import extract_primary_result  # noqa: E402
from lmi_focus_reminder import parse_priority_items, parse_schedule_entries  # noqa: E402


class DailyPlanStructureTests(unittest.TestCase):
    def test_unfinished_candidates_ignore_nested_notes(self) -> None:
        text = """
# 2026-06-10 LMI 日计划草案

## 事项归位

### A：重要事项
- A1: 完成 IFD-海外初步研究的最小可讨论版本
  - 交付标准：看什么问题 / 机会
  - 交付标准：现有信息与关键缺口
- A2: 候选课题收敛

### B：紧要事项
- B1: 候选课题整理
  - 说明：只做归类、收敛、优先级判断

### C：联络/追踪事项
- C1: 客户后续跟进

### D：会议/讨论/协调事项
- D1: 系统部客户交流
  - 讨论要点：确认下一步

## Todays Completed Items

- [ ] 待回填
""".strip()

        self.assertEqual(
            unfinished_candidates(text),
            [
                "完成 IFD-海外初步研究的最小可讨论版本",
                "候选课题收敛",
                "候选课题整理",
                "客户后续跟进",
                "系统部客户交流",
            ],
        )

    def test_build_output_uses_new_daily_sections(self) -> None:
        content = build_output(
            today=__import__("datetime").date(2026, 6, 10),
            yesterday_source="workspace-azai/memory",
            biggest_progress="梳理了 A1 的研究框架",
            unfinished=["候选课题整理", "用户需求洞察作业初稿"],
            decided_for_today=["会后沉淀 20 分钟"],
            tomorrow_first_move="先把会议输入并入 A1",
            carry=["- 候选课题整理：今日重新决策（继续 / 延后 / 授权 / 删除）"],
            weekly_goals=["A1 完成 IFD-海外初步研究的最小可讨论版本"],
            weekly_warning="",
            inbox_items=["企业数据安全问题如何处理"],
            schedule_source="feishu calendar via azai",
            calendar_source="feishu calendar via azai",
            a_items=["完成 IFD-海外初步研究的最小可讨论版本", "候选课题整理"],
            b_items=["会后沉淀 20 分钟"],
            c_items=["客户后续跟进"],
            d_items=["系统部客户交流（线上）"],
            schedule=[
                "- 09:30-11:00 系统部客户交流（线上）",
                "- 11:20-12:00 A1 启动块 -> 把会议输入并入 A1",
                "- 14:00-16:00 A1 深入块 -> 完成 IFD-海外初步研究的最小可讨论版本",
                "- 16:00-17:00 B1 候选课题整理 -> 只做归类、收敛、优先级判断",
                "- 17:00-17:30 收工整理 -> 回填完成事项，准备 Daily Review",
            ],
        )

        self.assertIn("## 硬约束", content)
        self.assertIn("## 今日时间安排", content)
        self.assertIn("## 今天不排入主线", content)
        self.assertIn("## 这样排的逻辑", content)
        self.assertIn("## 事项归位", content)
        self.assertIn("### A：重要事项", content)
        self.assertIn("### B：紧要事项", content)
        self.assertNotIn("\n## A：重要事项\n", content)
        self.assertNotIn("\n## 今日日程\n", content)

    def test_build_output_filters_action_like_d_items(self) -> None:
        content = build_output(
            today=__import__("datetime").date(2026, 6, 10),
            yesterday_source="workspace-azai/memory",
            biggest_progress="梳理了 A1 的研究框架",
            unfinished=["整理用户需求洞察的作业初稿", "将上午 Charter 讨论结论沉淀为后续判断框架"],
            decided_for_today=[],
            tomorrow_first_move="整理用户需求洞察的作业初稿",
            carry=[],
            weekly_goals=["A1 完成 IFD-海外初步研究的最小可讨论版本"],
            weekly_warning="",
            inbox_items=[],
            schedule_source="synthetic fallback schedule",
            calendar_source="calendar query disabled by env",
            a_items=["整理用户需求洞察的作业初稿"],
            b_items=[],
            c_items=[],
            d_items=["将上午 Charter 讨论结论沉淀为后续判断框架", "Charter 6月版本PIC通过IPMT评审"],
            schedule=[
                "- 09:00-10:30 深度推进 -> 整理用户需求洞察的作业初稿",
                "- 16:00-17:00 协调 / 评审 / 对齐 -> Charter 6月版本PIC通过IPMT评审",
            ],
        )

        self.assertNotIn("D1: 将上午 Charter 讨论结论沉淀为后续判断框架", content)
        self.assertIn("D1: Charter 6月版本PIC通过IPMT评审", content)

    def test_focus_reminder_parses_new_structure(self) -> None:
        text = """
# 2026-06-10 LMI 日计划草案

## 事项归位

### A：重要事项
- A1: 完成 IFD-海外初步研究的最小可讨论版本
- A2: 候选课题收敛

### B：紧要事项
- B1: 会后沉淀 20 分钟

## 今日时间安排

### 上午主块
- 11:20-12:00 A1 启动块 -> 把会议输入并入 A1

### 下午第一主块
- 14:00-16:00 A1 深入块 -> 完成 IFD-海外初步研究的最小可讨论版本
""".strip()

        priority_items = parse_priority_items(text)
        self.assertEqual(priority_items["A1"]["task"], "完成 IFD-海外初步研究的最小可讨论版本")
        self.assertEqual(priority_items["B1"]["task"], "会后沉淀 20 分钟")

        schedule_entries = parse_schedule_entries(text)
        self.assertEqual(len(schedule_entries), 2)
        self.assertEqual(schedule_entries[0]["task"], "把会议输入并入 A1")

    def test_weekly_review_can_read_new_primary_result_heading(self) -> None:
        text = """
# 2026-06-10 LMI 日计划草案

## 今日主结果

- A1: 完成 IFD-海外初步研究的最小可讨论版本
""".strip()

        self.assertEqual(
            extract_primary_result(text),
            "完成 IFD-海外初步研究的最小可讨论版本",
        )


if __name__ == "__main__":
    unittest.main()
