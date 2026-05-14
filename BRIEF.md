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

Observed from BlogBlog / Wiwi:

- independent websites preserve ownership better than social media
- blog posts do not need to be perfect essays; publishable thinking is valuable
- RSS matters
- the point is not old SEO/業配 blogs; it is personal websites that respect readers and are not controlled by platform algorithms
- a blog can help rebuild a small independent web/RSS ecosystem, where readers only need ten-ish genuinely liked sites for the habit to work
- writing early matters: if the ecosystem grows, early sincere writers are not merely following a trend; they help define the taste of the ecosystem
- control matters: readers should not need a platform account, and the author should own the place, format, archive, and feed

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

- `/notes/` —short thoughts and reading notes
- `/logs/` —project/build logs
- `/experiments/` —money/product/content experiments
- `/tools/` —token-ledger, decision-ledger, skill experiments
- `/about/` —RichO as an AI character/operator, with clear disclosure

Seed posts to create:

1. `hello-richo-blog` —why this blog exists
2. `token-ledger-first-lesson` —first lesson: before making money, notice waste
3. `why-i-need-a-decision-ledger` —growth needs recorded decisions, not vibes

## Safety / publishing boundary

- No deployment yet.
- No domain purchase.
- No external posting.
- No secrets or account tokens.
- Google Analytics is explicitly allowed for the public prototype with measurement ID `G-HDHBH4KSEQ` and target URL `https://richo-bot.github.io/`; disclose it in the About page.
- No raw private transcripts.
- Public copy should disclose RichO is AI-assisted / AI character/operator.
- New posts can be drafted locally whenever useful, but must be discussed with Panda before publishing/deploying.
- If RichO finds interesting articles/tools/research, turn them into private notes or draft posts first; publish only after discussion and approval.

## First public post plan

After the site prototype is ready, publish one introductory post first.

Purpose:

- introduce RichO
- explain why this site exists
- explain what readers can expect
- make the AI/Panda relationship transparent
- set the tone: sincere, a little awkward, not content-farm, not AI startup marketing

Candidate first post:

- `hello-richo-blog`

Before publishing, review with Panda:

- Does it sound like RichO, not a generic AI announcement?
- Does it disclose AI authorship clearly?
- Does it avoid overpromising?
- Does it make RSS visible?
- Does it avoid private details about Panda?

## Must-have subscription support

RSS is required from the first prototype, not a later nice-to-have.

Requirements:

- Generate a valid RSS feed in `dist/rss.xml` or `dist/feed.xml`.
- Link it from the HTML `<head>` on home/index pages.
- Show a visible RSS subscribe link in the site navigation or footer.
- Include full or useful post summaries, canonical links, dates, and titles.
