#!/usr/bin/env bash
# PreToolUse hook: blocks Bash commands that would violate .ai/guardrails.md.
# Contract: reads hook JSON on stdin; exit 2 blocks the tool call and feeds stderr
# back to the agent; exit 0 allows. Keep patterns conservative — false blocks erode
# trust in the guard (agents must never be trained to bypass it — GR-012).

set -u

command_text="$(cat | { command -v jq >/dev/null 2>&1 && jq -r '.tool_input.command // empty' || cat; })"
[ -z "$command_text" ] && exit 0

block() {
  echo "BLOCKED by guardrail $1: $2 (see .ai/guardrails.md). Use the documented alternative instead of working around this guard." >&2
  exit 2
}

# GR-010: direct push to main/master (covers flags, "-u", and "HEAD:main" refspecs).
# Terminators include " so the guard still works when jq is absent and the raw hook
# JSON (…main") is grepped; "-" is NOT a terminator so feat/main-nav stays allowed.
echo "$command_text" | grep -Eq 'git +push\b.*( |:)(main|master)( |"|$)' \
  && block "GR-010" "direct push to main/master — open a PR from a branch"

# GR-011: force push (word-boundary safe: matches trailing -f/--force too, jq or not)
echo "$command_text" | grep -Eq 'git +push\b.* (--force|-f)( |"|$)' \
  && block "GR-011" "force push — use --force-with-lease on your own PR branch only, and only when needed"

# GR-012: bypassing hooks/CI
echo "$command_text" | grep -Eq -- '--no-verify|--no-gpg-sign|\[skip ci\]|\[ci skip\]' \
  && block "GR-012" "bypassing hooks or CI — fix the failing check instead"

# GR-031: destructive filesystem/database operations. Blocks recursive rm targeting any
# absolute/home path (/, /etc, ~, ~/x, $HOME...), quoted or not; workspace-relative
# (./x, bare names) is allowed. The leading [\'"]* also skips a JSON-escaped quote (\")
# so the guard still fires on the jq-absent raw-JSON path (LOG-0006).
echo "$command_text" | grep -Eq 'rm +-[a-zA-Z]*r[a-zA-Z]* +[\'\''"]*(/|~|\$HOME)' \
  && block "GR-031" "recursive delete of an absolute/home path — needs explicit human approval"
echo "$command_text" | grep -Eiq 'drop +(table|database|schema)' \
  && block "GR-031" "destructive database operation — needs explicit human approval"

# GR-032/GR-001: piping remote scripts into a shell (untrusted code exec / exfil vector).
# Also catches a privilege/env prefix after the pipe (| sudo sh, | env X=y bash).
echo "$command_text" | grep -Eq '(curl|wget)[^|;]*\|\s*(sudo\s+|env\s+[^|;]*)?(ba|z|da)?sh\b' \
  && block "GR-032" "piping a remote script into a shell — download, review, then run"

# git history rewrite on shared branches
echo "$command_text" | grep -Eq 'git +(rebase|reset +--hard) +[^ ]*origin/(main|master)|git +filter-(branch|repo)' \
  && block "GR-011" "history rewrite touching shared branches — needs explicit human approval"

exit 0
