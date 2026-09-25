# Product

## Register

product

## Users

One person: the owner of the NAS this runs on. Single-user by decision (D4 in
[specs.md](specs.md)), no accounts, no sharing, no social layer.

They open it twice a day, on a phone, installed to the home screen. Morning:
standing at a bathroom mirror, often in a hurry, frequently one-handed while the
other hand is holding something. Night: tired, low light, sometimes in bed
deciding whether they can be bothered. Neither moment survives a slow or fiddly
interface.

The job is small and repetitive: see what today asks of me, tick it off, and
occasionally answer "how long since I did that?" for things measured in weeks
rather than days (a haircut, a facial). Editing routines is rare by comparison
and happens sitting down.

## Product Purpose

Track a skincare routine that has enough moving parts to forget: different
products on different weekdays, layered in a specific order, split across
morning and night, plus appointments that recur every few weeks.

Success is finishing the daily interaction in a few seconds without thinking,
and trusting the streak and history enough to believe them. Failure is opening
it, squinting, and closing it again.

## Brand Personality

Warm, considered, unhurried. It should feel like a small ritual object rather
than a compliance tool: something with a bit of indulgence to it, because the
activity it tracks is itself a small pleasure.

It is still a tool. Personality shows in surface warmth, typographic care and
restraint, not in decoration that costs a tap or a second.

Voice: plain and specific. "23 days since the last one", not "It's been a while!"

## Anti-references

All three of these, explicitly:

- **Generic SaaS dashboard.** Card grids, stat tiles, gradient accents, an admin
  panel that happens to be about skincare. The Progress view is the one at risk.
- **Influencer beauty app.** Heavy pastels, script faces, glitter, aspirational
  photography, anything that looks like it wants to sell a product. The rose
  accent must stay a considered colour, not a candy one.
- **Bare developer tool.** System defaults, cramped rows, obviously self-hosted
  and unloved. Being a personal project is not an excuse for looking like one.

## Design Principles

1. **Two taps, half awake.** The daily path (open, see today, tick it off) is the
   only thing that gets optimised at the cost of everything else. Configuration
   can be slower; it happens rarely and sitting down.
2. **Thumb-reachable, one-handed.** Primary actions live in the lower two-thirds
   of a phone screen and are large enough to hit without looking. Nothing
   important sits in the top corners.
3. **Warmth through surface and type, not decoration.** Personality comes from
   the palette, spacing and typographic hierarchy already in the codebase. Any
   ornament that costs a tap, a second, or a line of legibility is cut.
4. **Say the specific thing.** Counters, dates and statuses are stated plainly
   and exactly. No cheerleading, no vagueness, no exclamation marks.
5. **Honest empty and unknown states.** When there is no data, say so rather
   than showing a zero that looks like a measurement. A tracker with no baseline
   reads "not recorded yet", never "0 days".

## Accessibility & Inclusion

- **WCAG 2.1 AA.** Body text ≥4.5:1, large text ≥3:1, in both light and dark.
  The dark theme is not an afterthought: half the usage is at night.
- **Touch targets ≥44×44px**, the iOS minimum. The current `.btn` and `.chip`
  are roughly 32px and 30px, which is below it and the most concrete
  accessibility defect in the app today.
- Respect `prefers-reduced-motion` for any animation added.
- Respect `prefers-color-scheme`; the app already ships both themes.
- Never encode meaning in colour alone. "Overdue" carries a word, not just a
  tint, for colour-blind users and for glances in bright light.
