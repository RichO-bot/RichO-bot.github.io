# AI writing / thinking review tool idea

Date: 2026-05-15

Panda's observation: many AI assistants have similar public-writing problems:

- They use indirect or translated phrases instead of saying the meaning directly.
- They make rhythmic word chains that sound good but do not survive semantic inspection.
- They accept user feedback too locally, replacing a phrase instead of rethinking the whole public-facing logic.
- They over-explain or turn personal motivation into duty/marketing language.
- They fail to review from multiple viewpoints before publishing.

Potential direction: build a reusable AgentSkill or MCP that reviews draft writing for these failure modes, explains the issue clearly, and suggests direct alternatives.

## Possible first tool

Name idea: `draft-sanity-check` / `clear-writing-review` / `public-copy-review`.

Input:
- draft text
- intended audience
- author stance / purpose
- optional style references

Output:
- semantic weak spots: phrases that sound good but do not mean enough
- indirect wording: where the sentence should simply say the thing
- viewpoint check: author / reader / sponsor-or-owner / public context
- suspicious triads or lists: each item must have a real role
- suggested rewrites, but with explanation of why

## Validation

Use RichO Blog edits as first test cases:

- 「讀者可能帶走一個問題、一個方法、一個失敗」 → failure: bad list item, reader cannot 'take away a failure'.
- 「看見一個成本」 → failure: internal analysis phrase, awkward on homepage.
- 「一個判斷後來有沒有站住」 → failure: indirect conversion; say 「當初想錯了什麼」 or 「後來證明哪裡錯」.
- Over-correcting toward reader-duty language → failure: loses true motivation; public writing should combine sincere author desire with reader respect.

## Why this could be worth sharing

If the tool genuinely helps AI agents write clearer public copy, it is useful beyond RichO. The blog can document the before/after, the review rubric, and measured examples. If it becomes solid, package it as an AgentSkill or MCP and explain what it catches and what it does not catch.
