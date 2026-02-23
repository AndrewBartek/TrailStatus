import requests
from bs4 import BeautifulSoup
import os
import sys

RAMBO_URL = "https://www.rambo-mtb.org/"
IFTTT_WEBHOOK_KEY = os.environ.get("IFTTT_WEBHOOK_KEY")  # Set in GitHub Actions secrets
IFTTT_EVENT_NAME = "freeride_status_change"               # Match this in your IFTTT applet


def get_freeride_status():
    """Scrape the RAMBO homepage and return 'open' or 'closed' for Freeride."""
    response = requests.get(RAMBO_URL, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text()

    # Find the line containing "Freeride" in the trail status section
    for line in page_text.splitlines():
        if "Freeride" in line and ("✅" in line or "❌" in line):
            if "✅" in line:
                return "open"
            elif "❌" in line:
                return "closed"

    return None  # Status not found


def trigger_ifttt(status):
    """Send a webhook to IFTTT with the current trail status."""
    if not IFTTT_WEBHOOK_KEY:
        print("ERROR: IFTTT_WEBHOOK_KEY environment variable not set.")
        sys.exit(1)

    url = f"https://maker.ifttt.com/trigger/{IFTTT_EVENT_NAME}/with/key/{IFTTT_WEBHOOK_KEY}"
    payload = {
        "value1": f"Big Creek Freeride is now {status.upper()}",
        "value2": status,
        "value3": RAMBO_URL
    }

    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print(f"IFTTT triggered successfully: Freeride is {status}")
    else:
        print(f"IFTTT trigger failed: {response.status_code} - {response.text}")
        sys.exit(1)


def main():
    # Allow passing a previous status via environment variable or command-line arg
    # GitHub Actions will pass this via env var LAST_KNOWN_STATUS
    last_status = os.environ.get("LAST_KNOWN_STATUS", "").strip().lower()
    current_status = get_freeride_status()

    if current_status is None:
        print("Could not determine Freeride status from page. Check the parser.")
        sys.exit(1)

    print(f"Current Freeride status: {current_status}")
    print(f"Last known status: {last_status or '(none)'}")

    # Output current status for GitHub Actions to capture
    # Add to GITHUB_OUTPUT so the workflow can store it as a step output
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"freeride_status={current_status}\n")

    # Trigger IFTTT only if status has changed (or if no prior status is known)
    if current_status != last_status:
        print(f"Status changed from '{last_status}' to '{current_status}' — triggering IFTTT.")
        trigger_ifttt(current_status)
    else:
        print("Status unchanged. No IFTTT trigger needed.")


if __name__ == "__main__":
    main()
