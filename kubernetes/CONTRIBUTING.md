# Contributing to Flagsmith Interview Challenges

This guide explains how to create, validate, and maintain interview challenges for the Flagsmith challenge system.

## Requirements

Every challenge **MUST** consist of:

1. **Challenge Definition** (`{name}.yaml`)
   - Name, description, estimates, helm values, kubectl patches

2. **Reviewer Manual** (`{name}.md`)
   - Step-by-step solution guide for the interviewer
   - Educational learning points
   - Debugging techniques and prevention strategies

3. **Required YAML Fields**
   ```yaml
   name: "Challenge Title"
   description: "Candidate must [action] to fix [issue] causing [symptom]"
   estimates:
     Lv1: <integer>    # Bronze: 0-2 years K8s experience
     Lv2: <integer>    # Silver: 2-4 years K8s experience
     Lv3: <integer>    # Gold: 4+ years K8s experience
   helm_values: {}     # Helm chart configuration
   kubectl_patches: [] # Optional kubectl JSON patches
   ```

All fields are mandatory. The system will fail immediately if any required field is missing or if the corresponding `.md` manual doesn't exist.

## Creating a Challenge

### Step 1: Define the Challenge

Create a new YAML file in `challenges/` with your challenge definition.

**Requirements:**
- Filename must be kebab-case: `my-challenge.yaml`
- Must include all required fields
- `name` should be descriptive and clear
- `description` should follow the pattern: "Candidate must [action] to fix [issue] causing [symptom]"
- Time estimates should be realistic integers (not `∞` unless unsuitable for that level)

**Example:**
```yaml
name: "Database Connection Timeout"
description: "Candidate must identify and fix connection pool exhaustion causing timeout errors."
estimates:
  Lv1: 30
  Lv2: 15
  Lv3: 8

helm_values:
  api:
    replicaCount: 1
    resources:
      limits:
        cpu: "100m"
        memory: "256Mi"

kubectl_patches:
  - resource: "deployment"
    name: "flagsmith-api"
    namespace: "flagsmith"
    patch_type: "json"
    patch:
      - op: "add"
        path: "/spec/template/spec/containers/0/env/-"
        value:
          name: "DB_POOL_SIZE"
          value: "1"
```

### Step 2: Write the Reviewer Manual

Create a corresponding `.md` file with the same name: `my-challenge.md`

**Required sections:**

1. **Problem Description** - What's broken and why
2. **Step-by-Step Solution** - Each debugging step with commands and expected output
3. **Key Learning Points** - Educational objectives (5-7 bullet points)
4. **Prevention** - How to avoid this in production
5. **Additional Debugging Commands** - Extra tools and techniques (optional but recommended)

**Structure Example:**
```markdown
# Challenge: Database Connection Timeout - Solution

## Problem Description
[Explain what's broken and the root cause]

## Step-by-Step Solution

### Step 1: Identify the Problem
[Commands and expected symptoms]

### Step 2: Investigate the Configuration
[Debugging commands with output]

[Continue with numbered steps...]

## Key Learning Points

1. [Educational point 1]
2. [Educational point 2]
[etc...]

## Prevention

- [Prevention strategy 1]
- [Prevention strategy 2]

## Additional Debugging Commands

[Optional reference commands]
```

### Step 3: Estimate Time Accurately

Time estimates guide interviewer expectations and candidate assessment.

**Guidelines:**
- **Lv1 (Bronze)**: 0-2 years K8s experience, may need to Google commands
- **Lv2 (Silver)**: 2-4 years, solid troubleshooting, familiar with tools
- **Lv3 (Gold)**: 4+ years, senior/staff level, can diagnose quickly

**Mark as Unsuitable:**
Use `"∞"` (infinity symbol) for Lv1 if the challenge is unsuitable for beginners:
```yaml
estimates:
  Lv1: "∞"    # Senior-level challenge, unsuitable for beginners
  Lv2: 20
  Lv3: 9
```

