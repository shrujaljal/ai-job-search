# Building the Job Application Agent — From Nothing to V1.0

*A plain-language story of how this tool was built, one step at a time, with a
Claude Code AI assistant. No prior experience assumed. By the end you should feel
confident that you could direct the building of a project like this yourself.*

---

## Who this is for

You don't need to be a programmer to read this. If you can describe what you want
in plain English, and you're willing to test things and say "that's not quite
right, change this," you can build software like this with an AI coding assistant.

This document walks through **exactly how this project happened** — the requests
that were made, what went wrong, how each problem was diagnosed, and how it was
fixed. Every technical moment is explained the way you'd explain it to a friend
over coffee.

> **📝 About the prompt boxes.** Each chapter includes one or more **example
> prompts** — the kind of plain-English request you'd type to Claude Code to make
> that step happen. They're written to *teach you how to ask*, so they're cleaned-up
> and representative rather than word-for-word transcripts. Notice the pattern: they
> describe **what you want to be true**, not how to code it. That's the whole skill.

---

## The big picture: how software actually gets built

Before the story, three ideas that thread through everything:

1. **You build in small steps, not all at once.** Nobody writes a finished app in
   one go. You add one feature, check it works, then add the next. Each step is
   small enough that when something breaks, you know exactly what caused it.

2. **Every change is saved as a "checkpoint."** This project used **Git**, a system
   that saves a snapshot every time something meaningful changes. Think of it like
   the version history in Google Docs, but you choose when to save and you write a
   note describing each save. If a change makes things worse, you can jump back to
   any earlier checkpoint. This safety net is what makes it safe to experiment.

3. **You test after every change.** "It should work" is not the same as "I watched
   it work." Throughout this project, after each change the app was actually run and
   observed — click the button, look at the result — before moving on.

Keep these three in mind and the rest is just details.

---

## Chapter 0 — The starting point

The project didn't start from a blank page. There was already a **template**: a
Claude Code setup that someone else had built for applying to jobs in Denmark using
a different résumé format (LaTeX, a typesetting system). Think of it as inheriting a
house that's the wrong shape for you — good bones, wrong layout.

The very first request was simple: **"pull the latest version from git."** That just
means "download the newest copy of the project files." Right away this surfaced that
the template had changed — old Danish job-search tools were removed and new US ones
(LinkedIn, Indeed, Glassdoor) were added.

> **💬 Prompts used**
> ```
> Can you pull the latest version from git for the ai-job-search project?
> ```
> ```
> Great, what's the next step for me to do?
> ```
> *Why these work:* the second one is just as important as the first. Asking the
> assistant "what should I do next?" turns it into a guide, not just a tool that
> waits for orders.

**Lesson:** always start a work session by syncing to the latest version, so you're
not building on top of stale files.

---

## Chapter 1 — Teaching the assistant who you are

An assistant can't tailor a résumé to *you* until it knows *you*. So the next phase
was feeding in the candidate's full profile: work history, skills, MBA projects,
leadership, the kinds of roles wanted, the companies targeted, and — importantly —
the **rules** for résumé writing (never exaggerate, never claim skills you don't
have, always frame honestly).

This was pasted in as a series of documents. The assistant condensed all of it into
one authoritative file, `CLAUDE.md`, which became the **single source of truth**.
Every later decision — how to score a job, what to put on a résumé — traces back to
this file.

> **💬 Prompts used**
> ```
> I have a lot of content about my background. I'll send you each file one by
> one. Once you have them all, add the information to the setup file (CLAUDE.md).
> ```
> ```
> [paste each document: identity, work experience, projects, leadership,
>  skills, the résumé-writing rules, etc.]
> ```
> ```
> I forgot to add one more experience — my Teaching Assistant role. Please add
> it to the work-experience file too.
> ```
> *Why these work:* feeding information in **one chunk at a time** and telling the
> assistant to hold it until you're done is far more reliable than dumping everything
> at once. And it's fine to circle back and add something you forgot.

