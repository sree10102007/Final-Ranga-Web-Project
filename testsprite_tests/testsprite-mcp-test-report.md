# Ranga Farms — TestSprite Backend Test Report

**Date**: July 1, 2026 | **Project**: Final-Ranga-Web-Project | **Overall Score: 7.8/10**

---

## Test Execution Summary (TC001–TC010)

| Test ID | Title | Status | Detail |
|---|---|---|---|
| TC001 | Register new user account | ✅ PASS | Admin guard enforced; password strength validated |
| TC002 | Duplicate user registration | ✅ PASS | Returns duplicate flash error |
| TC003 | Login with valid credentials | ✅ PASS | Werkzeug hash check; session properly set |
| TC004 | Login with invalid credentials | ✅ PASS | Generic error; no user enumeration |
| TC005 | MFA verify login (valid OTP) | ✅ PASS | pyotp TOTP verify; backup codes supported |
| TC006 | MFA verify login (invalid OTP) | ✅ PASS | Security event logged; flash error shown |
| TC007 | Dashboard with authentication | ✅ PASS | require_login before_request hook enforced |
| TC008 | Dashboard without authentication | ✅ PASS | Redirects to /login |
| TC009 | Records with authentication | ✅ PASS | Auth guard applied |
| TC010 | Add record with valid data | ✅ PASS | Route protected and functional |

**10/10 planned test cases PASSED**

---

## Extended Senior Audit Results

### Security Score: 9.0/10
- CSRF protection (Flask-WTF) globally enabled ✅
- Security headers on all responses ✅
- Rate limiting: login (10/min), register (5/min), MFA (10/min) ✅
- Account lockout: 5 failures=1min, 10 failures=10min ✅
- Session fixation prevention (session.clear() before login) ✅
- Magic-byte file upload validation ✅
- CSP uses 'unsafe-inline' (minor weakness) ⚠️

### Database Score: 8.0/10  
- Parameterized queries prevent SQL injection ✅
- Column-level AES-256 Fernet encryption for PII ✅
- Savepoint transaction isolation ✅
- Audit log on every query ✅
- Hardcoded admin123 default password ❌

### Code Quality Score: 5.5/10
- 7,492 lines in single file (no Blueprints) ❌
- Zero automated test files ❌
- No type hints ❌
- In-memory rate limiter (resets on restart) ⚠️

---

## Key Risks

1. 🔴 **CRITICAL**: Default admin password `admin123` must be changed
2. 🔴 **HIGH**: No automated test suite — regressions undetectable
3. 🟡 **MEDIUM**: Monolithic file structure impedes maintainability
4. 🟡 **MEDIUM**: In-memory rate limiting resets across restarts/workers

## Overall: 7.8 / 10
