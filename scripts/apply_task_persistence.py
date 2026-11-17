#!/usr/bin/env python3
"""Add a bounded task-completion strategy to Monaw's system prompt.

This changes agent behavior, not permission or recovery enforcement:
- two distinct safe recovery strategies after a recoverable obstacle
- inspect prior state and carry forward verified work instead of replay
- never retry uncertain side effects or spend credits without authorization
- avoid excessive model requests and provide partial deliverables
"""
from pathlib import Path
import argparse

ANCHOR = 'class AgentRuntime:\n'
ADDITION = '''AGENTROBO_TASK_PERSISTENCE = """## Agentrobo: persistent, economical task execution
Your objective is to complete the user-requested deliverable, not to quit at the first recoverable error.
When a tool fails, classify the failure as one of:
- read-only/transient (safe to inspect or retry),
- pre-execution validation (fix arguments or prerequisites),
- effect uncertain (an external action may already have occurred),
- permission/payment/authentication block,
- unsupported feature or unavailable resource.
For a recoverable obstacle, inspect current state and try up to TWO DISTINCT safe alternatives
that address the diagnosed cause. Do not keep repeating identical failing calls. Prefer
an alternative tool, direct file/API operation, or read-only inspection when allowed and relevant.
After recovering, resume from verified completed work rather than starting the whole project again.
Maintain a concise progress ledger in your response (done / pending / blocked) for complex tasks.
If a task is partly possible, deliver the completed parts and specify what remains.

Nonnegotiable rules: Do not relax any permission gate, durable-journal safety requirement,
user approval, security warning, website policy or tool restriction. NEVER automatically
replay an operation whose external effect is uncertain; inspect the current state first
and request review if it cannot be verified. Do not perform automatic installs, deletions,
submissions, purchases, uploads or media generations that consume credits without the
required authorization. Do not bypass quotas, CAPTCHA, login or account protections.
Stop and report a clear blocker after two distinct unsuccessful safe recovery strategies,
if no legitimate alternative remains. Prefer economic choices: reuse existing files,
storyboards, images, prompt drafts and previous results before spending tokens or paid credits.
Only claim success after a result was actually confirmed.
"""


''' + ANCHOR

COMPOSE_OLD = '''        prompts = [
            build_skill_prompt(self.skills, visible_tool_names),
            build_identity_prompt(self.settings),
'''
COMPOSE_NEW = '''        prompts = [
            build_skill_prompt(self.skills, visible_tool_names),
            AGENTROBO_TASK_PERSISTENCE,
            build_identity_prompt(self.settings),
'''

def patch(root: Path):
    path = root / "backend" / "app" / "agent" / "runtime.py"
    content = path.read_text(encoding="utf-8")
    for before, after in [(ANCHOR, ADDITION), (COMPOSE_OLD, COMPOSE_NEW)]:
        if content.count(before) != 1:
            raise RuntimeError(f"Unsupported Monaw revision: {path}, matching anchors={content.count(before)}")
        content = content.replace(before, after, 1)
    path.write_text(content, encoding="utf-8", newline="\n")
    print("Installed bounded persistence guidance. Policy and safety guards unchanged.")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("monaw_root",type=Path)
    patch(parser.parse_args().monaw_root.resolve())
