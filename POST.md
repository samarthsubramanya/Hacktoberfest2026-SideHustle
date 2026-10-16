*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I Built

**Shoebox** is a receipt sorter for gig workers and freelancers that runs entirely on their own laptop.

If you drive for Uber, deliver for DoorDash, or freelance on the side, the IRS treats you as a small business. Every gas fill-up, phone bill and box of printer ink can lower your tax bill, but only if you can show it. So you end up with a literal shoebox, or a camera roll of 400 crumpled receipts, and in April you have two bad options:

1. Pay a bookkeeper $150 to $300 to sort them.
2. Upload a photo of every purchase you made this year to a "free" expense app.

Shoebox is a third option. You put the photos in a folder and run one command. A vision model running on your own machine reads each receipt, files it under the matching line of **IRS Schedule C** (the tax form for self-employment income), and writes one sentence explaining why. You look the results over on a single page, fix anything that's off, and export a CSV your accountant or tax software can use.

**Who would pay:** the tens of millions of Americans who earn some of their income as independent workers. They aren't big enough to hire a bookkeeper, and their receipts are too personal to hand to a startup. I'd price it at **$19, paid once**. That price only works because each receipt costs nothing to process. More on that below.

## Demo

<!-- TODO: embed a 60–90s screen recording: drop folder → terminal sorting → review page → fix the flagged $0 → export CSV -->

Here's a run on a sample shoebox of seven receipts:

```
$ python3 shoebox.py ./receipts --work "freelance graphic designer who also drives rideshare"
[1/7] reading adobe.png ... Adobe Inc. $64.85 -> 18 Office expense
[2/7] reading carwash.jpg ... MISTER CAR WASH $39.99 -> 9 Car and truck expenses
[3/7] reading coffee.jpg ... STARBUCKS $14.48 -> 24b Meals (50%)
[4/7] reading gas.jpg ... SHELL $41.33 -> 9 Car and truck expenses
[5/7] reading groceries.jpg ... TRADER JOE'S #172 $22.93 -> Personal (not deductible)
[6/7] reading phone.jpg ... T-MOBILE $101.64 -> 25 Utilities
[7/7] reading staples.jpg ... STAPLES $60.29 -> 22 Supplies
```

The coffee result is my favorite. The receipt had a note printed on it, *"Met client re: logo revisions."* The model used it to file the purchase as a business meal and applied the 50% limit for meals. It also left the groceries out of the deductions.

The review page shows each receipt photo next to its extracted fields. The Schedule C totals update live as you make corrections, and anything suspicious, like a $0 total, is outlined in orange:

<!-- TODO: screenshot of review page -->

## Code

<!-- TODO: {% embed https://github.com/<you>/shoebox %} -->

It's two files: `shoebox.py` (about 200 lines of Python using only the standard library, with Pillow optional) and `review.html` (one page, no framework). There's also `make_samples.py`, which generates fake receipts so you can try it without sharing your own.

## How I Built It

**Model:** [Qwen3-VL 8B](https://ollama.com/library/qwen3-vl), an open-weight vision-language model, running locally in **Ollama** on a MacBook (M5 Pro, 24 GB).

**Pipeline:**

1. Shoebox scans the folder for images. Each one is hashed, so a photo it has already read is never processed again (and dropping the same receipt in twice doesn't count it twice).
2. Each image is shrunk to 1280 px and sent to Ollama's `/api/chat` with a **JSON schema** passed in `format`. Ollama enforces the schema at decode time, so the model can only return a valid object, and its `category` must be one of the Schedule C lines.
3. Results are saved to `shoebox.json` after every receipt, so a crash halfway through loses nothing.
4. A tiny standard-library HTTP server, bound to `127.0.0.1` only, serves the review page and the CSV export.

The `--work` flag matters more than it looks. A car wash is a business expense for a rideshare driver and a personal one for a designer who works from home. The same model gives the right answer for each person because it's told who it's working for.

### Two things that broke, and how I fixed them

**1. The model chose before it explained.** My first schema listed `category` before `reason`. For a gas receipt, the model filed it as *Personal*, then wrote a reason arguing it was a deductible vehicle expense. The output is generated left to right, so it had committed to an answer before it thought it through. **Moving `reason` above `category` in the schema** made it explain first and then decide. I also added a one-line description of each Schedule C line to the prompt, because an 8B model doesn't know offhand what "Line 10" covers. With both changes, it filed all 7 sample receipts correctly.

**2. `think: false` behaves differently across Ollama versions.** On Ollama 0.34, turning off thinking made Qwen3-VL put its JSON in the `thinking` field and leave `content` empty. After Ollama updated to 0.40 mid-build, the model reasoned anyway and used up my 400-token output limit before it got to the JSON. The fix is to read whichever field is filled and raise the limit to 3000 tokens. That's enough room to think, and it still stops a model that runs away.

Neither fix needed a vendor support ticket. The model and the server are on my machine, so I could see exactly what was happening.

### Results on the sample set

| | |
|---|---|
| Schedule C line correct | **7 / 7** |
| Totals correct | **7 / 7** (one receipt needed the larger token limit) |
| Speed | about 30 s per receipt with reasoning on |
| Cost per receipt | **$0.00** |

One honest note: with reasoning turned off, which is much faster, the model once read the phone bill as $0.00. That's why the review page exists. **The product isn't "AI does your taxes." It's a 30-second review where the machine has done the tedious part and highlighted what needs a human.**

## Why Does Open Innovation Matter?

**Because a year of receipts is a map of your life.** They show where you drive, what you eat, which pharmacy you use, and when you're short on money. The people who most need help with this paperwork, gig workers living from one payout to the next, are exactly the people expense apps ask to give all of that up. A model on their own laptop removes the trade-off. After the one-time model download, Shoebox needs no internet connection at all.

**Because the unit economics only work at $0 per receipt.** A cloud vision API costs real money per image. Multiply that by hundreds of receipts per user and you're pushed into a subscription, for a tool people use mainly once a year in tax season. Open weights let me sell it as a $19 tool you buy once and own, the way software used to be sold.

**Because I could open it up and fix it.** Both bugs above were in how the model and server behave, and I fixed both in the request itself in minutes. With a closed API I'd have had a prompt, a support forum and hope. Open weights also mean swapping models is one flag (`--model`), and fine-tuning on a few hundred labeled receipts for a niche like long-haul truckers or wedding photographers is a weekend project, not an enterprise contract.

**Because nobody can raise the price on me.** No pricing change or deprecation notice can break Shoebox for someone who has already bought it.

## My Agent Session

<!-- TODO: {% agent_session <id> %} -->

I built this with Claude Code as a pair programmer. The session includes the dead ends: model weights that had gone missing from disk, an Ollama server serving a stale copy of the model, and the schema-ordering discovery.

## Prize Categories

<!-- None this week: Shoebox uses Qwen3-VL via Ollama, not a partner technology. Remove this section if no category applies. -->
