---
name: create-pull-request
description: "Create GitHub pull requests with a concise Korean title and a Korean bullet-based body explaining each change and its background, intent, or purpose. Use when asked to create or open a pull request."
---

# Create Pull Request

## Goal

Create PR title and body in a consistent Korean format.
Keep title concise and descriptive, and keep body easy to scan with bullets while preserving enough context in each quoted explanation.

## Required PR Content Format

### Title Format

- Write in Korean.
- Keep one line.
- Make concise and descriptive.
- Reflect the major changes in the PR.

### Body Format

- Write in Korean.
- Use bullets only.
- Use this exact structure:

```markdown
- {핵심변경사항A}
  > {배경/의도/목적을 3-5문장으로 설명}

- {핵심변경사항B}
  > {배경/의도/목적을 3-5문장으로 설명}
```

- Write 2-6 top-level bullets.
- Treat top-level bullet as what was done.
- Write the background, intent, or purpose on the next line starting with exactly two spaces followed by `>`.
- Make the quoted background/intent/purpose content 3-5 sentences long so it gives enough explanation and context.
- Separate each bullet block with a blank line.
- Keep the top-level bullet line short and concrete; keep the quoted explanation specific and informative.

## Workflow

1. Collect PR context from git diff and commit history.
2. Draft the Korean title from the major changes.
3. Fill `assets/pr-content-format-ko.md` with concrete bullets.
4. Open PR with `gh pr create --title --body-file`.

Use these commands when needed:

```bash
BASE_BRANCH=$(gh repo view --json defaultBranchRef -q '.defaultBranchRef.name')
CURRENT_BRANCH=$(git branch --show-current)
git log --oneline "origin/$BASE_BRANCH..$CURRENT_BRANCH"
git diff --stat "origin/$BASE_BRANCH...$CURRENT_BRANCH"
```

```bash
GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 \
gh pr create \
  --base "$BASE_BRANCH" \
  --head "$CURRENT_BRANCH" \
  --title "$PR_TITLE" \
  --body-file "$PR_BODY_FILE"
```

## Quality Checks

- Confirm title is one-line, concise, and descriptive.
- Confirm body is fully Korean and bullet-based.
- Confirm each top-level bullet is followed by one background/intent/purpose line that starts with exactly two spaces and `>`.
- Confirm each quoted background/intent/purpose line contains 3-5 sentences.
- Confirm bullet blocks are separated by blank lines.
- Confirm quoted lines explain impact, intent, or value, not only implementation details.
