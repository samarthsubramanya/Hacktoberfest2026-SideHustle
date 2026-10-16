"""Generate fake receipt photos for demoing Shoebox without sharing anyone's real receipts."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

RECEIPTS = {
    "gas.jpg": ["SHELL #04417", "1820 E APACHE BLVD", "TEMPE AZ 85281", "", "10/03/2026  07:42", "PUMP 6  UNLEADED",
                "11.204 GAL @ $3.689", "", "FUEL           $41.33", "TAX             $0.00", "TOTAL          $41.33",
                "", "VISA ****4417", "APPROVED"],
    "coffee.jpg": ["STARBUCKS", "Store #12093 Mill Ave", "", "09/28/2026 2:15 PM", "", "Grande Latte       5.45",
                   "Turkey Pesto Pan   7.95", "", "Subtotal          13.40", "Tax                1.08",
                   "Total             14.48", "", "MASTERCARD ****2210", "Met client re: logo revisions"],
    "staples.jpg": ["STAPLES", "Store 1123  Tempe AZ", "", "10/01/2026 11:03", "", "HP 64XL INK BLACK   34.99",
                    "COPY PAPER 500CT     9.49", "SHARPIE 12PK        11.29", "", "SUBTOTAL            55.77",
                    "SALES TAX 8.1%       4.52", "TOTAL               60.29", "", "VISA ****4417"],
    "phone.jpg": ["T-MOBILE", "Monthly Statement", "", "Bill date: 09/22/2026", "Account ****8812", "",
                  "Magenta Plan         70.00", "Device installment   22.50", "Taxes & fees          9.14", "",
                  "TOTAL DUE           101.64", "AUTOPAY - DEBIT ****0091"],
    "groceries.jpg": ["TRADER JOE'S #172", "6460 S McClintock Dr", "", "10/05/2026 18:20", "", "BANANAS          0.99",
                      "FROZEN GYOZA     3.99", "OAT MILK         3.49", "CHOC ALMONDS     5.99", "CHICKEN THIGHS   8.47",
                      "", "TOTAL           22.93", "DEBIT ****0091"],
    "carwash.jpg": ["MISTER CAR WASH", "Tempe - Rural Rd", "", "10/07/2026 09:11", "", "Unlimited Monthly",
                    "  Platinum Plan     39.99", "Tax                0.00", "TOTAL             39.99", "",
                    "VISA ****4417", "Thank you!"],
    "adobe.png": ["Adobe Inc.", "Invoice  IE20260915-0042", "", "Invoice date: 15-SEP-2026", "",
                  "Creative Cloud All Apps", "  Monthly plan        59.99", "Sales tax            4.86",
                  "Total (USD)         64.85", "", "Paid with VISA ****4417"],
}

font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 26)
out = Path(__file__).parent / "sample_receipts"
for i, (name, lines) in enumerate(RECEIPTS.items()):
    paper = Image.new("RGB", (520, 60 + 38 * len(lines)), "#fbf8f0")
    d = ImageDraw.Draw(paper)
    for j, line in enumerate(lines):
        d.text((30, 30 + 38 * j), line, fill="#2a2a2a", font=font)
    photo = Image.new("RGB", (700, paper.height + 200), "#7a6a58")  # "table" behind the receipt
    photo.paste(paper.rotate((i % 3 - 1) * 2.5, expand=True, fillcolor="#7a6a58"), (90, 100))
    photo.filter(ImageFilter.GaussianBlur(0.6)).save(out / name)
print("wrote", len(RECEIPTS), "receipts to", out)
