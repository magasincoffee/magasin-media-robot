# MAGASIN Business OS — Historical Bootstrap Blueprint

> **MOVED / NON-CANONICAL — 2026-09-18**  
> MAGASIN Business OS execution now lives in `magasincoffee/magasincoffee.github.io`.  
> Canonical files: `01_DOCS/MAGASIN/00_BUSINESS_OS_BLUEPRINT.md`, `00_CURRENT_STATE.md`, `00_PROJECT_STATE.json`, and `00_TASK_QUEUE.md`.  
> This copy remains only as historical bootstrap context. Do not continue Business OS implementation from this repository.

Last updated: 2026-09-18

## Purpose

This document is the canonical bootstrap specification for the future private repository `magasin-business-os`.

Until that repository exists, this file is intentionally stored in `magasin-media-robot` so a future ChatGPT session can recover the agreed architecture, operating model, delivery scope, safety rules, and next actions without relying on chat history.

When `magasin-business-os` is created, copy this document into that repository under `00_PROJECT/ARCHITECTURE.md` or `00_PROJECT/PROJECT_BLUEPRINT.md`, then treat the private Business OS repository as the new source of truth.

Do not place private operating data, credentials, customer data, employee data, financial records, tokens, cookies, browser profiles, or generated private artifacts in this public repository.

---

## Project objective

Build a practical management operating system for MAGASIN COFFEE in **21 calendar days**, with a first usable Owner Control Tower by approximately **day 7**.

The system is not intended to become a large ERP in V1. The first release must help the owner answer the core operating questions quickly:

1. How much did MAGASIN sell today?
2. Which branch is underperforming?
3. What inventory is low or abnormal?
4. Which products are driving revenue?
5. Who is working and where are staffing gaps?
6. Which SOP/tasks are incomplete?
7. What requires owner attention now?
8. What can the system safely automate?
9. What decisions require explicit approval?
10. What changed versus the recent operating baseline?

---

## Development method — Five-Step Algorithm

All requirements and implementation decisions must pass through the following sequence before automation is added.

### Step 1 — Question every requirement

Every feature must have a named business reason and owner.

Ask:

- What decision or operating outcome does this feature improve?
- Who uses it?
- What happens if it does not exist?
- Is the requirement based on actual operating need or habit?
- Is the requirement duplicated elsewhere?

A requirement that cannot justify its existence should not enter V1.

### Step 2 — Delete unnecessary parts or processes

Before digitizing an existing process, attempt to remove steps.

Default objective:

> each business fact should be entered once and reused everywhere.

Avoid reproducing inefficient spreadsheet/manual workflows inside software.

Examples:

- remove duplicate data entry;
- remove unnecessary approval layers;
- remove reports no one acts on;
- remove duplicated spreadsheets;
- remove manual summary work when raw data already exists.

### Step 3 — Simplify and optimize what remains

Only after deletion should a process be simplified.

V1 is centered on four core domains:

1. Sales
2. Inventory
3. People
4. Tasks / SOP

Other functions should initially be projections, reports, workflows, or derived views over these cores rather than independent large modules.

### Step 4 — Accelerate cycle time

Development must use vertical slices and short micro-tasks.

The project should not wait for a large phase to finish before being usable.

Target milestones:

- day 3: data visible;
- day 7: owner can use the Control Tower;
- day 14: business alerts and daily brief usable;
- day 21: V1 production-ready.

### Step 5 — Automate only after the process is correct

Automation is last.

Do not automate a process merely because it exists today.

First:

1. verify requirement;
2. delete unnecessary steps;
3. simplify;
4. validate the process in real use;
5. then automate low-risk execution.

---

## V1 architecture

```text
MAGASIN BUSINESS OS
│
├── Web Control Center
│   └── Next.js + TypeScript
│
├── Business Core
│   └── Supabase / PostgreSQL
│
├── Core Domains
│   ├── Sales
│   ├── Inventory
│   ├── People
│   └── Tasks / SOP
│
├── Business Robot
│   ├── Daily Brief
│   ├── Alerts
│   ├── Anomaly Detection
│   ├── Recommendations
│   └── Approval Queue
│
├── Connectors
│   ├── Google Sheets
│   ├── Sapo
│   ├── Media Robot
│   └── Local Windows Agent
│
└── Autonomy Layer
    ├── GitHub task queue
    ├── Windows self-hosted runner
    └── Supervisor Robot
```

---

## Web Control Center

