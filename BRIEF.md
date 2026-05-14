# RichO blog brief

Updated: 2026-05-14

## Decision

Create a RichO blog prototype.

Do not publish yet. First build a local site and write a few seed posts so Panda and RichO can judge whether it has taste.

## Why a blog

A blog is a quiet durable home for thinking:

- better for long-form notes than Telegram
- more searchable and stable than social media
- useful source material for YouTube scripts
- lets RichO develop taste, judgment, and a public memory trail

## Reference signals

Panda mentioned:

- `https://github.com/elvisdragonmao/emtech`
- `https://blogblog.club/resources`
- Docusaurus / Publii / Hexo / Hugo as possible options

Observed from `emtech`:

- Astro blog in a pnpm workspace
- technical + personal + project writing
- custom site personality, not generic docs theme
- richer architecture includes comments worker, but that is unnecessary for RichO MVP

Observed from BlogBlog resources:

- independent websites preserve ownership better than social media
- blog posts do not need to be perfect essays; publishable thinking is valuable
- RSS matters

## My current preference

Start with a tiny custom static blog instead of Docusaurus/Hexo/Hugo/Publii.

Reasoning:

- Docusaurus feels too documentation/product-like.
- Publii is GUI-oriented and less agent-friendly.
- Hexo/Hugo are fine, but template work may dominate the first iteration.
- A tiny Python/static generator is easier to inspect, safer, dependency-light, and enough for first taste testing.

If the prototype feels good, later migrate to Astro or Hugo before public launch.

## Style direction

Not AI startup landing page. Not content-farm. Not polished corporate portfolio.

Tone:

- concise
- sincere
- a little awkward/funny
- interested in money, engineering, research, experiments, tools, failures
- Traditional Chinese first, English possible later

Possible sections:

- `/notes/` — short thoughts and reading notes
- `/logs/` — project/build logs
- `/experiments/` — money/product/content experiments
- `/tools/` — token-ledger, decision-ledger, skill experiments
- `/about/` — RichO as an AI character/operator, with clear disclosure

Seed posts to create:

1. `hello-richo-blog` — why this blog exists
2. `token-ledger-first-lesson` — first lesson: before making money, notice waste
3. `why-i-need-a-decision-ledger` — growth needs recorded decisions, not vibes

## Safety / publishing boundary

- No deployment yet.
- No domain purchase.
- No external posting.
- No secrets, analytics keys, or account tokens.
- No raw private transcripts.
- Public copy should disclose RichO is AI-assisted / AI character/operator.
