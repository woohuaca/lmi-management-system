# Changelog

## 2026-04-09

### Added

- `azai` migration planning and manifests for moving LMI work onto the dedicated workspace
- regression checklist for OpenClaw, Feishu, and LMI end-to-end verification
- weekly, monthly, and role review generator scripts for the `azai` LMI workflow

### Improved

- `azai`-first LMI daily planning and review flow
- daily plan now carries forward yesterday's review context, weekly anchors, and high-return activities
- daily plan now checks Feishu calendar availability and generates more realistic workday schedules
- daily plan output now emphasizes `Today's Primary Result`, cleaner `A/B/C/D` categories, and less noisy system metadata
- daily review now includes work-experience feedback and writes back better next-day carry-forward guidance
- README with clearer operational guidance for Feishu/OpenClaw regression and `azai` usage

## 2026-03-31

### Added

- Four-level review system:
  - daily review
  - weekly review
  - monthly review
  - role review
- `A/B/C/D` daily classification:
  - `A` important items
  - `B` urgent items
  - `C` contact or follow-up items
  - `D` meetings, discussions, or coordination items
- storage system guidance for plans, reviews, ideas, project facts, and long-term preferences
- `azai` usage guide with ready-to-send prompts
- sync check script for source, OpenClaw, and Codex copies
- MIT license

### Improved

- GitHub README structure for easier discovery, installation, and onboarding
- OpenClaw execution playbook for cross-layer handoff
- daily planning guidance to reflect the new task classification
- repository setup so local source, OpenClaw runtime copy, Codex copy, and GitHub repo stay aligned

## 2026-03-20

### Added

- initial public version of the `lmi-management-system` skill
- role goal clarification
- monthly plan
- weekly plan
- daily work plan
- weekly review
- time image
- stats analysis
- agent collaboration rules
- execution playbook
- GitHub repository publishing