**Estimation Guidelines:**
- Simple challenge (e.g., single configuration error): 15-25 minutes for Lv1
- Moderate challenge (multi-step debugging): 30-45 minutes for Lv1
- Complex challenge (multiple concurrent issues): 45-60 minutes for Lv1, or mark as `"∞"`
- Senior-level candidates (Lv3): Typically complete challenges in 5-15 minutes

## Validation Checklist

Before submitting a challenge:

- [ ] Both files exist: `challenges/my-challenge.yaml` and `challenges/my-challenge.md`
- [ ] YAML contains all required fields: `name`, `description`, `estimates`, `helm_values`, `kubectl_patches`
- [ ] Time estimates are positive integers or `"∞"` where appropriate
- [ ] Helm values deploy successfully
- [ ] kubectl patches use valid JSON syntax
- [ ] Challenge deployment is actually broken (health check fails)
- [ ] Solution manual is technically accurate and matches the challenge
- [ ] Time estimates are realistic (verified through manual walkthrough)

## Testing Your Challenge

Run the system and test your challenge:

```bash
make run
```

Then:
1. Select your challenge from the menu
2. Verify it deploys successfully
3. Confirm the challenge is actually broken (health check fails)
4. Work through the solution steps in your manual
5. Verify time estimates are realistic for each skill level
6. Confirm the health endpoint returns 200 after your fixes

## Code Quality

All Python code must pass linting and type checking:

```bash
ruff check cli/
ty check cli/
```

Challenge files are discovered automatically. No code changes are needed when adding new challenges.

## Challenge Consistency

### Naming Conventions
- Use kebab-case for filenames: `network-issue.yaml`, not `NetworkIssue.yaml`
- Use Title Case for `name` field in YAML
- Keep names concise but descriptive

### Description Format
Follow this pattern:
> "Candidate must **[action]** to fix **[issue]** causing **[symptom]**."

**Good examples:**
- "Candidate must identify and fix a typo in the database service name causing connection failures."
- "Candidate must remove a CPU-intensive sidecar container causing API performance issues."
- "Candidate must adjust memory limits that are set too low causing OOMKilled pods."

**Bad examples:**
- "There's a broken pod" (vague)
- "Fix this" (unclear)
- "Challenge about networking" (not action-oriented)

### Patch Format
Use JSON patches with proper escaping for special characters:
```yaml
# Correct: Use ~1 for forward slash in JSON pointer
path: "/spec/selector/app.kubernetes.io~1name"

# Wrong: Don't use literal forward slash
path: "/spec/selector/app.kubernetes.io/name"
```

## Educational Standards

### What Makes a Good Challenge?

**Characteristics of effective challenges:**
- Tests real-world debugging skills and systematic troubleshooting
- Clear root cause that candidates can identify through investigation
- Teaches production-relevant concepts and best practices
- Multiple valid approaches to reach the solution
- Objective success criteria (health endpoint returns HTTP 200)

**What to avoid:**
- Ambiguous symptoms that could indicate multiple unrelated issues
- Contrived scenarios that wouldn't occur in real environments
- Challenges requiring deep Flagsmith application knowledge (focus on Kubernetes)
- Overly trivial fixes (unless teaching a specific lesson)
- Subjective or unclear completion criteria

### Learning Progression

Design challenges across a spectrum of difficulty:

1. **Beginner-friendly (Lv1)**: Single, well-defined issue with clear symptoms
2. **Intermediate (Lv2)**: Multiple related issues requiring systematic debugging
3. **Advanced (Lv3)**: Complex scenarios with concurrent problems, demanding deep expertise

Each difficulty level should introduce new concepts or techniques, not just expect faster execution.

## Maintenance

### When to Update Challenges

Update challenges when:
- Time estimates prove inaccurate based on candidate performance
- Debugging techniques or tools change
- New Kubernetes best practices emerge
- Technical inaccuracies are discovered in the solution

### When to Mark as Unsuitable

Use `"∞"` for specific levels when:
- New tooling makes the challenge trivial for that skill level
- The scenario no longer reflects realistic production issues
- The educational value no longer justifies the time investment

## Questions?

Review existing challenges in the `challenges/` directory for working examples. The system enforces these requirements to maintain consistency and educational quality across all challenges.