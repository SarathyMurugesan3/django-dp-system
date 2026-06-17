"""
Django Management Command — PLFS Fixed-Width TXT to CSV Converter
=================================================================
Place this file at:
  proj/risk_assessment/management/commands/plfs_convert.py

Run it like:
  python manage.py plfs_convert --file "C:/Users/sarat/Downloads/MHH_Q2_Q4_2025.txt" --type HH
  python manage.py plfs_convert --file "C:/Users/sarat/Downloads/MPER_Q2_Q4_2025.txt" --type PER

Optional flags:
  --output "C:/Users/sarat/Downloads/my_result.csv"   custom output path
  --encoding utf-8                                     default is latin-1
"""

import csv
import os
from django.core.management.base import BaseCommand


# ─────────────────────────────────────────────────────────────────────────────
# HOUSEHOLD LEVEL LAYOUT  (MHH_Q2_Q4_2025.txt  |  record length 128)
# (field_name, start_byte, end_byte)  — bytes are 1-based, from the Excel file
# ─────────────────────────────────────────────────────────────────────────────
HOUSEHOLD_LAYOUT = [
    ("FILE_ID",          1,   5),
    ("SCHEDULE",         6,   8),
    ("QUARTER",          9,  10),
    ("MONTH",           11,  12),
    ("VISIT",           13,  14),
    ("SECTOR",          15,  15),
    ("STATE_UT",        16,  17),
    ("DISTRICT",        18,  19),
    ("NSS_REGION",      20,  22),
    ("BASIC_STRATUM",   23,  26),
    ("STRATUM",         27,  29),
    ("GROUP",           30,  30),
    ("SUB_STRATUM",     31,  32),
    ("FOD_SUB_REGION",  33,  36),
    ("FSU",             37,  41),
    ("STAGE2_STRATUM",  42,  42),
    ("SAMPLE_HH_NO",    43,  44),
    ("MONTH_SURVEY",    45,  46),
    ("RESPONSE_CODE",   47,  47),
    ("SURVEY_CODE",     48,  48),
    ("REASON_SUBST",    49,  49),
    ("HH_SIZE",         50,  51),
    ("HH_TYPE",         52,  52),
    ("RELIGION",        53,  53),
    ("SOCIAL_GROUP",    54,  54),
    ("HH_CONS_EXP",     55,  64),
    ("LAND_POSSESSED",  65,  66),
    ("LAND_LEASED_OUT", 67,  68),
    ("HH_INCOME",       69,  78),
    ("INFORMANT_SL",    79,  80),
    ("SURVEY_DATE",     81,  90),
    ("TIME_CANVASS",    91,  94),
    ("NS_COUNT",        95,  97),
    ("MULTIPLIER",      98, 107),
    ("TOTAL_SUBDIV",   108, 110),
    ("STRATUM_SIZE",   111, 120),
    ("LISTED_HH",      121, 124),
    ("SELECTED_HH",    125, 126),
    ("PANEL_CODE",     127, 128),
]


