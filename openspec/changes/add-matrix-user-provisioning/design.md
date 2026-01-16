## Context
Django is the OIDC IdP for Synapse. Today, Synapse JIT-creates users from the OIDC subject, which produces non-memorable MXIDs and exposes internal identifiers. The deployment is private and small (<= 100 users), so admin-controlled provisioning is preferred.

## Goals / Non-Goals
- Goals: admin-chosen MXIDs, pre-provisioned Matrix accounts, stable UUID-based identity binding, and automatic MatrixUserBinding creation.
- Non-Goals: federation support, end-user self-service provisioning, large-scale bulk onboarding.

## Decisions
- Store matrix_localpart on UserProfile along with provisioning metadata.
- Use Synapse Admin API to create/update users with external_ids linking to the UserProfile UUID (OIDC sub).
- Keep OIDC sub derived from UserProfile UUID; do not use OIDC claims to generate MXIDs.
- Configure Synapse OIDC to disallow new-user creation and allow existing users only.

## Risks / Trade-offs
- Provisioning depends on Synapse admin access; failures must be surfaced to admins.
- Manual MXID selection adds admin workload but is acceptable for a small user base.

## Migration Plan
- Add nullable fields; no backfill required (greenfield).
- After deployment, update Synapse OIDC config to disable JIT and rely on pre-provisioned users.

## Open Questions
- Confirm the exact Synapse 1.99 config key to disable JIT user creation for OIDC.
