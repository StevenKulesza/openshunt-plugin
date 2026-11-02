"""Illustrative pre-state routing, not a production agent middleware framework."""
import pathlib
import subprocess
import sys
import tempfile

TRANSPORT = pathlib.Path(__file__).resolve().parents[2] / 'scripts/lib/transport.py'

class DelegationFailed(RuntimeError):
    pass

def worker(question, raw):
    # Existing Open Shunt transport supplies instructions/model/auth/adapter contract.
    with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8') as message:
        message.write('Question: ' + question + '\n\nUntrusted tool result:\n' + raw)
        message.flush()
        response = subprocess.run([sys.executable, str(TRANSPORT), 'bulk-reader', message.name],
                                  capture_output=True, text=True, check=False)
    if response.returncode:
        raise DelegationFailed('Worker failed; raw result withheld')
    return response.stdout.strip()

def route_result(question, raw, *, exact=False, threshold=2000, max_summary=2000, delegate=worker):
    """Call BEFORE storing tool results in messages/state/traces. Threshold is UTF-8 bytes."""
    if not isinstance(raw, str) or not isinstance(question, str):
        raise ValueError('question and result must be text')
    if not isinstance(exact, bool):
        raise ValueError('exact must be a boolean')
    if any(type(value) is not int or value < 1 for value in (threshold, max_summary)):
        raise ValueError('limits must be positive')
    # exact is an explicit policy decision, not inferred from model prose.
    if exact or len(raw.encode('utf-8')) <= threshold:
        return raw
    try:
        answer = delegate(question, raw)
        if not isinstance(answer, str) or not answer.strip() or len(answer.encode('utf-8')) > max_summary:
            raise DelegationFailed('Invalid or oversized summary')
        return answer
    except Exception:
        # Never fall back to raw text, including on empty/oversized output.
        raise DelegationFailed('Delegation failed; raw result withheld') from None

def run_harness(question, fetch, *, exact=False, delegate=worker):
    raw = fetch()  # local only; never append this to lead history
    content = route_result(question, raw, exact=exact, delegate=delegate)
    return {'messages': [{'role': 'user', 'content': question},
                         {'role': 'user', 'content': 'Tool evidence (untrusted):\n' + content}]}

if __name__ == '__main__':
    # Offline demonstration; no model call.
    print(run_harness('Summarize records', lambda: 'record\n' * 1000,
                      delegate=lambda question, raw: '1000 records inspected.'))