# ─────────────────────────────────────────────────────────────────────────────
# PERSON LEVEL LAYOUT  (MPER_Q2_Q4_2025.txt  |  record length 301)
# ─────────────────────────────────────────────────────────────────────────────
PERSON_LAYOUT = [
    ("FILE_ID",          1,   5),
    ("SCHEDULE",         6,   8),
    ("QUARTER",          9,  10),
    ("MONTH",           11,  12),
    ("VISIT",           13,  14),
    ("SECTOR",          15,  15),
    ("STATE_UT",        16,  17),
    ("DISTRICT",        18,  19),
    ("NSS_REGION",      20,  22),
    ("BASIC_STRATUM",   23,  26),
    ("STRATUM",         27,  29),
    ("GROUP",           30,  30),
    ("SUB_STRATUM",     31,  32),
    ("FOD_SUB_REGION",  33,  36),
    ("FSU",             37,  41),
    ("STAGE2_STRATUM",  42,  42),
    ("SAMPLE_HH_NO",    43,  44),
    ("PERSON_SL",       45,  46),
    ("RELATION_HEAD",   47,  47),
    ("GENDER",          48,  48),
    ("AGE",             49,  51),
    ("MARITAL_STATUS",  52,  52),
    ("GEN_EDUC",        53,  54),
    ("TECH_EDUC",       55,  56),
    # Day 7
    ("DAS11",           57,  58),
    ("IND11",           59,  60),
    ("HR11",            61,  62),
    ("ERN11",           63,  67),
    ("DAS21",           68,  69),
    ("IND21",           70,  71),
    ("HR21",            72,  73),
    ("ERN21",           74,  78),
    ("HR1",             79,  80),
    ("AHR1",            81,  82),
    # Day 6
    ("DAS12",           83,  84),
    ("IND12",           85,  86),
    ("HR12",            87,  88),
    ("ERN12",           89,  93),
    ("DAS22",           94,  95),
    ("IND22",           96,  97),
    ("HR22",            98,  99),
    ("ERN22",          100, 104),
    ("HR2",            105, 106),
    ("AHR2",           107, 108),
    # Day 5
    ("DAS13",          109, 110),
    ("IND13",          111, 112),
    ("HR13",           113, 114),
    ("ERN13",          115, 119),
    ("DAS23",          120, 121),
    ("IND23",          122, 123),
    ("HR23",           124, 125),
    ("ERN23",          126, 130),
    ("HR3",            131, 132),
    ("AHR3",           133, 134),
    # Day 4
    ("DAS14",          135, 136),
    ("IND14",          137, 138),
    ("HR14",           139, 140),
    ("ERN14",          141, 145),
    ("DAS24",          146, 147),
    ("IND24",          148, 149),
    ("HR24",           150, 151),
    ("ERN24",          152, 156),
    ("HR4",            157, 158),
    ("AHR4",           159, 160),
    # Day 3
    ("DAS15",          161, 162),
    ("IND15",          163, 164),
    ("HR15",           165, 166),
    ("ERN15",          167, 171),
    ("DAS25",          172, 173),
    ("IND25",          174, 175),
    ("HR25",           176, 177),
    ("ERN25",          178, 182),
    ("HR5",            183, 184),
    ("AHR5",           185, 186),
    # Day 2
    ("DAS16",          187, 188),
    ("IND16",          189, 190),
    ("HR16",           191, 192),
    ("ERN16",          193, 197),
    ("DAS26",          198, 199),
    ("IND26",          200, 201),
    ("HR26",           202, 203),
    ("ERN26",          204, 208),
    ("HR6",            209, 210),
    ("AHR6",           211, 212),
    # Day 1
    ("DAS17",          213, 214),
    ("IND17",          215, 216),
    ("HR17",           217, 218),
    ("ERN17",          219, 223),
    ("DAS27",          224, 225),
    ("IND27",          226, 227),
    ("HR27",           228, 229),
    ("ERN27",          230, 234),
    ("HR7",            235, 236),
    ("AHR7",           237, 238),
    # CWS
    ("TOTHRS_WRK",     239, 241),
    ("TOTADL_WRK",     242, 244),
    ("ACWS",           245, 246),
    ("AIND_CWS",       247, 248),
    ("OCU_CWS",        249, 251),
    ("ERN_REG",        252, 259),
    ("ERN_SELF",       260, 267),
]


