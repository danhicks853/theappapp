# Decision 84: User Authentication with 2FA

## Status
✅ **RESOLVED**  
**Date**: Nov 1, 2025  
**Priority**: P1 - BLOCKING

---

## Context

TheAppApp requires a secure user authentication system to support multi-user access, project ownership, and sensitive operations (API key management, GitHub integration, cost tracking). The system must:

- Secure user credentials and sessions
- Support two-factor authentication (2FA) for enhanced security
- Enable invite-only access control
- Prevent brute force attacks and account takeover
- Work seamlessly with frontend SPA architecture
- Scale to support concurrent sessions from multiple devices

Without proper authentication, the application cannot support multi-user features or protect sensitive data.

---

## Decision

### **1. Authentication Strategy: JWT with Session Tracking (Hybrid)**

**Implementation**:
- **JWT Tokens**: Access token (15min expiry), Refresh token (7 days expiry)
- **Session Tracking**: Store session records in database with refresh token hash
- **Signing Algorithm**: HS256 with secure secret key (min 256 bits)
- **Token Claims**: user_id, session_id, email, issued_at, expires_at
- **Storage**: Access token in memory (React state), refresh token in httpOnly cookie

**Rationale**:
- JWT provides stateless scalability for API requests
- Session tracking enables token revocation for logout/security events
- Hybrid approach combines best of both: performance + security control
- httpOnly cookies protect refresh tokens from XSS attacks
- Short-lived access tokens minimize damage if leaked

**Token Flow**:
```
1. User logs in → Verify credentials → Issue access + refresh tokens
2. Frontend stores access token in memory, refresh token in httpOnly cookie
3. API requests include access token in Authorization header
4. Access token expires after 15min
5. Frontend detects expiry → Calls refresh endpoint with cookie
6. Backend validates refresh token + session → Issues new access token
7. Repeat until refresh token expires (7 days) or session revoked
```

---

### **2. Password Policy: Standard Enterprise**

**Requirements**:
- Minimum 12 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
- No common passwords (check against top 10k leaked passwords)
- Cannot match email address

**Storage**:
- Hash passwords with bcrypt
- Cost factor: 12 rounds (2^12 iterations)
- Salt automatically generated per password by bcrypt

**Rationale**:
- Industry-standard policy familiar to enterprise users
- Good balance of security and usability
- Bcrypt is proven secure against brute force attacks
- 12 rounds provides strong security without excessive CPU load

---

### **3. Two-Factor Authentication: TOTP with Email Fallback**

**Primary Method: TOTP (Time-based One-Time Password)**
- Standard: RFC 6238
- Library: `pyotp` (Python), compatible with Google Authenticator, Authy, 1Password, etc.
- Code Length: 6 digits
- Time Window: 30 seconds
- Tolerance: ±1 window (allows 30s clock drift)

**Fallback Method: Email OTP**
- When TOTP unavailable (lost device, no authenticator app)
- 6-digit code sent to verified email
- Valid for 10 minutes
- Rate limited: Max 3 emails per hour per account

**Backup Codes**:
- Generate 10 single-use backup codes during 2FA setup
- Stored as bcrypt hashes (like passwords)
- Display once, user must save them
- Can be regenerated (invalidates previous codes)

**2FA Setup Flow**:
```
1. User enables 2FA in settings
2. Backend generates TOTP secret → Encrypt with Fernet → Store in DB
3. Backend generates QR code data URI from secret
4. Frontend displays QR code + manual entry option
5. User scans with authenticator app
6. User enters test code to verify setup
7. Backend verifies code → Marks 2FA as enabled → Displays backup codes
8. User saves backup codes
```

**Login Flow with 2FA**:
```
1. User enters email + password
2. Backend verifies credentials → Returns temporary token + 2FA status
3. If 2FA enabled → Frontend redirects to 2FA verification page
4. User enters TOTP code (or selects email fallback)
5. Backend verifies code → Issues full auth tokens
6. Frontend stores tokens → Redirect to dashboard
```

**Rationale**:
- TOTP is secure, standard, works offline, no ongoing costs
- Email fallback provides recovery option without SMS security risks
- Backup codes protect against device loss
- Aligns with industry best practices (GitHub, Google, AWS use TOTP)

---

### **4. Token Expiry: Short-Lived for Security**

**Access Token**: 15 minutes
- Minimizes damage if token leaked
- Acceptable refresh frequency for SPAs

**Refresh Token**: 7 days  
- Balance of security and UX convenience
- Long enough to avoid frequent re-login
- Short enough to limit compromise window

