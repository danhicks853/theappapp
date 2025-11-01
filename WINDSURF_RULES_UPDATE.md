# .windsurf Rules Update Required

**File**: `.windsurf/rules/devguidelines.md`

---

## Current Content (Has Typo)

```markdown
---
trigger: always_on
---

Before completing any tasks, always refer to docs\development_guradrails.md and follow ALL instructions without exception.
```

---

## Required Update

```markdown
---
trigger: always_on
---

Before completing any tasks, always refer to the following documents:

1. **docs/TASK_EXECUTION_GUIDE.md** - Complete step-by-step workflow for executing "start the next task"
2. **docs/testing/development_guardrails.md** - Quality standards and mandatory requirements
3. **docs/testing/testing_philosophy.md** - Testing approach and coverage requirements

Follow ALL instructions in these documents without exception.

When you receive the command "start the next task", follow the exact 10-step workflow in TASK_EXECUTION_GUIDE.md.
```

---

## Why This Update Is Needed

1. **Fixes typo**: "guradrails" → "guardrails"
2. **Adds workflow reference**: Points to new TASK_EXECUTION_GUIDE.md
3. **Clarifies process**: Explicitly mentions "start the next task" command
4. **Complete references**: All 3 mandatory documents listed

---

**Action Required**: Manually update `.windsurf/rules/devguidelines.md` with the content above.