# ─────────────────────────────────────────────────────────────────────────────
# Django Management Command
# ─────────────────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = "Convert PLFS fixed-width .txt file to CSV (Household or Person level)"

    # ── 1. Define command-line arguments ─────────────────────────────────────
    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Full path to the input .txt file  e.g. C:/Users/sarat/Downloads/MHH_Q2_Q4_2025.txt",
        )
        parser.add_argument(
            "--type",
            type=str,
            required=True,
            choices=["HH", "PER"],
            help="HH = Household level | PER = Person level",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Full path for the output CSV (optional). "
                 "Default: same folder as input, same name with .csv extension",
        )
        parser.add_argument(
            "--encoding",
            type=str,
            default="latin-1",
            help="File encoding (default: latin-1). Try utf-8 if you see errors.",
        )

    # ── 2. Main logic ─────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        input_path = options["file"]
        file_type  = options["type"]
        output_path = options["output"]
        encoding   = options["encoding"]

        # ── Step 1: Validate input file exists ────────────────────────────────
        if not os.path.exists(input_path):
            self.stdout.write(self.style.ERROR(f"[ERROR] File not found: {input_path}"))
            return

        # ── Step 2: Pick the correct layout ───────────────────────────────────
        if file_type == "HH":
            layout = HOUSEHOLD_LAYOUT
            label  = "Household"
        else:
            layout = PERSON_LAYOUT
            label  = "Person"

        # ── Step 3: Auto-generate output path if not provided ─────────────────
        if not output_path:
            base        = os.path.splitext(input_path)[0]   # remove .txt
            output_path = base + ".csv"                      # add .csv

        # ── Step 4: Extract column names and byte slices from the layout ──────
        headers = [col[0] for col in layout]

        # Excel layout uses 1-based bytes  →  convert to 0-based Python slices
        # Example: start=1, end=5  →  line[0:5]
        slices = [(col[1] - 1, col[2]) for col in layout]

        # ── Step 5: Print a summary before starting ───────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 55))
        self.stdout.write(self.style.SUCCESS("  PLFS Fixed-Width → CSV Converter"))
        self.stdout.write(self.style.SUCCESS("=" * 55))
        self.stdout.write(f"  Type    : {label} level")
        self.stdout.write(f"  Input   : {input_path}")
        self.stdout.write(f"  Output  : {output_path}")
        self.stdout.write(f"  Fields  : {len(layout)}")
        self.stdout.write(f"  Encoding: {encoding}")
        self.stdout.write("")

        # ── Step 6: Read fixed-width file and write CSV ───────────────────────
        total_rows   = 0
        skipped_rows = 0

        try:
            with open(input_path, "r", encoding=encoding, errors="replace") as infile, \
                 open(output_path, "w", newline="", encoding="utf-8") as outfile:

                writer = csv.writer(outfile)

                # Write header row first
                writer.writerow(headers)

                # Process each line
                for lineno, line in enumerate(infile, start=1):

                    # Remove newline characters but KEEP internal spaces
                    # (spaces are meaningful in fixed-width format)
                    raw = line.rstrip("\r\n")

                    # Skip completely blank lines
                    if not raw:
                        skipped_rows += 1
                        continue

                    # Slice each field from the line using the layout positions
                    row = []
                    for start, end in slices:
                        if start >= len(raw):
                            # Line is shorter than expected → empty cell
                            row.append("")
                        else:
                            # Slice the field and strip leading/trailing spaces
                            row.append(raw[start:end].strip())

                    writer.writerow(row)
                    total_rows += 1

                    # Show live progress every 10,000 rows
                    if total_rows % 10000 == 0:
                        self.stdout.write(f"  ... {total_rows:,} rows processed", ending="\r")

        except PermissionError:
            self.stdout.write(self.style.ERROR(
                f"[ERROR] Cannot write to: {output_path}\n"
                "        Is the file already open in Excel? Close it and try again."
            ))
            return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] {e}"))
            return

        # ── Step 7: Print final summary ───────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"[OK] Conversion completed!"))
        self.stdout.write(f"     Records written : {total_rows:,}")
        if skipped_rows:
            self.stdout.write(f"     Blank lines skipped: {skipped_rows}")
        self.stdout.write(f"     Output file     : {output_path}")
        self.stdout.write("")