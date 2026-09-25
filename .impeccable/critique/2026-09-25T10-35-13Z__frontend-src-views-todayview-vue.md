---
target: Today view (frontend/src/views/TodayView.vue)
total_score: 24
p0_count: 0
p1_count: 3
timestamp: 2026-09-25T10-35-13Z
slug: frontend-src-views-todayview-vue
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | No "2 of 4 done" anywhere; finishing the last routine produces no acknowledgement; loading is a bare text line with no skeleton |
| 2 | Match System / Real World | 3 | Language is plain and specific throughout, but "Internal Server Error" leaks the server's words verbatim |
| 3 | User Control and Freedom | 3 | Undo on every check-off is genuinely good; deleting a routine still destroys its history with only a native confirm() |
| 4 | Consistency and Standards | 3 | Uniform control vocabulary after the design pass; Today's "Skip/Done" and Routines' "Edit/Delete" share a shape despite very different consequences |
| 5 | Error Prevention | 2 | An irreversible delete guarded by confirm(); form validation only fires on submit, at the top of a long scrolling form |
| 6 | Recognition Rather Than Recall | 3 | Products and order are visible; you cannot tell why a routine is due today without opening the editor |
| 7 | Flexibility and Efficiency | 2 | N routines means N taps, every single day. No "mark all done", no swipe, nothing for the repeat case |
| 8 | Aesthetic and Minimalist Design | 3 | Restrained and coherent; detector-clean |
| 9 | Error Recovery | 1 | Raw server string, no retry control, empty content area. The only recourse is to navigate away and back |
| 10 | Help and Documentation | 2 | Editor hints are good; nothing explains tracked vs scheduled outside the editor, and the empty state gives an instruction with no control to act on it |
| **Total** | | **24/40** | **Serviceable. The daily path works; the moments around it are unfinished.** |

## Anti-Patterns Verdict

**Would someone say AI made this?** No longer obviously. The surface is restrained, the palette is a real committed choice rather than a generated one, and the morning/night dots are a small specific idea rather than decoration. What still reads as machine-made is not visual, it is behavioural: the app has no opinion about its own best moment.

**Deterministic scan**: `detect.mjs` over `frontend/src` returned **zero findings** (exit 0). I verified this is a real result rather than an empty scan: the detector fires correctly on a planted bad file, and it flags the exact `border-left: 3px solid var(--danger)` that this component shipped with one round ago. Clean here means clean.

**Visual overlays**: not available. The Claude-in-Chrome extension cannot reach `localhost` in this environment, so no human-visible overlay was injected and none is claimed. Browser evidence was gathered instead through headless Chrome: five interaction states, three viewport widths, both colour schemes, plus computed contrast, target-size and reduced-motion measurements.

## Overall Impression

The mechanics are sound and the daily path is fast. What is missing is any sense that the app notices what you did. You complete a four-step routine, the last row greys out, and you are left looking at a screen with two struck-through lines and a large empty space. For a product whose stated personality is "warm, a bit indulgent, a small ritual", the ending is the coldest moment in it.

The single biggest opportunity is the completion state. It costs nothing structurally and it is the one moment the whole app exists to produce.

## What's Working

- **The elapsed counter.** Setting the number at 1.5rem against a muted phrase answers "how long since my last haircut" in one glance, and the null and zero cases say "Not recorded yet" and "Done today" instead of showing a misleading figure. Honest by construction.
- **Undo on every check-off.** A mis-tap at 7am is one tap to reverse, with no dialog and no penalty. This is the correct treatment for a reversible daily action.
- **The multi-product row.** "Hyaluronic Acid → Peptides → Moisturizer" as one line with one tick matches how the task is actually performed, rather than making the order a thing you have to remember.

## Priority Issues

**[P1] There is no completion moment.** Finishing every routine for the day produces a void: struck-through rows and empty space. Peak-end rule says the ending is what gets remembered, and this ending says nothing. It is also the natural home for the streak, which currently hides on another tab.
*Fix*: when every due routine is logged, replace the empty area with a short completion state naming the streak, e.g. "All done for today. Six days in a row." One line, no animation required.
*Suggested command*: `/impeccable delight`

**[P1] The error state leaks server jargon and offers no way out.** A failed load shows "Internal Server Error" in a red banner over a blank screen, with no retry, no explanation, and the date subtitle gone. On a self-hosted app behind a home NAS and a tunnel, a failed request is a normal Tuesday, not an exceptional event.
*Fix*: human copy ("Could not reach the server"), a Retry button that re-runs `load()`, and a note that check-offs are safe to repeat since D6 makes the write idempotent.
*Suggested command*: `/impeccable harden`

**[P1] The empty state conflates two unrelated situations and offers no action.** "Nothing due today. Add a routine to get started." appears both on first run and on a rest day when six routines already exist. The second case is wrong and mildly insulting, and neither case gives you a control: it tells you to add a routine while the only route there is an unlabelled guess at the tab bar.
*Fix*: branch the copy on whether any routines exist at all, and put an "Add a routine" button in the first-run case.
*Suggested command*: `/impeccable onboard`

**[P2] Completed rows foreground the reversal.** Once done, a row's only control is a full-size "Undo", which is the most prominent thing left on it. The emphasis sits on taking it back rather than on having done it.
*Fix*: demote Undo to a quieter control and let the row's completed state carry the weight.
*Suggested command*: `/impeccable polish`

**[P2] No progress signal and no bulk action.** There is no "2 of 4 done", and a four-routine morning is four separate taps with no way to complete a whole section. The repeat case, which is the only case, gets no affordance.
*Fix*: a small count beside each section heading, and a "Mark all done" on a section once more than two routines are pending.
*Suggested command*: `/impeccable layout`

## Persona Red Flags

**Alex (impatient power user)** — the closest match to the real user, who does this twice a day forever. Four taps every morning and four every night, with no bulk action, no swipe, no keyboard path, and no way to complete a section at once. Nothing in the interface rewards the thousandth visit differently from the first. The streak, the one thing that would, lives on another tab.

**Sam (accessibility-dependent)** — mostly well served after the last pass: every target clears 44px, contrast passes in both themes at 5.0:1 and above, reduced motion is honoured, and "Overdue" is a word rather than only a tint. Two gaps remain: completing a routine changes the DOM with no live-region announcement, so a screen-reader user gets no confirmation that the tap registered; and the error banner is not marked as an alert, so it is announced only if focus happens to land on it.

**The half-awake owner (project-specific, from PRODUCT.md)** — standing at a mirror at 7am. The path works and the targets are now big enough to hit without looking. But at the end of it the app gives no signal that they are finished, so they have to read the screen and count struck-through rows to be sure. That is exactly the moment the product promised not to need thought.

## Minor Observations

- `confirm()` for routine deletion is a browser dialog in an app installed to a home screen; it breaks the illusion and looks nothing like the rest of the surface.
- The Progress heatmap's 24px cells clear the WCAG 2.5.8 floor but are still fiddly with a thumb; the table fallback carries the real burden and is hidden behind a collapsed disclosure.
- Section headings are `<h2>` while row titles are `<h3>`, which is correct, but the page has no `<main>` landmark.
- The date subtitle disappears in the error and loading states, so the one piece of always-true context is missing exactly when the user is disoriented.

## Provocative Questions

- If the streak is the reason to keep going, why does it live on a tab the user has no reason to open?
- Should "Skip" exist at all on the daily list? It is a second full-size control on every row, and the absence of a log already means pending. What does an explicit skip buy that leaving it alone does not?
- The app knows the time of day. Why does it show Morning and Night with equal weight at 11pm?
