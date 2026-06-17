"""
Entry point for the SEC agent.

Local run:        python main.py
Local dry run:    python main.py --dry-run   (prints report, skips Telegram)
Railway cron:     set start command to `python main.py`

The --dry-run flag lets you verify collection + summarization output
without Telegram credentials configured.
"""

import sys

from agents import sec_agent


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        # Run collect -> summarize -> format only, print to stdout.
        from agents.sec_agent import collect, format_report, summarize

        state = {"documents": [], "report_text": "", "errors": [], "delivery": {}}
        state = collect(state)
        state = summarize(state)
        state = format_report(state)
        print(state["report_text"])
        if state["errors"]:
            print("\n--- ERRORS ---")
            for e in state["errors"]:
                print(e)
        return

    result = sec_agent.run()
    print(f"Documents collected: {len(result['documents'])}")
    print(f"Delivery: {result['delivery']}")
    if result["errors"]:
        print(f"Non-fatal errors: {len(result['errors'])}")
        for e in result["errors"]:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