The owner-facing interface should prioritize business decisions rather than technical details.

Primary V1 screens:

- Today / Owner Dashboard
- Sales
- Inventory
- People / Shift
- Tasks / SOP
- Alerts
- Approval Queue
- Daily Brief
- System / Sync status

The dashboard must optimize for fast comprehension, not visual complexity.

---

## Business Core

Use PostgreSQL through Supabase as the primary system of record for the Business OS.

V1 should favor a small normalized core and explicit event/movement records over duplicated calculated balances.

Core concepts should include at minimum:

- branch;
- product;
- sale / sale line;
- inventory item;
- inventory movement;
- employee;
- shift;
- SOP template;
- checklist execution;
- task;
- alert;
- approval request;
- audit event;
- connector sync state.

Business rules and workflow definitions should be separated from durable transaction data wherever practical.

---

## Core domain 1 — Sales

V1 responsibilities:

- branch revenue;
- order count;
- product sales;
- average order value where data supports it;
- time/shift aggregation;
- recent-baseline comparisons;
- branch/product anomaly flags.

V1 is management reporting, not full accounting.

---

## Core domain 2 — Inventory

Use movement-ledger logic.

```text
Opening balance
+ receipts
+ transfers in
- transfers out
- usage / sales-linked depletion
- adjustments
= current stock
```

V1 responsibilities:

- receipts;
- issues/usage;
- transfers;
- adjustments;
- current stock;
- minimum stock;
- stock alerts;
- basic days-of-stock estimate where inputs are reliable.

Avoid storing multiple competing “current stock” truths.

---

## Core domain 3 — People

V1 responsibilities:

- employee directory;
- branch assignment;
- shift registration;
- shift schedule;
- basic attendance/status where available;
- staffing-gap alerts;
- simple operating roles.

Payroll and advanced HR are outside V1.

---

## Core domain 4 — Tasks / SOP

Existing MAGASIN operating SOPs should become executable workflow/checklist templates rather than static documents.

Examples:

- opening shift;
- preparation;
- order flow;
- brewing/production procedures;
- cleaning;
- closing shift;
- weekly inspection.

Lifecycle:

```text
SOP template
→ scheduled/triggered checklist
→ responsible person
→ completion evidence/status
→ exception
→ corrective task
→ close
```

---

## Business Robot

The Business Robot is an operating-assistance layer over verified business data.

V1 responsibilities:

### Daily Brief

Generate a concise management summary containing:

- total revenue;
- branch changes;
- significant inventory alerts;
- staffing gaps;
- overdue SOP/tasks;
- material anomalies;
- decisions requiring owner approval.

### Alerts

Alerts should be rule-driven first.

Examples:

- branch revenue falls materially versus recent baseline;
- inventory below minimum;
- repeated stock adjustment;
- unfilled shift;
- overdue checklist;
- abnormal cost/movement if reliable inputs exist.

### Recommendations

Recommendations must cite the evidence used.

The robot may propose actions such as:

- inspect a branch;
- transfer stock;
- replenish inventory;
- fill a shift;
- assign a corrective task;
- create a marketing/content request.

### Approval Queue

Potentially consequential actions should be staged for approval rather than executed automatically.

---

## Media Robot integration

`magasin-media-robot` remains a separate system.

Business OS may create structured media requests, for example:

```text
business signal
→ content opportunity
→ approved media task
→ magasin-media-robot
→ produced artifact/status
```

The Business OS should not absorb video/voice/render implementation details.

---

## Google Sheets strategy

Do not block V1 on a full spreadsheet migration.

Initial flow:

```text
Existing Google Sheets
        ↓
   import / sync
        ↓
PostgreSQL / Supabase
        ↓
Business OS
```

Sheets may remain transitional inputs while PostgreSQL becomes the management system of record.

Every connector must record:

- source;
- sync timestamp;
- result;
- rows/events handled;
- errors;
- idempotency/reference key where relevant.

---

## Business rules must remain changeable

Real operating procedures will change after field use.

The architecture must support this intentionally.

Separate:

```text
Core transaction/data model
        from
Business rule / workflow policy
```

When the owner changes a process:

```text
request change
→ impact analysis
→ version rule/workflow
→ migration if required
→ unit test
→ regression test
→ E2E test
→ deploy
→ observe
```

SOP/workflow versions should be explicit, for example:

```text
SOP v1
SOP v2
SOP v3
```

Historical executions must retain the version that governed them.

