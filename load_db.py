# ============================================================
# SQL Part 1 - create the MySQL database and load the clean tables
# Folder : <project folder>\  (project root)
# Run    : python load_db.py
# Needs  : python -m pip install pymysql cryptography
# Input  : Output/cdsco_final.csv, fda_final.csv, nfhs5_clean.csv,
#          obj10_imports_clean.csv, obj10_category_to_segment.csv
# Makes  : database device_analysis with tables
#          cdsco, fda, nfhs, imports, category_segment
# Safe to re-run: each table is dropped and rebuilt from the CSV files.
# It asks for your MySQL password when it starts (typing is hidden, nothing is saved).
# ============================================================
import getpass  # tool to ask for the password without showing it
import math  # tool for rounding up column sizes
import sys  # tool to read the optional folder argument and stop the script
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables
import pymysql  # tool to talk to MySQL

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
if len(sys.argv) > 1:  # if a folder was typed after the script name
    BASE = Path(sys.argv[1])  # use that folder instead (only for testing)
OUT = BASE / "Output"  # folder with the clean CSV files

HOST, PORT, USER, DB = "localhost", 3306, "root", "device_analysis"  # connection settings (change USER if you use another account)

# ---------------- what to load ----------------
# name = table name, file = CSV file, usecols = only these columns (None = all),
# date_cols = columns turned into real dates, bool_cols = True/False columns stored as 1/0,
# text_cols = number-looking columns we keep as text, pk = primary key, indexes = columns to index
TABLES = [
    dict(name="cdsco", file="cdsco_final.csv", usecols=None, date_cols=[], bool_cols=["is_renewal"],
         text_cols=["importer_pincode"], pk=None, indexes=["license_no", "category", "license_year", "importer_name"]),
    dict(name="fda", file="fda_final.csv", usecols=None, date_cols=["approved_date", "date_submission"],
         bool_cols=["long_review_flag"], text_cols=[], pk="device_id",
         indexes=["category", "country", "approved_date", "company_name"]),
    dict(name="nfhs", file="nfhs5_clean.csv", usecols=None, date_cols=[], bool_cols=[], text_cols=[],
         pk="district_lgd_code", indexes=["state"]),
    dict(name="imports", file="obj10_imports_clean.csv", usecols=None, date_cols=[], bool_cols=[], text_cols=[],
         pk=None, indexes=["fy", "segment"]),
    dict(name="category_segment", file="obj10_category_to_segment.csv", usecols=["category", "segment", "fit"],
         date_cols=[], bool_cols=[], text_cols=[], pk="category", indexes=[]),
]

# ---------------- helper functions ----------------
def to_text(v):  # turns a number-looking value (like 400001.0) into clean text (400001)
    if pd.isna(v):  # if the cell is blank
        return None  # keep it blank
    if isinstance(v, float) and v.is_integer():  # a whole number stored as a decimal
        return str(int(v))  # drop the .0
    return str(v).strip()  # otherwise just trim spaces

BOOL_WORDS = {"true": 1, "false": 0, "1": 1, "0": 0, "1.0": 1, "0.0": 0, "yes": 1, "no": 0, "y": 1, "n": 0}  # accepted True/False spellings

def sql_type(s, is_date, is_bool):  # decides the MySQL column type from the data itself
    if is_date:  # real date column
        return "DATE"  # date type
    if is_bool:  # True/False column
        return "TINYINT(1)"  # 1 or 0
    if pd.api.types.is_integer_dtype(s):  # whole numbers
        return "INT"  # integer type
    if pd.api.types.is_float_dtype(s):  # decimals (or whole numbers with blanks)
        v = s.dropna()  # ignore blanks
        if len(v) and (v % 1 == 0).all():  # all values are whole numbers
            return "INT"  # integer type
        return "DOUBLE"  # real decimals
    n = s.dropna().astype(str).str.len().max()  # longest text in the column
    n = 0 if pd.isna(n) else int(n)  # blank column -> 0
    if n > 500:  # very long text
        return "TEXT"  # long text type
    return f"VARCHAR({max(20, math.ceil((n + 10) / 50) * 50)})"  # text with a safe length

def prepare(t):  # reads one CSV and returns the cleaned table plus its column types
    df = pd.read_csv(OUT / t["file"], usecols=t["usecols"], low_memory=False)  # read the CSV
    for c in t["date_cols"]:  # real dates
        before = df[c].isna().sum()  # blanks before
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date  # text -> date (bad text becomes blank)
        bad = df[c].isna().sum() - before  # new blanks created
        if bad:  # if some dates could not be read
            print(f"  NOTE: {t['name']}.{c}: {bad} values could not be read as dates (stored as blank)")  # tell the user
    for c in t["bool_cols"]:  # True/False columns
        m = df[c].astype(str).str.strip().str.lower().map(BOOL_WORDS)  # text -> 1 or 0
        bad = int(m.isna().sum() - df[c].isna().sum())  # values that were not understood
        if bad:  # if some values were not understood
            print(f"  NOTE: {t['name']}.{c}: {bad} values not understood (stored as blank)")  # tell the user
        df[c] = m  # keep the 1/0 version
    for c in t["text_cols"]:  # number-looking columns kept as text
        df[c] = df[c].map(to_text)  # clean text version
    types = {}  # column -> MySQL type
    for c in df.columns:  # decide each column's type
        types[c] = sql_type(df[c], c in t["date_cols"], c in t["bool_cols"])  # pick the type
    return df, types  # give both back

