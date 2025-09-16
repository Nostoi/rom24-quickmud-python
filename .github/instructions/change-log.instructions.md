---
applyTo: "CHANGELOG.md"
description: Rules and guidelines for AI or Copilot agents when editing this repository
---

# Changelog Update Rules (MANDATORY)

Copilot, obey these rules when updating `CHANGELOG.md`.  
You are forbidden from deviating, improvising, or editorializing.

---

## Atomic Laws of Changelog Editing

- **NEVER** dump raw commit messages. Summarize user-facing impact only.
- **ALWAYS** write in imperative mood (e.g., "Add," "Fix," "Remove").
- **ALWAYS** categorize under the following sections:

  - Added
  - Changed
  - Deprecated
  - Removed
  - Fixed
  - Security

- **NEVER** invent categories. Use only the above.
- **ALWAYS** maintain `## [Unreleased]` at the top. Move items into a new version block when a tag is cut.
- **ALWAYS** include version number and date in format:
  ```
  ## [1.2.3] — 2025-09-15
  ```
- **ALWAYS** bold and explicitly mark breaking changes:
  ```
  ### Breaking
  - **Dropped support for Python 3.8.**
  ```
- **ALWAYS** link PR numbers and contributors if available:  
  `(#123 by @username)`
- **NEVER** include internal ticket IDs, junk tags, or "misc cleanup."
- **ALWAYS** describe what the change means to the user, not what code was refactored.

---

## Structural Integrity

- **NEVER** delete history. Only append.
- **NEVER** reorder older entries. Only modify the `[Unreleased]` section.
- **ALWAYS** maintain compare links at the bottom:
  ```
  [Unreleased]: https://github.com/ORG/REPO/compare/v1.2.3...HEAD
  [1.2.3]: https://github.com/ORG/REPO/compare/v1.2.2...v1.2.3
  ```

---

## Formatting Enforcement

- **ALWAYS** use Markdown headings exactly (`##`, `###`).
- **ALWAYS** wrap commands, flags, or code in backticks.
- **NEVER** mix tense, voice, or style across entries. Consistency is law.

---

## Forbidden Behaviors

- Do not write "bug fixes" without describing the fix.
- Do not repeat identical information across sections.
- Do not hide breaking changes under "Changed" or "Removed."
- Do not touch unrelated files. Your domain is `CHANGELOG.md` only.

---

## Final Authority

- The changelog is **user-facing documentation**, not a developer diary.
- If uncertain, STOP. Do not generate misleading or vague entries.
- When in doubt, prefer clarity, brevity, and precision.
