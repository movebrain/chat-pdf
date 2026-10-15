---
name: conventional-commits
description: Write and review git commit messages following Conventional Commits v1.0.0 (https://www.conventionalcommits.org/en/v1.0.0/). Use when writing, suggesting, or validating commit messages, or mapping commits to SemVer bumps and changelog entries.
---

# Conventional Commits v1.0.0

A lightweight convention on top of commit messages that makes history machine-readable and maps directly to SemVer.

## Structure

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## Rules (from the spec)

1. Commit MUST start with a **type** (noun: `feat`, `fix`, ...), optional **scope**, optional `!`, then required `: ` (colon + space), then a **description**.
2. `feat` = new feature → SemVer **MINOR**.
3. `fix` = bug fix → SemVer **PATCH**.
4. **Scope** is an optional noun in parentheses describing a codebase section: `fix(parser):`.
5. **Description** is a short summary right after the prefix.
6. **Body** is optional, begins one blank line after the description, free-form, may have multiple paragraphs.
7. **Footers** are optional, begin one blank line after the body. Format: `Token: value` or `Token #value`. Tokens use `-` instead of spaces (`Acked-by`, `Reviewed-by`); `BREAKING CHANGE` is the only exception.
8. **Breaking change** → SemVer **MAJOR** (any type). Signal it by either:
   - `!` immediately before the colon: `feat(api)!: drop v1 endpoints`
   - a `BREAKING CHANGE: <description>` footer (uppercase; `BREAKING-CHANGE` is a synonym)
   - If `!` is used, the footer MAY be omitted and the description describes the break.
9. Types other than `feat`/`fix` are allowed (spec has no fixed list). Recommended set (Angular convention): `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`.
10. Type and scope are case-insensitive, except `BREAKING CHANGE` which MUST be uppercase.

## Type cheat sheet

| Type       | Use for                                  | SemVer |
| ---------- | ---------------------------------------- | ------ |
| `feat`     | New feature                              | MINOR  |
| `fix`      | Bug fix                                  | PATCH  |
| `docs`     | Documentation only                       | -      |
| `style`    | Formatting, whitespace (no logic change) | -      |
| `refactor` | Restructure without feature/fix          | -      |
| `perf`     | Performance improvement                  | -      |
| `test`     | Add/update tests                         | -      |
| `build`    | Build system, dependencies               | -      |
| `ci`       | CI configuration                         | -      |
| `chore`    | Other maintenance                        | -      |
| any + `!`  | Breaking change                          | MAJOR  |

## Style

- Write commit message descriptions, bodies, and footer explanations in Korean. Keep Conventional Commits types, scopes, footer tokens, and technical identifiers in their standard form.
- Description: use a concise Korean action phrase with no trailing period (for example, `docs: 커밋 메시지 한국어 작성 규칙 추가`).
- Keep the first line short (~50-72 chars).
- Body explains _what_ and _why_, not _how_.
- One logical change per commit; if two types apply, split the commit.

## Examples

```
docs: CHANGELOG 오타 수정
```

```
feat(lang): 폴란드어 지원 추가
```

```
feat!: 상품 배송 시 고객 이메일 발송
```

```
feat(api)!: v1 엔드포인트 제거

BREAKING CHANGE: /v1/* 경로를 제거했으므로 /v2/* 경로로 전환해야 합니다.
```

```
fix: 요청 간 경합 방지

최신 요청의 응답만 반영해 이전 요청의 응답이 현재 상태를 덮어쓰지 않도록 합니다.

Reviewed-by: Z
Refs: #123
```

```
revert: 이전 변경 되돌리기

Refs: 676104e, a215868
```

## Quick check before committing

- [ ] Starts with a valid `type` (and `(scope)` if useful)?
- [ ] `: ` with a space after the prefix?
- [ ] Description, body, and footer explanations written in Korean?
- [ ] Description concise, no trailing period?
- [ ] Blank line separating description / body / footers?
- [ ] Breaking change marked with `!` and/or `BREAKING CHANGE:` footer?