**Automatic Refresh**:
- Frontend checks token expiry every 60 seconds
- Refreshes when <2 minutes remaining
- Transparent to user (no interruption)
- If refresh fails → Logout and redirect to login

**Rationale**:
- Short access tokens limit exposure window
- 7-day refresh balances security and UX
- Automatic refresh provides seamless experience
- Standard approach used by Auth0, Okta, Google

---

### **5. Session Management: Limited Concurrent Sessions**

**Limit**: Maximum 2 concurrent active sessions per user
- Expected use case: One mobile device + one desktop
- Aligns with typical user behavior

**Session Tracking**:
- Store in `user_sessions` table with:
  - session_id (unique identifier)
  - user_id (foreign key)
  - refresh_token_hash (bcrypt hash)
  - expires_at (7 days from creation)
  - ip_address (for audit/security)
  - user_agent (device identification)
  - created_at (session start time)
  - last_activity_at (updated on token refresh)

**Enforcement**:
- When user logs in with 2 active sessions → Revoke oldest session
- User can view active sessions in settings
- User can manually revoke individual sessions
- All sessions revoked on password change or 2FA disable

**Session Cleanup**:
- Cron job runs daily to delete expired sessions (expires_at < now)
- Prevents database bloat from abandoned sessions

**Rationale**:
- 2 sessions covers typical usage (phone + desktop)
- Provides security against stolen credentials (attacker triggers revocation)
- User control over sessions increases security awareness
- Balance between convenience and security

---

### **6. User Registration: Invite-Only System**

**Flow**:
```
1. Admin invites user via Settings UI
2. System generates secure invite token (UUID, 48 hours expiry)
3. System sends invite email with signup link (/register?token=xxx)
4. User clicks link → Validates token → Shows registration form
5. User sets password → Creates account → Email auto-verified (since invited)
6. Invite token consumed (single-use)
```

**Invite Management**:
- **Database Table**: `user_invites`
  - id, email, invite_token, invited_by (FK users), expires_at, created_at, consumed_at
- **Frontend UI**: Settings → User Management → Invite User
- **Invite List**: Show pending invites, allow cancellation
- **Tracking**: Log who invited whom for audit

**Email Not Sent** (Initial Implementation):
- No email service configured initially
- Show copyable invite link in UI
- Admin manually sends link to user
- Phase 2: Add SMTP service for automatic emails

**Rationale**:
- Prevents spam registrations and abuse
- Provides access control from day one
- Aligns with enterprise/team collaboration model
- Reduces support burden (only invited users)
- Email auto-verified (came from trusted invite)

**Future Enhancement**:
- Role-based invites (admin, member, viewer)
- Bulk invite CSV upload
- Invite expiry reminders
- Waitlist for public launch

---

### **7. Rate Limiting: Per-Account + Per-IP**

**Per-Account Limits**:
- **Login attempts**: 5 attempts per 15 minutes per email
- **Password reset**: 3 requests per hour per email
- **2FA verification**: 10 attempts per 15 minutes per account

**Per-IP Limits**:
- **Login attempts**: 10 attempts per 15 minutes per IP
- **Registration**: 5 signups per hour per IP (for invite redemption)
- **API calls**: 1000 requests per 15 minutes per IP (general)

**Implementation**:
- **Algorithm**: Token bucket
- **Storage**: In-memory dictionary (Python dict) for MVP
- **Future**: Redis for distributed rate limiting
- **Response**: 429 Too Many Requests with Retry-After header

**Lockout Behavior**:
- **Per-Account**: After 5 failed logins → Lock for 15 minutes
- **Per-IP**: After 10 failed logins → Lock for 15 minutes
- **Notification**: Email user on account lockout (potential attack)

**Bypass for Admins**:
- Admins can unlock accounts via Settings UI
- Log all manual unlocks for audit

**Rationale**:
- Per-account prevents credential stuffing attacks
- Per-IP prevents distributed brute force attacks
- Dual limits provide defense in depth
- Token bucket allows burst traffic while limiting sustained abuse
- Email notifications alert users to attacks

---

## Email Service Integration

### SMTP Configuration (Phase 2)

**Required Emails**:
- Invite emails (user registration invites)
- Email OTP codes (2FA fallback)
- Account security alerts (lockout, password change, 2FA changes)
- Email verification (if open signup added later)

**SMTP Settings** (stored in database, configurable via UI):
- SMTP host (e.g., smtp.gmail.com)
- SMTP port (587 for TLS, 465 for SSL)
- SMTP username
- SMTP password (encrypted with Fernet)
- From email address
- From name (e.g., "TheAppApp Team")

