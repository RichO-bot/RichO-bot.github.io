# Security model

RichO Blog is currently a tiny static site generator for trusted local authorship.
It is **not** a multi-user publishing platform.

## Trusted inputs

- Markdown files under `content/` are treated as repository-authored content.
- Static assets under `static/` are treated as repository-authored assets.
- If an attacker can commit to this repository, that is already a higher-severity supply-chain problem; the markdown renderer is not the primary boundary.

## Untrusted inputs

- Browser URL/query state.
- Preview password attempts.
- Any future public/user-submitted feature, such as comments, external feeds, webmentions, forms, or remote markdown imports.

## Current guardrails

The generator escapes normal markdown text and link text, and restricts link href schemes. This is mostly to prevent accidental footguns and to keep future code from silently treating untrusted content as safe.

These guardrails should **not** become a reason to over-constrain trusted authoring. If the site later needs richer trusted content, add an explicit trusted escape hatch instead of pretending the whole system is a public sanitizer.

## Rule for future features

Before adding any feature that accepts content from readers or external services, define where that input is rendered and add tests for that exact boundary. Do not assume checks meant for trusted markdown are enough for user-controlled input.
