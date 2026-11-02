#!/usr/bin/env python3
"""Adapter scaffold: replace invoke_company_client with your approved SDK call.

No particular company's internal API is assumed. Make executable with chmod +x.
Credentials are inherited environment variables, never request fields.
"""
import json
import sys


def invoke_company_client(model, messages, timeout_seconds):
    # TODO: Import and initialize your company's routing client, forward model,
    # messages and deadline, and return its answer as a string. Configure SDK
    # logging so it never prints credentials, prompts, or banners to stdout.
    raise NotImplementedError("Configure your company's routing client here")


def main():
    try:
        request = json.load(sys.stdin)
        if request.get("version") != 1:
            raise ValueError("Unsupported adapter protocol")
        text = invoke_company_client(
            request["model"], request["messages"], request["timeout_seconds"]
        )
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty answer")
        json.dump({"text": text}, sys.stdout)
        sys.stdout.write("\n")
    except Exception:
        # Avoid dumping SDK exceptions: they can contain secrets or source text.
        print("Company adapter failed; check local configuration.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