**Email Templates**:
- HTML templates with inline CSS (email client compatibility)
- Plain text fallback
- Variables: {{user_name}}, {{invite_link}}, {{otp_code}}, etc.

**Email Service** (`backend/services/email_service.py`):
- `send_invite_email(to, invite_link)`
- `send_otp_email(to, otp_code)`
- `send_security_alert(to, alert_type, details)`
- Queue emails for async sending (Celery or background thread)

**Frontend SMTP Settings UI** (Settings → Email Configuration):
- Test connection button
- Send test email
- View email queue/logs
- Toggle email features on/off

---

## Database Schema

### users table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(60) NOT NULL,  -- bcrypt hash
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    invited_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
```

### user_sessions table
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(60) NOT NULL,  -- bcrypt hash
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),  -- IPv6 max length
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(refresh_token_hash);
CREATE INDEX idx_sessions_expiry ON user_sessions(expires_at);
```

### two_factor_auth table
```sql
CREATE TABLE two_factor_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    secret_encrypted TEXT NOT NULL,  -- Fernet encrypted TOTP secret
    backup_codes_encrypted JSONB NOT NULL,  -- Array of bcrypt hashes
    email_fallback_enabled BOOLEAN DEFAULT true,
    enabled_at TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX idx_2fa_user ON two_factor_auth(user_id);
```

### user_invites table
```sql
CREATE TABLE user_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    invite_token UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    invited_by UUID NOT NULL REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,  -- 48 hours from creation
    consumed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_invites_token ON user_invites(invite_token);
CREATE INDEX idx_invites_email ON user_invites(email);
CREATE INDEX idx_invites_expiry ON user_invites(expires_at);
```

