# Exercise 2: Configure Claude Code for a Team Development Workflow

**Source:** CCA-F Exam Guide, Preparation Exercise 2
**Domains reinforced:** Domain 3 (Claude Code Config & Workflows), Domain 2 (Tool Design & MCP)

This exercise is CONFIG-ONLY. There is no Python code. The whole folder is
a self-contained pedagogical example of a project's Claude Code setup.

## Layout

```
exercise-2-team-workflow/
├── CLAUDE.md                          # project-level standards (Step 6)
├── .claude/
│   ├── rules/
│   │   ├── api-conventions.md         # path-scoped: src/api/**  (Step 7)
│   │   └── test-conventions.md        # path-scoped: **/*.test.* (Step 7)
│   ├── skills/
│   │   └── summarize-diff/
│   │       └── SKILL.md               # context: fork, allowed-tools (Step 8)
│   └── commands/
│       └── new-endpoint.md            # example custom slash command
├── .mcp.json                          # project-scoped MCP servers (Step 9)
├── src/                               # sample area referenced by rules
│   ├── api/README.md
│   └── payments.test.md
└── PLAN_MODE_vs_DIRECT.md             # Step 10 comparison writeup
```

## The 5 exam steps mapped to files

| Step | Concept | File(s) |
|------|---------|---------|
| 6 | Project-level CLAUDE.md consistency | `CLAUDE.md` |
| 7 | Path-scoped rules via YAML `paths:` globs | `.claude/rules/*.md` |
| 8 | Project-scoped skill with `context: fork` + `allowed-tools` | `.claude/skills/summarize-diff/SKILL.md` |
| 9 | `.mcp.json` with env-var expansion + personal `~/.claude.json` override | `.mcp.json` |
| 10 | Plan mode vs direct execution comparison | `PLAN_MODE_vs_DIRECT.md` |

## Verification steps (as described in the exam guide)

Steps 7, 8, 9, 10 all say "verify" something. Concrete verification recipes
are inline in each file's `## Verify` section.

## Mnemonic — HIERARCHY

- **H**ierarchy: user → project → subdirectory CLAUDE.md
- **I**mport with `@path/to/file` from CLAUDE.md
- **E**nv-var expansion in `.mcp.json` (`${VAR}`)
- **R**ules: path-scoped via YAML frontmatter globs
- **A**llowed-tools: restrict skill capabilities in SKILL.md
- **R**un skills in `context: fork` for isolation
- **C**ommands live in `.claude/commands/*.md`
- **H**ybrid MCP: project `.mcp.json` + personal `~/.claude.json` coexist
- **Y**ield to plan mode when >1 valid approach exists
