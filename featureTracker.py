import sys
import argparse
import requests
import json
from datetime import datetime, timedelta, date
import yaml

# ---- CONFIG: Load configuration from a YAML file ----
CONFIG_FILE = "/config.yaml"

try:
    with open(CONFIG_FILE, "r") as file:
        config = yaml.safe_load(file)
except FileNotFoundError:
    print(f"Error: Configuration file not found at {CONFIG_FILE}")
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"Error: Failed to parse YAML configuration file: {e}")
    sys.exit(1)

APIKEY = config.get("APIKEY")
BASEURL = config.get("BASEURL")
APIVERSION = config.get("APIVERSION")
SITE_ID = config.get("SITE_ID")
PERIOD = config.get("PERIOD")

if not all([APIKEY, BASEURL, APIVERSION, SITE_ID, PERIOD]):
    print("Error: Missing required configuration values in the YAML file.")
    sys.exit(1)

# ---- HELPERS ----
def get_json(url):
    headers = {"Authorization": f"Bearer {APIKEY}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        sys.exit(1)
    return response.json()

def add_one_month(d):
    year, month = d.year, d.month
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
    day = min(d.day, (date(year, month+1, 1) - timedelta(days=1)).day)
    return date(year, month, day)

def validate_interval_alignment(interval, start_date, end_date):
    if interval == "week":
        if start_date.weekday() != 6 or end_date.weekday() != 5:
            print("Error: For 'week' interval, start date must be Sunday and end date must be Saturday.")
            sys.exit(1)
    elif interval == "month":
        current = start_date
        while current < end_date:
            current = add_one_month(current)
        if current != end_date + timedelta(days=1):
            print("Error: Date range must cover full calendar months for interval 'month'.")
            sys.exit(1)

# ---- MAIN ----
parser = argparse.ArgumentParser()
parser.add_argument("interval", choices=["day", "week", "month"])
parser.add_argument("start_date")
parser.add_argument("end_date")
parser.add_argument("page_path")
parser.add_argument("goals", nargs="+")
args = parser.parse_args()

interval = args.interval
start_str, end_str = args.start_date, args.end_date
page_path = args.page_path
goals = [g.replace('+', ' ') for g in args.goals]  # normalize CLI input


try:
    start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
except ValueError:
    print("Error: Dates must be in YYYY-MM-DD format.")
    sys.exit(1)

if end_date < start_date:
    print("Error: End date must be on or after start date.")
    sys.exit(1)

validate_interval_alignment(interval, start_date, end_date)


# ---- SECTION 1: Aggregate Unique Visitors for All Goals ----
section1_lines = []

base_params = f"site_id={SITE_ID}&period={PERIOD}&date={start_str},{end_str}"
url = f"{BASEURL}{APIVERSION}/breakdown?{base_params}&property=event:goal&metrics=visitors"
data = get_json(url)

# Total up unique visitors for all specified goals (approximation)
total_goal_visitors = 0
goal_visitor_map = {}

for item in data.get("results", []):
    goal = item.get("goal") or item.get("event:goal") or item.get("name")
    if goal in goals:
        count = item.get("visitors", 0)
        goal_visitor_map[goal] = count
        total_goal_visitors += count

# Fetch total site-wide visitors (to cap total if needed)
site_url = f"{BASEURL}{APIVERSION}/aggregate?{base_params}&metrics=visitors"
site_data = get_json(site_url)
site_total_visitors = site_data.get("results", {}).get("visitors", {}).get("value", 0)

total_goal_visitors = min(total_goal_visitors, site_total_visitors)

section1_lines.append(str(total_goal_visitors))
section1_lines.append("\nAggregate Unique Visitors")
section1_lines.append(f"{start_str} to {end_str}")

# Output Section 1
print("\n---\n")
print("\n".join(section1_lines))
print("\n---\n")


# ---- SECTION 2: Aggregate Total Events + Echo Unique Visitors ----
section2_lines = []

# Aggregate total events from specified goals (NOT pageviews)
events_url = f"{BASEURL}{APIVERSION}/breakdown?{base_params}&property=event:goal&metrics=events"
events_data = get_json(events_url)

total_events = 0
for item in events_data.get("results", []):
    goal = item.get("goal") or item.get("event:goal") or item.get("name")
    if goal in goals:
        total_events += item.get("events", 0)

section2_lines.append(str(total_events))
section2_lines.append("  Aggregate Events")
section2_lines.append(str(total_goal_visitors))
section2_lines.append("  Aggregate Unique Visitors")

# Output Section 2
print("\n".join(section2_lines))
print("\n---\n")

# ---- SECTION 3: Events / Visitors per Interval ----
section3_lines = []
section3_lines.append("Aggregate Total Events / Aggregate Unique Visitors")
section3_lines.append(f"\nper {interval}\n\n")

# Build list of intervals
intervals = []
current = start_date
if interval == "day":
    while current <= end_date:
        intervals.append((current, current))
        current += timedelta(days=1)
elif interval == "week":
    while current <= end_date:
        interval_end = current + timedelta(days=6)
        intervals.append((current, interval_end))
        current += timedelta(days=7)
elif interval == "month":
    while current <= end_date:
        next_month = add_one_month(current)
        interval_end = next_month - timedelta(days=1)
        intervals.append((current, interval_end))
        current = next_month

for start, end in intervals:
    s_str = start.strftime("%Y-%m-%d")
    e_str = end.strftime("%Y-%m-%d")
    interval_params = f"site_id={SITE_ID}&period={PERIOD}&date={s_str},{e_str}"
    interval_url = f"{BASEURL}{APIVERSION}/breakdown?{interval_params}&property=event:goal&metrics=visitors,events"
    data = get_json(interval_url)

    visitors = 0
    events = 0
    for item in data.get("results", []):
        goal = item.get("goal") or item.get("event:goal") or item.get("name")
        if goal in goals:
            visitors += item.get("visitors", 0)
            events += item.get("events", 0)

    visitors = min(visitors, total_goal_visitors)
    section3_lines.append(f"{events} / {visitors}\t")

section3_lines.append(f"\n{start_str}")

# Output Section 3
print("".join(section3_lines))
print("\n---\n")


# ---- SECTION 4: Goal Breakdown by Percent of Total Visitors ----
section4_lines = []

# Sort goals by number of visitors (descending)
sorted_goals = sorted(goal_visitor_map.items(), key=lambda x: x[1], reverse=True)

for goal, count in sorted_goals:
    percentage = (count / total_goal_visitors * 100) if total_goal_visitors > 0 else 0
    section4_lines.append(f"{percentage:.2f}% ({count})  {goal}")

# Output Section 4
print("Percent Unique Visitors (Total Unique Visitors) by Goal\n\n")
print("\n".join(section4_lines))
print("\n---\n")


# ---- SECTION 5: Aggregate Conversion Rate ----
section5_lines = []

# Get homepage visitors
home_url = f"{BASEURL}{APIVERSION}/aggregate?{base_params}&metrics=visitors&filters=event:page=={page_path}"
home_data = get_json(home_url)
home_visitors = home_data.get("results", {}).get("visitors", {}).get("value", 0)

# Fetch each goal separately with page filter to avoid undercounting
conversion_visitors = 0
for goal in goals:
    goal_filter = f"event:goal=={goal};event:page=={page_path}"
    goal_url = f"{BASEURL}{APIVERSION}/aggregate?{base_params}&metrics=visitors&filters={goal_filter}"
    goal_data = get_json(goal_url)
    visitors = goal_data.get("results", {}).get("visitors", {}).get("value", 0)
    conversion_visitors += visitors

conversion_visitors = min(conversion_visitors, home_visitors)
conversion_rate = (conversion_visitors / home_visitors * 100) if home_visitors > 0 else 0.0

section5_lines.append(f"{conversion_rate:.2f}%")
section5_lines.append("\nAggregate Conversion Rate")
section5_lines.append("= Unique Visitor Events / Unique Visitors to Page")
section5_lines.append(f"(feature on page = {page_path}")

# Output Section 5
print("\n".join(section5_lines))
print("\n---\n")

# ---- SECTION 6: Conversion Rate per Interval (Single Row) ----
section6_line = []

# Build list of intervals
intervals = []
current = start_date
if interval == "day":
    while current <= end_date:
        intervals.append((current, current))
        current += timedelta(days=1)
elif interval == "week":
    while current <= end_date:
        interval_end = current + timedelta(days=6)
        intervals.append((current, interval_end))
        current += timedelta(days=7)
elif interval == "month":
    while current <= end_date:
        next_month = add_one_month(current)
        interval_end = next_month - timedelta(days=1)
        intervals.append((current, interval_end))
        current = next_month

# Get conversion rate per interval
for start, end in intervals:
    s_str = start.strftime("%Y-%m-%d")
    e_str = end.strftime("%Y-%m-%d")
    interval_params = f"site_id={SITE_ID}&period={PERIOD}&date={s_str},{e_str}"

    # Homepage visitors
    home_url = f"{BASEURL}{APIVERSION}/aggregate?{interval_params}&metrics=visitors&filters=event:page=={page_path}"
    home_data = get_json(home_url)
    home_visitors = home_data.get("results", {}).get("visitors", {}).get("value", 0)

    # Goal conversions on homepage
    goal_page_url = f"{BASEURL}{APIVERSION}/breakdown?{interval_params}&property=event:goal&metrics=visitors&filters=event:page=={page_path}"
    goal_page_data = get_json(goal_page_url)
    conversion_visitors = 0
    for item in goal_page_data.get("results", []):
        goal = item.get("goal") or item.get("event:goal") or item.get("name")
        if goal in goals:
            conversion_visitors += item.get("visitors", 0)

    conversion_visitors = min(conversion_visitors, home_visitors)
    rate = (conversion_visitors / home_visitors * 100) if home_visitors > 0 else 0.0
    section6_line.append(f"{rate:.2f}%")

section6_line.append(f"\n{start_str}") # Final label

# Output Section 6 as a single row
print(f"Aggregate Conversion Rate\nper {interval}\n")
print("\t\t".join(section6_line))
print("\n---\n")