Large changes to financial logic, persistent data structure, or historical transaction interpretation require a migration plan and stronger review.

---

## Autonomy operating model

The owner does not want to remain at the computer continuously asking ChatGPT to continue.

The project therefore requires an autonomy layer.

### Responsibilities

ChatGPT / implementation agent:

- architecture;
- task decomposition;
- coding;
- tests;
- bug fixes;
- regression;
- E2E;
- documentation;
- commits;
- pull requests;
- progress/state maintenance.

Owner:

- installation where local/admin action is required;
- credentials entered directly into trusted interfaces;
- business-policy decisions;
- approval for consequential production actions;
- physical/local actions when automation cannot safely perform them.

---

## Supervisor Robot

A local Supervisor Robot should be built early in the project.

Purpose:

- observe the active ChatGPT workflow;
- detect normal completion/interruption states;
- continue the next approved project task;
- recover from ordinary UI/network interruptions where safe;
- stop when explicit human action is required.

Preferred interaction order:

1. DOM/accessibility/UI automation;
2. stable application controls;
3. image/screen interpretation only where necessary;
4. OCR only as a last resort.

Do not rely on brittle pixel coordinates when semantic UI targets exist.

### Supervisor may handle

- continue/next prompts;
- retry after ordinary transient UI/network failure;
- monitor GitHub task state;
- wait for Actions jobs;
- reopen the approved workflow;
- submit the canonical “continue current task” instruction when project state allows it.

### Supervisor must stop for

- login requiring user credentials;
- CAPTCHA;
- MFA/OTP;
- financial transaction;
- destructive production deletion;
- administrator permission escalation;
- security-sensitive configuration;
- ambiguous business decision;
- any project state marked `WAIT_USER`.

The Supervisor must never request or scrape passwords, cookies, session tokens, browser profiles, or authentication dumps.

---

## Local execution control

Current model:

```text
Shell 1 — GitHub self-hosted runner
C:\actions-runner
.\run.cmd

Shell 2 — Supervisor Robot
local process / launcher
```

Kill-switch semantics:

- close Supervisor → no automated ChatGPT/UI continuation;
- close GitHub runner → no new GitHub Actions jobs can execute on the local PC through that runner;
- close both → local project automation stops.

A previously spawned independent process may continue until it exits, so workflows should avoid detached uncontrolled processes.

---

## Automation risk levels

### GREEN — automatic

Examples:

- read repository;
- create code on feature branch;
- unit tests;
- lint/build;
- documentation;
- non-destructive local diagnostics;
- ordinary retry of a non-side-effect operation;
- continue to next approved micro-task.

### YELLOW — prepare, then require approval when production-impacting

Examples:

- production schema migration;
- enabling a new connector;
- changing a business workflow currently in use;
- data backfill;
- modifying permissions;
- production deployment with material behavior change.

### RED — explicit human action always

Examples:

- payment;
- bank action;
- entering credentials;
- MFA;
- destructive production deletion;
- irreversible data purge;
- security/admin escalation.

---

## Micro-task execution rule

No implementation task should normally exceed approximately **20 minutes of active work**.

If estimated larger, split it.

Bad:

```text
Build inventory system
```

Good:

```text
INV-001 inventory schema
INV-002 movement model
INV-003 stock balance query
INV-004 minimum-stock rule
INV-005 stock API
INV-006 stock dashboard
INV-007 stock alert
INV-008 inventory E2E
```

Each task should move through:

```text
Estimate
→ Implement
→ Unit test
→ Fix
→ Regression
→ Integration test
→ E2E when applicable
→ Update project state/docs
→ Commit
→ Next task
```

---

## Definition of Done

A task is not DONE merely because code exists.

Required gate:

```text
implementation complete
+
relevant tests pass
+
known failure paths handled/documented
+
regression pass
+
E2E pass where applicable
+
project state updated
+
coherent commit created
```

For every reproducible defect:

```text
FAIL
→ BUG_LOG
→ root cause
→ fix
→ regression test
→ PASS
```

---

## Project state files for the private Business OS repository

The future private repo should contain:

```text
00_PROJECT/
├── ARCHITECTURE.md
├── CURRENT_STATUS.md
├── NEXT_STEP.md
├── TASK_QUEUE.md
├── DECISIONS.md
├── BUG_LOG.md
├── TEST_LOG.md
├── CHANGELOG.md
└── PROJECT_STATE.json
```

Minimum `PROJECT_STATE.json` concept:

