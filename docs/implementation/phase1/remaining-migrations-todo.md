# Remaining Migrations TODO

**Status**: Deferred to later phases
**Date**: November 2, 2025

---

## Phase 4+ Migrations (Auth & Security)

### Migration 017+: User Authentication
- **Tables**: `users`, `user_sessions`, `user_invites`
- **Purpose**: User management, JWT sessions, invite-only signup
- **Reference**: Section 4.7
- **Priority**: Phase 4
- **Dependencies**: None (bootstrap with initial admin via script)

### Migration 018+: Two-Factor Authentication
- **Table**: `two_factor_auth`
- **Purpose**: TOTP secrets and backup codes for 2FA
- **Reference**: Section 4.7
- **Priority**: Phase 4
- **Dependencies**: Migration 017 (FK to users table)

### Migration 019+: Email Service Configuration
- **Table**: `email_settings`
- **Purpose**: SMTP configuration for automated emails
- **Reference**: Section 4.7
- **Priority**: Phase 4
- **Dependencies**: None

---

## Feature-Specific Migrations (Needs Design)

### Docker Container Lifecycle Management
- **Table**: `docker_containers` (proposed)
- **Purpose**: Track container lifecycle per project
- **Status**: **NEEDS DESIGN**
- **Questions to Answer**:
  - What container metadata to track?
  - How to handle container cleanup?
  - Integration with Docker API?
- **Priority**: Medium (needed for code execution isolation)

### GitHub Integration
- **Table**: `github_credentials` (proposed)
- **Purpose**: Store encrypted GitHub OAuth tokens per user/project
- **Status**: **NEEDS DESIGN**
- **Questions to Answer**:
  - User-level or project-level credentials?
  - OAuth flow details?
  - Token refresh strategy?
- **Priority**: Medium (needed for GitHub specialist agent)

---

## Optional Tooling

### Migration Validation Script
- **File**: `backend/scripts/validate_migrations.py`
- **Purpose**: Verify migrations can be applied in order, all FK references valid
- **Priority**: Low (nice to have, not blocking)

---

## Summary

**Completed Migrations**: 001-016 (16 migrations) ✅
**Deferred to Phase 4**: Auth, 2FA, Email (3 migrations)
**Needs Design**: Docker, GitHub (2 migrations)
**Optional**: Validation script

**Action Items**:
1. ⏸️ **Hold on auth migrations** - Phase 4 only
2. 📋 **Design Docker/GitHub tables** - When implementing those features
3. ✅ **Continue with Phase 1** - All required migrations done

**Next**: Return to Item #4 (GateManager Service)