### email_settings table (for SMTP config)
```sql
CREATE TABLE email_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    smtp_host VARCHAR(255) NOT NULL,
    smtp_port INTEGER NOT NULL,
    smtp_username VARCHAR(255) NOT NULL,
    smtp_password_encrypted TEXT NOT NULL,  -- Fernet encrypted
    from_email VARCHAR(255) NOT NULL,
    from_name VARCHAR(255) NOT NULL,
    use_tls BOOLEAN DEFAULT true,
    is_enabled BOOLEAN DEFAULT false,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Security Considerations

### Threat Model

**Threats Addressed**:
- ✅ Brute force password attacks (bcrypt + rate limiting)
- ✅ Credential stuffing (rate limiting per account + IP)
- ✅ Token theft (short-lived access tokens, httpOnly cookies)
- ✅ Session hijacking (session tracking with IP/user agent, revocation)
- ✅ Account takeover (2FA required for sensitive operations)
- ✅ XSS attacks (httpOnly cookies, CSP headers)
- ✅ CSRF attacks (SameSite cookies, CSRF tokens)
- ✅ SQL injection (parameterized queries, ORM usage)
- ✅ Timing attacks (constant-time comparison for tokens)

**Threats Requiring Additional Mitigation**:
- ⚠️ Phishing (user education, warn about fake login pages)
- ⚠️ Device compromise (2FA helps, backup codes at risk)
- ⚠️ Insider threats (audit logging, least privilege)

### Security Best Practices

**Password Security**:
- Never log or display passwords
- Always use bcrypt with min 12 rounds
- Require password change if breach detected (HaveIBeenPwned API)
- Force password reset on suspicious activity

**Token Security**:
- Sign JWTs with strong secret (256+ bits)
- Rotate signing key periodically (once per quarter)
- Never expose tokens in URLs or logs
- Validate token signature, expiry, and session on every request

**Session Security**:
- Track IP address and user agent for each session
- Alert user on login from new device/location
- Provide session management UI (view/revoke sessions)
- Revoke all sessions on password change or 2FA disable

**2FA Security**:
- Encrypt TOTP secrets at rest (Fernet encryption)
- Never display secret after initial setup
- Backup codes hashed like passwords (bcrypt)
- Rate limit 2FA attempts (10 per 15min)

**Email Security**:
- Use STARTTLS for SMTP connections
- Encrypt SMTP credentials at rest
- Rate limit OTP email sends
- Include security warnings in emails

---

## Testing Strategy

### Unit Tests
1. **Password hashing**: Verify bcrypt rounds, uniqueness of salts
2. **JWT generation/validation**: Test signing, expiry, claims
3. **TOTP generation/verification**: Test code validity, time windows
4. **Backup code hashing/validation**: Test bcrypt, single-use consumption
5. **Rate limiting**: Test bucket algorithm, reset timing
6. **Token refresh logic**: Test expiry detection, automatic refresh

### Integration Tests
1. **Full registration flow**: Invite → Signup → Login
2. **Login with 2FA**: Credentials → TOTP verification → Token issuance
3. **Email OTP fallback**: Request OTP → Receive email → Verify code
4. **Session management**: Create session → Refresh token → Revoke session
5. **Rate limiting**: Trigger limits → Verify 429 responses → Test reset
6. **Concurrent sessions**: Login from 3 devices → Verify oldest revoked

### Security Tests
1. **Brute force resistance**: Attempt 100 logins → Verify rate limiting
2. **Token tampering**: Modify JWT claims → Verify rejection
3. **Session hijacking**: Use token from different IP → Verify security warnings
4. **SQL injection**: Submit malicious input → Verify sanitization
5. **XSS prevention**: Submit script tags → Verify escaping
6. **Timing attack resistance**: Test password comparison timing

### End-to-End Tests (Playwright)
1. **Full user journey**: Invite → Register → Login → 2FA Setup → Login with 2FA
2. **Forgot password flow**: Request reset → Email → Set new password → Login
3. **Session management UI**: View sessions → Revoke session → Verify logout
4. **Account lockout**: Fail 5 logins → Verify lockout → Wait 15min → Retry
5. **Email OTP**: Select fallback → Receive email → Verify code

---

## Dependencies

**Depends On**:
- Database schema (PostgreSQL)
- Email service (SMTP) - Phase 2
- Frontend framework (React + TypeScript)
- State management (Zustand)

**Enables**:
- All multi-user features
- Project ownership and permissions
- API key management
- GitHub integration security
- Cost tracking per user
- Audit logging

---

## Implementation Plan

### Phase 1: Core Authentication (Week 1-2)
1. Create database tables and migrations
2. Implement AuthService (register, login, token management)
3. Implement JWT middleware
4. Build login and invite-redemption pages
5. Create session management backend
6. Unit and integration tests

### Phase 2: Two-Factor Authentication (Week 3)
1. Implement TwoFactorService
2. Create 2FA API endpoints
3. Build 2FA setup and verification pages
4. Add backup code support
5. Email OTP fallback (requires SMTP)
6. Security and E2E tests

### Phase 3: Session Management & Rate Limiting (Week 4)
1. Implement rate limiting middleware
2. Build session management UI
3. Add security alerts
4. Create admin unlock functionality
5. Session cleanup cron job
6. Load and stress testing

### Phase 4: Email Service Integration (Week 5)
1. Implement EmailService
2. Create SMTP settings UI
3. Design email templates
4. Add invite email automation
5. Implement email queue
6. Test email delivery

---

## Metrics & Monitoring

**Key Metrics**:
- **Authentication Success Rate**: % of successful logins
- **2FA Adoption Rate**: % of users with 2FA enabled
- **Account Lockout Rate**: Accounts locked per day (detect attacks)
- **Token Refresh Rate**: Refreshes per hour (performance metric)
- **Session Duration**: Average session length
- **Failed Login Attempts**: Failed logins per hour per account/IP

**Alerts**:
- Sustained failed login attempts (>50/min) → Potential attack
- Multiple account lockouts (>10/hour) → Distributed attack
- Unusually high token refresh failures → Backend issue
- SMTP send failures → Email service down

**Logging**:
- All authentication events (login, logout, 2FA)
- All security events (lockout, password change, session revocation)
- Rate limiting triggers
- Token refresh operations
- Admin actions (unlock account, revoke sessions)

---

## Future Enhancements

**Short Term** (Next 3-6 months):
- WebAuthn/FIDO2 support (hardware keys)
- Social login (Google, GitHub OAuth)
- Remember device (skip 2FA for 30 days on trusted devices)
- Session analytics (device types, locations, activity patterns)

**Long Term** (6-12 months):
- Risk-based authentication (adaptive security based on behavior)
- Passwordless login (magic links, passkeys)
- Multi-tenancy with organization accounts
- SAML/SSO for enterprise customers
- Anomaly detection (unusual login patterns, IP changes)

---

## Notes

- This decision establishes production-grade security from day one
- Invite-only system provides controlled rollout and prevents abuse
- TOTP with email fallback balances security and accessibility
- 2-session limit aligns with typical usage patterns
- Rate limiting provides defense against common attacks
- Email service integration enables full automation in Phase 2

---

*Decision resolved: Nov 1, 2025*  
*Implementation priority: P1 - Required before multi-user features*