```json
{
  "project": "magasin-business-os",
  "phase": "P1_DATA_FOUNDATION",
  "task": "TASK-001",
  "status": "RUNNING",
  "autonomy": "AUTO_CONTINUE",
  "blocked": false,
  "requires_user": false,
  "next_task": "TASK-002"
}
```

Allowed high-level states:

- `READY`
- `RUNNING`
- `TESTING`
- `FIXING`
- `WAIT_CI`
- `WAIT_USER`
- `BLOCKED`
- `DONE`

Supervisor must continue only when the state explicitly permits autonomous continuation.

---

## Continuation contract for future ChatGPT sessions

If chat context is lost, a new session should:

1. read this blueprint;
2. read `CURRENT_STATUS.md`;
3. read `NEXT_STEP.md`;
4. read `PROJECT_STATE.json`;
5. read the current task and relevant decisions/bugs/tests;
6. inspect the repository state and current open PR/CI;
7. continue from repository evidence rather than memory.

Repository state overrides stale chat recollection.

Once the private `magasin-business-os` repository exists, that repository becomes authoritative for Business OS work.

---

## V1 locked scope

Included:

- Sales
- Inventory
- People
- Shift
- SOP / Checklist
- Task management
- Owner Dashboard
- Alerts
- Daily Brief
- Business Robot
- Approval Queue
- Google Sheets import/sync
- Media Robot connector
- audit log
- backup/recovery basics
- basic roles/access
- Supervisor Robot
- GitHub task/autonomy state

Excluded from V1:

- full accounting ERP;
- complete payroll;
- native mobile application;
- advanced CRM;
- complete loyalty platform;
- complex AI forecasting;
- camera AI;
- full FoodApp automation;
- advanced recruitment system;
- excessive role granularity;
- non-essential UI polish.

Scope additions require an explicit tradeoff against the 21-day schedule.

---

## 21-day delivery plan

### Days 1–3 — Foundation + autonomy

- create private Business OS repository;
- canonical project/state files;
- Supervisor Robot foundation;
- Supabase/PostgreSQL project;
- auth/basic roles;
- branch/store/product foundation;
- CI;
- first E2E skeleton.

Exit: system can run continuously through micro-tasks and persist project state.

### Days 4–7 — Owner Control Tower

- sales ingestion;
- inventory foundation;
- Sheets sync/import;
- owner dashboard;
- initial alerts.

Exit: owner can use the system for daily visibility.

### Days 8–10 — People / Shift

- employees;
- shift registration/schedule;
- staffing gap detection;
- basic E2E.

### Days 11–13 — SOP / Task Engine

- SOP templates;
- checklist execution;
- task creation/assignment;
- overdue/exception handling.

### Days 14–16 — Business Rules / Daily Brief

- alert rules;
- baseline comparisons;
- daily brief;
- management exceptions.

### Days 17–18 — Business Robot / Approvals

- recommendations;
- evidence-backed action proposals;
- approval queue;
- safe action dispatch framework.

### Day 19 — Media Robot connector

- structured task contract;
- approved handoff to `magasin-media-robot`;
- status/result callback model.

### Day 20 — Full E2E / recovery

- representative end-to-end operating flows;
- connector failure;
- network interruption;
- resume/checkpoint behavior;
- regression suite.

### Day 21 — Production hardening / V1 release

- backup;
- permissions review;
- audit checks;
- performance sanity;
- production release;
- rollback plan;
- V1 acceptance report.

---

## V1 acceptance

Business OS V1 is accepted only if representative owner workflows work end to end.

At minimum:

1. sales data reaches dashboard;
2. inventory movement produces reliable stock state;
3. low-stock alert is created;
4. employee/shift workflow can expose a staffing gap;
5. SOP/checklist can create and close a corrective task;
6. Daily Brief summarizes current operating exceptions;
7. Business Robot recommendation includes traceable evidence;
8. consequential action can be held for owner approval;
9. system resumes after a controlled interruption;
10. audit/logging records material actions;
11. E2E and regression suites pass;
12. no credentials/private runtime state exist in Git.

---

## Current immediate next action

The private repository `magasincoffee/magasin-business-os` does not yet exist.

Owner action required:

1. create repository `magasin-business-os`;
2. set visibility to **Private**;
3. initialize with README.

After creation:

- migrate this blueprint into that repository;
- create canonical state files;
- start TASK-001: Project Bootstrap + Autonomy Supervisor;
- execute continuously using the micro-task/test/fix/E2E loop.

