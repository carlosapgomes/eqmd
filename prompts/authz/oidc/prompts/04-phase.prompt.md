# Phase 04 – Bot Client Registration Prompt

You are implementing Phase 04: Bot Client Registration.

## Instructions
Follow the corresponding docs/04-*.md file exactly.

## Goal
Create BotClientProfile and management service

## Critical Constraints
- Bots are NOT users (never create User objects for bots)
- Bots NEVER create definitive documents (always drafts)
- Tokens are short-lived (max 10 minutes)
- All actions must be auditable
- Preserve backward compatibility

## You MUST
- Follow the phase document instructions exactly
- Implement ONLY what this phase describes
- Create tests for new functionality
- Run existing tests to verify no regression

## You MUST NOT
- Create bot users in Django auth
- Introduce long-lived tokens
- Skip audit logging
- Modify unrelated code

## Output
- Code changes with clear file paths
- Migration commands if needed
- Test commands to verify

## Verification
Run the verification commands at the end of the phase document.