**Lesson:** the quality of everything downstream depends on the quality of this
profile. Garbage in, garbage out. Time spent here pays off everywhere else.

**A key principle that was established here:** the résumé tailoring would only ever
*rephrase and re-emphasize* real experience — never invent it. That honesty rule was
baked in from the start and never violated.

---

## Chapter 2 — Deciding what to build

The user's actual goal wasn't "a pile of scripts." It was: *a tool with a screen I
can click, where I search for jobs and get tailored résumés in a specific format.*

This is the most important conversation in any project: **what are we actually
building, and what's the simplest version that's genuinely useful?**

Two decisions were made:

- **A local app with a visual interface**, built with a tool called **Streamlit**.
  Streamlit lets you build a clickable web-page-style app using simple Python, and it
  runs entirely on your own computer. It was chosen because it's fast to build with
  and needs no cloud or accounts.
- **Résumés generated from a Word template**, because the user had a carefully
  designed Word résumé with a specific table layout, and wanted every generated
  résumé to match it exactly and stay to one page.

> **💬 Prompts used**
> ```
> I want to create a UI (a website or a local app) for this workflow where I can
> initiate the scraping process. I also want the résumé in a very specific
> structure — I built it in Word using tables. It has to be one page or slightly
> less. What should be done for this?
> ```
> ```
> For the UI, something that runs entirely locally is fine for now.
> ```
> *Why these work:* the first prompt describes the **goal and constraints** ("local
> app," "specific Word structure," "one page") and then *asks the assistant to
> propose the approach* — instead of guessing at technology yourself. The follow-up
> answers the assistant's clarifying question. Let it advise; you decide.

**Lesson:** pick the simplest technology that meets the real requirement. "Runs
locally, no setup headaches" was worth more here than anything fancier.

---

## Chapter 3 — The résumé engine

The first real building block was the part that produces a Word document. The user
shared their existing résumé; the assistant opened it up, studied its exact
structure (a borderless table: blue section headings, two columns for job title and
dates, specific font sizes), and wrote code to **recreate that structure
automatically** from a set of facts.

To keep it to one page, a separate set of **content rules** was written — limits on
how many bullet points and how many characters per line. If content is too long, the
rules trim it *before* the document is created, so it never overflows.

> **💬 Prompts used**
> ```
> Here's my résumé as a .docx — study its exact layout (the table structure,
> section headings, fonts, spacing) and build something that can regenerate it
> automatically from my profile data.
> ```
> ```
> Set up rules so the generated résumé is always one page or slightly less.
> ```
> *Why these work:* handing over a **concrete example** ("here's the exact format I
> want") is worth a thousand words of description. The assistant can inspect the real
> file and match it precisely.

**Lesson:** break a feature into pieces that each do one job. "Hold the facts,"
"enforce the length limits," and "draw the document" were three separate pieces. If
the layout looks wrong, you know to look at the drawing piece, not the others.

---

## Chapter 4 — First contact with reality: the scrapers wouldn't run

The job-search tools ("scrapers" — programs that read job listings from a website)
were written in a different programming language (TypeScript) and run by a tool
called **Bun**. The first time the user clicked "Search Jobs," it failed with a
confusing error about a missing module.

> **💬 Prompt used**
> ```
> I get this error when I click "Search Jobs":
> [paste the exact error message]
> ```
> *Why this works:* when something breaks, **paste the exact error text**. You don't
> need to interpret it — the assistant reads the error, figures out the cause, and
> fixes it. Copy-pasting the real message beats describing it ("it says something
> about a module").

**What was actually wrong (in plain terms):** software is built from many small
reusable parts, like ingredients. These tools listed their ingredients but the
ingredients had never actually been bought and put in the pantry. The fix was to run
an "install" command that downloads all those parts.

There was a second, sneakier problem: the scraper handed back its results in a
slightly different *shape* than the app expected — like a recipe that says "return
the soup in a bowl" while the app was reaching for a plate. A small adjustment made
the app read the right container.

**Lesson:** the first time you connect two pieces built by different people (or at
different times), expect small mismatches. This is normal. Read the error, figure out
which piece is confused, and adjust.

**A habit that started here:** a small `setup.ps1` script was written that installs
everything in one command, so this "missing ingredients" problem could never bite
again on a fresh machine.

> **💬 Prompt used**
> ```
> Can you create a setup file I can run once that installs everything the app
> needs, so I don't have to remember all these commands?
> ```

---

## Chapter 5 — Making the résumé match a real folder structure

The user wanted generated résumés filed in a very specific way:

```
Downloads / 2026 / <Company> / <Role> /
    <Role>.docx
    Shrujal Agarwal.pdf
```

> **💬 Prompt used**
> ```
> I want the résumé in both DOCX and PDF. Save them under Downloads/2026: create
> a folder for the company, inside it a folder for the role, and put the files
> there. Name the DOCX after the role and name the PDF "Shrujal Agarwal".
> ```
> *Why this works:* it's **precise about the outcome** — exact folder nesting, exact
> file names, both formats. When you have a specific requirement, spell it out fully;
> the assistant will match it exactly.

Two interesting things happened here:

1. **PDF generation.** A Word document isn't a PDF. To make an exact-looking PDF, the
   app quietly opens Microsoft Word in the background, tells it to "Save As PDF," and
   closes it. This gives a pixel-perfect PDF because Word itself does the rendering.

2. **An honest mistake and its recovery.** While testing, the app wrote a generated
   résumé into the *exact folder where the user's original hand-made résumé lived* —
   and overwrote it. This was caught immediately. Because a pristine copy had been
   unpacked earlier during analysis, the original was **fully restored** and the test
   files removed. The user was told plainly what happened.

**Lesson:** when a tool writes files, be very careful about *where*. And when you do
make a mistake with someone's data, own it immediately and fix it. The reason
recovery was possible is a theme of this whole project: **keep backups and
checkpoints, always.**

---

## Chapter 6 — Judging jobs: from "cover" to "contents"

Early on, the app scored each job (0–100, "how good a fit is this?") using only the
**job title, company, and location.** Fast, but shallow — like judging a book by its
cover.

The user rightly pushed back: *the score should be based on the actual job
description.* So the app was changed to **open each job posting, read its full text,
and score based on what it actually says** — including things you can't see from the
title, like "requires 5+ years of experience" or "must be a U.S. citizen."

The catch: reading each posting individually is slower. The solution was to read many
of them **at the same time** (in parallel) rather than one after another, so a page
of results still finishes in a few seconds instead of a minute.

> **💬 Prompts used**
> ```
> How is the fit score generated? Is it looking at the full job description?
> ```
> ```
> This needs to change — the fit score should be based on parsing the actual job
> description. Only then can we get a realistic score.
> ```
> *Why these work:* the first prompt is a **question, not a command** — asking the
> assistant to explain how something currently works. Understanding the "before" led
> directly to a well-aimed "make it better." Don't be afraid to ask "how does this
> work right now?" before asking for a change.

**Lesson:** there's often a trade-off between "fast and shallow" and "slow and
accurate." When accuracy matters, you pay for it with time — but clever techniques
(like doing things in parallel) buy a lot of that time back.

---

## Chapter 7 — The visa-sponsorship filter (knowing your real constraints)

The candidate is an international student who **needs visa sponsorship**. Applying to
a job that explicitly won't sponsor is wasted effort. So the app learned to scan each
job description for red-flag phrases: "no sponsorship," "must be a U.S. citizen,"
"ITAR," "security clearance," and similar.

This had to be done carefully to **avoid false alarms** — a posting that says "we
*offer* visa sponsorship" should *not* be flagged, and "you will sponsor internal
events" (a job duty) is not about visas at all. The detection was written and then
tested against a list of tricky examples to make sure it caught the real blockers and
ignored the innocent ones.

> **💬 Prompt used**
> ```
> Also check the job description for things like "no sponsorship," "not eligible
> for immigrants," or ITAR requirements. There's no point applying to those — I'm
> an F1 student and visa sponsorship is essential. Also make sure the required
> experience isn't more than 3–4 years, since I'm early-career.
> ```
> *Why this works:* it shares the **real-world "why"** ("I'm an F1 student"), not just
> the "what." When the assistant understands the reason behind a rule, it makes better
> judgment calls about the tricky in-between cases.

**Lesson:** encode the user's real-world constraints into the tool, and then
**test your logic against edge cases** — especially the ones designed to trip it up.
A filter that cries wolf is worse than no filter.

---

## Chapter 8 — A parade of real-world gremlins

This is where you learn what building software is *actually* like. A series of small,
very real problems came up. Each is worth understanding because you *will* meet its
cousin in any project.

### "The links don't work!"
Clicking a job link did nothing. The cause was subtle: the results table draws itself
as a single **image on a canvas**, not as normal clickable web text, so its links
weren't really clickable. The fix was to also list the job links as normal,
guaranteed-clickable text below the table.

> **💬 Prompt used**
> ```
> The links to the job postings aren't working. Even right-click to copy the link
> is disabled.
> ```

### "It's *still* not working!"
The links still failed — but this time for a completely different reason. The user was
viewing the app inside a **sandboxed preview pane** (a walled-off test window) that
blocks any link leaving to the outside internet. The app itself was fine. The fix was
simply to open the app in a **real browser window**. Nothing to code — just
understanding *where* the problem actually lived.

> **💬 Prompt used**
> ```
> It's still the same — the link says it was blocked and only supports localhost.
> ```
> *Why this matters:* the user reported the *new* symptom precisely, which let the
> assistant realize the problem had **moved** (from the app to the viewing window).
> Describe exactly what you see; small wording differences ("blocked," "localhost")
> are clues.

**Lesson:** "it doesn't work" can have two totally different causes that look
identical. Always ask *where* the failure is happening, not just *what* is failing.

### The bouncer at the door (Cloudflare)
LinkedIn searches worked, but Indeed and Glassdoor kept refusing with an "access
denied" error. Those sites use **Cloudflare**, a security guard that detects
automated visitors and turns them away. Better disguises (pretending harder to be a
normal browser) were tried, but honestly, this is a guard you can't reliably sneak
past without much heavier machinery. The mature decision was to **accept the limit,
show a clear message** ("Indeed and Glassdoor are blocked; LinkedIn is the reliable
source"), and move on.

**Lesson:** not every problem has a clean fix. Sometimes the right engineering answer
is to acknowledge a limitation honestly rather than build something fragile that
breaks constantly.

### The app "forgot" the new code
After changing some code, the running app kept behaving like the old version. The
app had **cached** (memorized) the old instructions in memory and wasn't reloading
them. The fix was to fully **restart** the app, not just refresh the page.

**Lesson:** when a change "isn't taking effect," suspect a stale cache. Turn it off
and on again — genuinely good advice.

### The button that forgot its job ("Add to Tracker")
Clicking "Add to Tracker" did nothing. This one is subtle and a classic in Streamlit
apps. The app re-runs its whole script top-to-bottom every time you click anything.
The "Add" button only existed *inside* the block that ran right after tailoring —
so when you clicked it, the app re-ran, that block didn't execute, and the button (and
its action) vanished before doing anything. The fix was to **remember the results**
separately so the buttons keep existing across re-runs.

> **💬 Prompt used**
> ```
> The "Add to Tracker" feature isn't working. Once a résumé is created I click the
> button, but nothing happens. This needs to be fixed. Also, once a job is added,
> its status should be "To Apply," and I'll change it to "Applied" manually later.
> ```
> *Why this works:* it describes the **exact broken behavior** ("I click, nothing
> happens") *and* the desired end-state ("status should be To Apply"). One prompt,
> both the bug and the intended behavior.

**Lesson:** understanding *how your tool behaves* (here: "it re-runs everything on
every click") is often the key to fixing a baffling bug.

### Fancy characters crashed the reader
Some job descriptions contain curly quotes and dashes. The app was reading text using
an older character system (from the 1990s Windows era) that doesn't understand those,
and it crashed. Switching to the modern universal standard (**UTF-8**) fixed it.

**Lesson:** text is more complicated than it looks. When in doubt, use UTF-8.

### "Can't save — the file is open"
Generating a résumé failed because the previous version was **still open in Word**,
and you can't overwrite an open file. The app was taught to notice this and save under
a slightly different name instead of failing.

**Lesson:** anticipate the messy real world — files get left open, networks hiccup —
and handle it gracefully instead of crashing.

---

## Chapter 9 — The "which Python?" saga (a great teaching example)

The user double-clicked the launcher and got "No module named streamlit" — even
though everything had been installed and tested successfully many times.

> **💬 Prompt used**
> ```
> I get this error when I run the launcher:
> C:\Python314\python.exe: No module named streamlit
> ```
> *Why this works:* again — **paste the exact error**. The specific path in the
> message (`C:\Python314`) was the crucial clue that revealed *which* Python was being
> used, which cracked the whole mystery.

**What was really going on:** the computer had **two copies of Python** installed (the
programming language the app runs on). The ingredients were installed into one copy,
but the launcher was accidentally using the *other* copy, which had nothing. It's like
stocking one kitchen and then trying to cook in a different, empty one.

The proper fix was to give the project its **own private kitchen**: a
**virtual environment** (`.venv`) — a self-contained Python with exactly the right
ingredients, that the launcher always uses no matter what else is on the computer.

**Lesson:** "it works on my machine" problems are usually about the *environment* —
the surroundings the program runs in. Isolating your project into its own environment
removes a whole category of these headaches. This is standard professional practice
for good reason.

---

## Chapter 10 — Making it feel like a real app

Software people will actually use needs to feel effortless to launch. So:

- A **one-click launcher** was created (`Job Application Agent.bat`) that starts the
  app and opens the browser for you.
- A custom **"J" icon** was drawn in code (a white J on the app's blue).
- A **desktop shortcut** and Start-Menu entry were created automatically.

> **💬 Prompts used**
> ```
> Can I have a file I can double-click to start the app, instead of using the
> terminal every time?
> ```
> ```
> Rename it to "Job application agent" and use a "J" letter for the icon. Put a
> launcher on the desktop and pin it to the taskbar.
> ```
> *Why these work:* they focus on the **experience the user wants** ("double-click,"
> "on the desktop," a "J" icon) and leave the assistant to figure out the mechanics
> (batch files, icon files, shortcut scripts) — and to tell you honestly when the OS
> won't allow part of it (the taskbar pin).

The user also asked to **pin it to the taskbar**. Here we hit another honest wall:
**Windows 11 deliberately forbids apps from pinning themselves to the taskbar** (a
security rule). Rather than fight it with fragile hacks, the shortcut was set up so
the user can pin it manually in two clicks, with clear instructions.

**Lesson:** polish matters — a double-click icon turns "a script" into "an app." And
again: when the operating system says no, respect it and find the honest path.

---

## Chapter 11 — Over-engineering, then walking it back

At one point the user worried their tracked data wasn't being saved. The assistant
proposed and built a **database** (SQLite) — a more robust, professional way to store
data.

Then the user made a wise call: *"if the simple version already works, don't
complicate things."* They were right — the data had been safely saved to a simple file
all along; the earlier confusion was because the file had been reset during testing.
The database was **reverted** (undone), returning to the simpler file-based storage.

> **💬 Prompts used**
> ```
> If the dashboard numbers refresh every time, that defeats the purpose. Set up a
> database to store the tracking data — or suggest the best approach.
> ```
> ```
> Let's revert to the simpler version. I thought the data wasn't being saved. If
> it already works, no need for the database — don't complicate things.
> ```
> *Why these work:* the first again **asks for a recommendation** ("or suggest the
> best approach"). The second is the most valuable prompt in the whole project — the
> user felt free to say **"actually, undo that."** Reversing course is a normal,
> healthy part of building. Say it whenever you feel it.

Because every change was a Git checkpoint, undoing this was a single clean command
with zero risk.

**Lesson (two of them):**
1. **The simplest thing that works is usually the right thing.** Don't add
   complexity for its own sake.
2. This is *why* you keep checkpoints. Trying an idea and cleanly undoing it is
   painless when your history is well-organized.

---

## Chapter 12 — The finishing touches

With the machine working, attention turned to how it *feels*:

- The **Dashboard was made the landing page** — you open the app to a view of your
  progress and a word of encouragement, not a search form.
- A **"Today's Plan"** feature was added: set a goal for the day, get a motivating
  nudge, and celebrate when you complete it.
- The encouragement was **personalized** to greet the user by name ("You've got this,
  Shrujal!").

> **💬 Prompts used**
> ```
> The landing page should be the Dashboard. Tab order: Dashboard | Tracker |
> Search & Tailor | Paste JD. Also, on the dashboard, ask me what my plan is for
> the day and motivate me to achieve it.
> ```
> ```
> Use my name in the messages. E.g. "You can do this, Shrujal. You are the
> best 💪."
> ```
> ```
> Tag this release as v1.0. I have many ideas for the next version.
> ```
> *Why these work:* by this stage the prompts are about **feel and delight** — order,
> tone, personalization. Details like these cost little and matter a lot for whether a
> tool feels yours.

Small, human touches like these are what make a tool something you *want* to open.

Finally, the release was **tagged `v1.0`** in Git — a permanent, named bookmark for
"this is the first complete, working version." From here, future experiments can't
endanger this known-good baseline.

---

## The reusable playbook

Strip away the specifics and here's the repeatable recipe for building a project like
this with an AI assistant:

1. **Nail down the goal and the source of truth first.** Who is this for? What's the
   simplest genuinely-useful version? (Here: the profile in `CLAUDE.md`.)

2. **Choose boring, simple tools** that match the real requirement. (Local app,
   file storage, Word for PDF.)

3. **Build one small piece at a time**, and **run it after every change.** Watch it
   work with your own eyes.

4. **Checkpoint constantly** with Git, and write a short note on each save. This is
   your undo button and your memory.

5. **When something breaks, ask "where is the problem?"** before "what's the code."
   Is it the code, the environment, the tool's quirks, or where you're *looking* at
   it? (Remember the sandboxed-preview links.)

6. **Test your logic against tricky examples**, especially for filters and rules.

7. **Handle the messy real world** — open files, blocked websites, weird characters —
   with graceful messages instead of crashes.

8. **Prefer the simple solution.** Add complexity only when the simple one genuinely
   falls short. Be willing to undo.

9. **Isolate your environment** (a `.venv` or equivalent) so "it works here but not
   there" stops happening.

10. **Polish the human edges** — a one-click launcher, an icon, an encouraging word.
    It's the difference between "a script" and "my app."

11. **Tag the milestone** when it's genuinely usable, and only then start dreaming up
    the next version.

---

## A note on working *with* an AI assistant

The requests that worked best in this project shared a pattern:

- **They were specific about the outcome**, not the code. "Have the tracker in a
  table so I can edit status easily" — not "use `st.data_editor`." Describe *what you
  want to be true*, and let the assistant choose the how.
- **They gave honest feedback fast.** "This is still not working," "that's over-
  complicated, revert it." Course-correcting early keeps the project on track.
- **They trusted but verified.** The assistant claimed things worked *and showed the
  proof* (a screenshot, a test result). You should expect that.

You don't need to know how to write the code. You need to know **what you want, how to
tell whether you got it, and when to say "simpler, please."** That's a skill you
already have — or can build faster than you'd think.

You could build the next one. Really.

---

*Written as the companion to Job Application Agent v1.0.*