def build_ddl(t, types):  # writes the CREATE TABLE command
    parts = [f"`{c}` {ty}" for c, ty in types.items()]  # one line per column
    if t["pk"]:  # primary key
        parts.append(f"PRIMARY KEY (`{t['pk']}`)")  # add it
    for c in t["indexes"]:  # normal indexes to speed up queries
        pre = "(100)" if types[c] == "TEXT" else ""  # long text needs a prefix length
        parts.append(f"INDEX `ix_{t['name']}_{c}` (`{c}`{pre})")  # add it
    return f"CREATE TABLE `{t['name']}` (\n  " + ",\n  ".join(parts) + "\n) DEFAULT CHARSET=utf8mb4"  # full command

# ---------------- connect ----------------
pw = getpass.getpass(f"MySQL password for {USER}@{HOST}: ")  # ask for the password (hidden)
try:  # try to connect
    conn = pymysql.connect(host=HOST, port=PORT, user=USER, password=pw, charset="utf8mb4")  # open the connection
except Exception as e:  # if it fails
    print("STOP - could not connect to MySQL:", e)  # show the reason
    print("Check: the MySQL80 service is running, the password is right, and USER/PORT at the top of this script.")  # hints
    sys.exit(1)  # stop here
cur = conn.cursor()  # object that sends commands
cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB}` DEFAULT CHARACTER SET utf8mb4")  # make the database if it is missing
cur.execute(f"USE `{DB}`")  # work inside it
print(f"Connected. Using database {DB}\n")  # confirm

# ---------------- build and load every table ----------------
for t in TABLES:  # go through each table
    print(f"Loading {t['name']} from {t['file']} ...")  # progress message
    df, types = prepare(t)  # read and clean the CSV
    cur.execute(f"DROP TABLE IF EXISTS `{t['name']}`")  # remove an old copy
    cur.execute(build_ddl(t, types))  # create the table
    df = df.astype(object).where(df.notna(), None)  # blanks become NULL
    cols = ", ".join(f"`{c}`" for c in df.columns)  # column list for the INSERT
    marks = ", ".join(["%s"] * len(df.columns))  # one placeholder per column
    sql = f"INSERT INTO `{t['name']}` ({cols}) VALUES ({marks})"  # the INSERT command
    rows = list(df.itertuples(index=False, name=None))  # all rows as plain tuples
    for i in range(0, len(rows), 2000):  # send 2,000 rows at a time
        cur.executemany(sql, rows[i:i + 2000])  # insert a batch
    conn.commit()  # save this table
    print(f"  {len(rows):,} rows loaded, {len(types)} columns")  # confirm

# ---------------- verify against numbers we already confirmed in Python ----------------
CHECKS = [  # label, SQL, expected value
    ("cdsco rows", "SELECT COUNT(*) FROM cdsco", "24,563"),
    ("cdsco unique licences", "SELECT COUNT(DISTINCT license_no) FROM cdsco", "5,163"),
    ("cdsco licence-category pairs", "SELECT COUNT(*) FROM (SELECT DISTINCT license_no, category FROM cdsco) t", "6,714"),
    ("fda rows", "SELECT COUNT(*) FROM fda", "47,375"),
    ("fda rows 2018-2026", "SELECT COUNT(*) FROM fda WHERE YEAR(approved_date) BETWEEN 2018 AND 2026", "24,880"),
    ("fda rows with country = IN", "SELECT COUNT(*) FROM fda WHERE country = 'IN'", "202"),
    ("nfhs districts", "SELECT COUNT(*) FROM nfhs", "704"),
    ("nfhs states", "SELECT COUNT(DISTINCT state) FROM nfhs", "34"),
    ("imports rows", "SELECT COUNT(*) FROM imports", "30"),
    ("imports total 2019-20 (USD Mn)", "SELECT ROUND(SUM(import_usd_mn), 1) FROM imports WHERE fy = '2019-20'", "5,845.4"),
    ("category_segment rows", "SELECT COUNT(*) FROM category_segment", "18"),
]
print("\n=== CHECKS (SQL result vs the number we confirmed in Python) ===")  # heading
ok = 0  # counter of passed checks
for label, q, exp in CHECKS:  # run every check
    cur.execute(q)  # run the query
    v = cur.fetchone()[0]  # read the answer
    got = f"{float(v):,.1f}" if not isinstance(v, int) else f"{v:,}"  # format like the expected text
    flag = "OK" if got == exp else "MISMATCH"  # compare
    ok += flag == "OK"  # count passes
    print(f"{label:34} {got:>10}   expected {exp:>10}   {flag}")  # one line per check
print(f"\n{ok} of {len(CHECKS)} checks passed")  # summary
conn.close()  # close the connection