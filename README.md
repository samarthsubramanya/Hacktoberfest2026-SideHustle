# 🧾 Shoebox

A receipt sorter for gig workers and freelancers that runs entirely on your laptop.
Drop receipt photos in a folder. A local vision model (Qwen3-VL 8B via Ollama) reads each one,
files it under the right IRS Schedule C line, and explains why. You check the results on one page
and export a CSV for your accountant.

Nothing leaves the machine. No account, no upload, no per-receipt fee.

## Run it

```bash
ollama pull qwen3-vl:8b
python3 shoebox.py ./my_receipts --work "rideshare driver"
```

Then open http://localhost:8765. Correct anything that looks off, tick **Looks right**, and hit **Export CSV**.

- `--work` tells the model what you do. A car wash is a business expense for a driver and personal for a designer.
- `--model` swaps in any Ollama vision model.
- Results are cached in `shoebox.json` inside the folder, keyed by image hash, so re-runs only read new photos.
- Requires Python 3 and Ollama. Pillow is optional (it shrinks phone photos so they process faster).
- Try it with no real data: `python3 make_samples.py` writes 7 fake receipts to `sample_receipts/`.

## What it did on the sample shoebox (M5 Pro, 24 GB)

| | |
|---|---|
| Receipts | 7 (gas, car wash, coffee with client, Staples, phone bill, Adobe, groceries) |
| Time | about 30 s per receipt (Ollama 0.40, where Qwen3-VL reasons before answering); 51 s for all 7 on Ollama 0.34 with reasoning off |
| Schedule C line correct | 7 / 7, including groceries flagged as personal and coffee at 50% because the receipt said "Met client re: logo revisions" |
| Totals correct | 7 / 7 with reasoning. With reasoning off, the phone bill came back as $0; the review page flags $0 totals in orange, and fixing it took one edit. |
| Cost | $0 |

## Notes from building it (material for the post)

- **Why the model runs locally:** a year of receipts is a map of your life: where you drive, what you eat, which clinic you visit. Gig workers are the people least able to pay a bookkeeper and most likely to be asked to upload their data to "free" apps. A local model removes that trade-off.
- **Why the price can be low:** with $0 marginal cost per receipt, this can be sold as a $19 one-time download instead of a $10/month subscription that has to cover API bills.
- **Open weights let me fix the model's behavior myself:** two quirks surfaced, and both were fixed in the request, not by waiting on a vendor:
  1. `think: false` behaves differently across Ollama versions. On 0.34, Qwen3-VL put its JSON in `thinking` and left `content` empty. On 0.40 it reasons anyway, and a 400-token cap cut the answer off mid-JSON. Shoebox reads whichever field is filled and allows 3000 tokens, so it still stops if the model runs away.
  2. With `category` listed before `reason` in the JSON schema, the model chose "Personal" for gas and then wrote a reason arguing it was deductible. Putting `reason` first in the schema, plus a one-line description of each Schedule C line in the prompt, fixed it.
- **Human review is part of the design:** the model is right most of the time. The product is the 30-second review pass, with suspicious values flagged, not blind automation.

## Limits

Images only for now (PDF invoices: add when someone asks). Not tax advice. The categories are a starting point for a preparer, not a filing.
