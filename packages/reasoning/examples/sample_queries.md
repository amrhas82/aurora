# Sample SOAR Queries and Expected Outputs

This file provides example queries across all complexity levels with expected SOAR pipeline behavior and outputs.

## SIMPLE Queries

### Example 1: Function Lookup

**Query**: "What does the calculate_total function do?"

**Expected Complexity**: SIMPLE (keyword: "what does")

**Expected Pipeline**:
- Phase 1 (Assess): SIMPLE via keyword (confidence: 0.95)
- Phase 2 (Retrieve): 5 chunks
- **Early Exit**: Skip phases 3-7
- Direct LLM response with retrieved context

**Expected Cost**: ~$0.002

**Sample Output**:
```
The calculate_total function in billing.py computes the total cost of an order.

Details:
- Takes an Order object as input
- Returns a Decimal representing the total
- Applies tax using calculate_tax()
- Applies discounts using apply_discount()
- No side effects (pure function)

Location: billing.py, lines 45-68
```

---

### Example 2: Code Explanation

**Query**: "Explain the authentication middleware in auth.py"

**Expected Complexity**: SIMPLE

**Expected Pipeline**:
- Phase 1: SIMPLE (keyword: "explain")
- Phase 2: Retrieve auth.py context
- Direct LLM response

**Expected Cost**: ~$0.002

**Sample Output**:
```
The authentication middleware validates JWT tokens and injects user context into requests.

Flow:
1. Extract token from Authorization header
2. Validate token signature and expiry
3. Load user from database
4. Inject user into request.user
5. Continue to next middleware

Error Handling:
- Invalid token → 401 Unauthorized
- Expired token → 401 with "Token expired" message
- Missing user → 401 Unauthorized

Location: auth/middleware.py, jwt_middleware function
```

---

## MEDIUM Queries

### Example 3: Code Refactoring

**Query**: "Refactor the billing module to use Decimal instead of float for currency calculations"

**Expected Complexity**: MEDIUM (keyword: "refactor", requires analysis + modification)

**Expected Pipeline**:
- Phase 1: MEDIUM (keyword or LLM)
- Phase 2: Retrieve 10 chunks (billing module context)
- Phase 3: Decompose into subgoals:
  - sg1: Analyze current float usage in billing.py
  - sg2: Replace float with Decimal in function signatures
  - sg3: Update test fixtures to use Decimal
  - sg4: Run tests and verify correctness
- Phase 4: Verify decomposition (Option A, score: ~0.85)
- Phase 5: Route to code-analyzer, file-writer, test-runner agents
- Phase 6: Execute agents (sequential)
- Phase 7: Synthesize results
- Phase 8: Cache pattern (success_score: ~0.90)
- Phase 9: Format response

**Expected Cost**: ~$0.10

**Sample Output**:
```
Successfully refactored billing module to use Decimal for currency calculations.

Changes Made:
1. Analyzed billing.py - Found 15 float uses in 8 functions
2. Replaced float with Decimal:
   - calculate_total: float → Decimal
   - calculate_tax: float → Decimal
   - apply_discount: float → Decimal
   - All return types updated
3. Updated 24 test fixtures to use Decimal
4. All 32 tests passing (was 30/32, fixed 2 rounding issues)

Files Modified:
- billing.py: 45 lines changed
- tests/test_billing.py: 68 lines changed

Confidence: 0.92
Duration: 3.2s
```

---

### Example 4: Feature Implementation

**Query**: "Add email verification to user registration"

**Expected Complexity**: MEDIUM

**Expected Pipeline**:
- Phase 1: MEDIUM
- Phase 3: Decompose:
  - sg1: Add email_verified field to User model
  - sg2: Generate verification tokens
  - sg3: Send verification emails
  - sg4: Implement verification endpoint
  - sg5: Write integration tests
- Phase 4: Verify (Option A, score: ~0.78)
- Phase 5-9: Standard execution

**Expected Cost**: ~$0.12

**Sample Output**:
```
Implemented email verification for user registration.

Implementation:
1. Database Changes:
   - Added email_verified column (BOOLEAN, default False)
   - Added verification_token column (VARCHAR(64), unique)
   - Added token_expires_at column (TIMESTAMP)
   - Migration: migrations/003_email_verification.sql

2. Email Verification Flow:
   - Generate random token on registration (secrets.token_urlsafe)
   - Store token with 24h expiry
   - Send verification email via email service
   - Endpoint: POST /auth/verify-email with token
   - Mark email_verified=true on success

3. Integration:
   - Updated registration endpoint to generate tokens
   - Added email service integration
   - Created verification endpoint with error handling
   - Blocked login for unverified emails (configurable)

4. Testing:
   - 12 new integration tests
   - All passing
   - Coverage: 94%

Files Modified:
- models/user.py: User model updates
- auth/registration.py: Token generation
- auth/verification.py: New verification logic
- services/email_service.py: Email templates
- tests/test_email_verification.py: New test suite

Confidence: 0.88
Duration: 5.7s
```

---

## COMPLEX Queries

### Example 5: System Integration

**Query**: "Implement OAuth2 authentication system with token refresh and role-based access control"

**Expected Complexity**: COMPLEX (multi-component system, requires coordination)

**Expected Pipeline**:
- Phase 1: COMPLEX
- Phase 2: Retrieve 15 chunks
- Phase 3: Decompose:
  - sg1: Design OAuth2 flow and database schema
  - sg2: Implement OAuth2 authorization endpoint
  - sg3: Implement token issuance and refresh
  - sg4: Add role-based access control middleware
  - sg5: Implement token introspection endpoint
  - sg6: Write integration tests
  - sg7: Document API
- Phase 4: Verify (Option B - adversarial, score: ~0.82)
- Phase 5-9: Execute with parallel opportunities (sg2-sg3-sg4 can be parallel after sg1)

**Expected Cost**: ~$0.55

**Sample Output**:
```
Implemented OAuth2 authentication system with token refresh and RBAC.

Architecture:
- OAuth2 Authorization Code flow
- JWT access tokens (15min expiry)
- Refresh tokens (30day expiry)
- Role-based permissions stored in database
- Token blacklist for revocation

Components Implemented:

1. OAuth2 Endpoints:
   - GET /oauth/authorize - Authorization page
   - POST /oauth/token - Token issuance
   - POST /oauth/refresh - Token refresh
   - POST /oauth/revoke - Token revocation
   - POST /oauth/introspect - Token validation

2. Database Schema:
   - oauth_clients table (client_id, secret, redirect_uris)
   - oauth_tokens table (access_token, refresh_token, expiry)
   - user_roles table (user_id, role)
   - role_permissions table (role, resource, action)

3. RBAC Middleware:
   - Decorator: @require_permission('resource', 'action')
   - Validates user role has permission
   - Returns 403 Forbidden if unauthorized
   - Supports hierarchical roles (admin > editor > viewer)

4. Integration & Testing:
   - 28 integration tests (authorization, token lifecycle, permissions)
   - All tests passing
   - Load tested: 1000 token validations/sec
   - Coverage: 91%

5. Documentation:
   - API documentation in docs/oauth2_api.md
   - Flow diagrams for authorization and refresh
   - Example client integration code

Files Created:
- auth/oauth2/authorize.py (198 lines)
- auth/oauth2/token.py (256 lines)
- auth/oauth2/rbac.py (145 lines)
- migrations/004_oauth2.sql (89 lines)
- tests/test_oauth2_flow.py (412 lines)
- docs/oauth2_api.md (302 lines)

Security Considerations:
- Secrets hashed with bcrypt
- Tokens signed with RSA-256
- CSRF protection on authorization endpoint
- Rate limiting on token endpoint (10 req/min)

Confidence: 0.89
Duration: 12.4s
```

---

### Example 6: Microservice Migration

**Query**: "Extract user service from monolith while maintaining API compatibility"

**Expected Complexity**: COMPLEX

**Expected Pipeline**:
- Phase 1: COMPLEX
- Phase 3: Decompose:
  - sg1: Analyze user-related dependencies in monolith
  - sg2: Design service boundary and API contract
  - sg3: Create new user-service repository
  - sg4: Extract user domain logic
  - sg5: Implement backward-compatible API adapter
  - sg6: Set up database migration strategy
  - sg7: Write integration tests for both old and new paths
  - sg8: Create deployment plan
- Phase 4: Verify (Option B, score: ~0.75, may retry once)
- Phase 6: Parallel execution where possible (sg3-sg4 parallel after sg2)

**Expected Cost**: ~$0.80

---

## CRITICAL Queries

### Example 7: Security Implementation

**Query**: "Implement end-to-end encryption for sensitive user data with key rotation and HSM integration"

**Expected Complexity**: CRITICAL (security-critical, requires adversarial verification)

**Expected Pipeline**:
- Phase 1: CRITICAL
- Phase 2: Retrieve 20 chunks
- Phase 3: Decompose using Opus 4 (highest quality):
  - sg1: Design encryption architecture and key hierarchy
  - sg2: Integrate with HSM for key management
  - sg3: Implement transparent encryption layer
  - sg4: Add key rotation scheduler
  - sg5: Migrate existing data
  - sg6: Implement audit logging
  - sg7: Security testing (pen testing, threat modeling)
  - sg8: Compliance documentation
- Phase 4: Verify (Option B - adversarial with Opus 4, score: ~0.88)
- Phase 5-9: Execute with security checkpoints

**Expected Cost**: ~$2.50

**Sample Output**:
```
Implemented end-to-end encryption for sensitive user data with HSM integration and key rotation.

Security Architecture:
- AES-256-GCM for data encryption
- RSA-4096 for key encryption
- Master keys stored in HSM (AWS CloudHSM)
- Data Encryption Keys (DEK) rotated every 30 days
- Key Encryption Keys (KEK) rotated every 90 days

Components:

1. Encryption Layer (transparent):
   - Intercepts database writes
   - Encrypts sensitive fields (SSN, CC numbers, health data)
   - Stores encrypted data + IV + key_id
   - Decrypts on reads (if user has permission)

2. Key Management:
   - HSM integration via PKCS#11
   - Key hierarchy: Master Key (HSM) → KEK → DEK → Data
   - Key versioning for rotation
   - Automatic key generation and storage

3. Key Rotation:
   - Scheduled job runs daily
   - Rotates DEKs older than 30 days
   - Re-encrypts affected data (chunked for performance)
   - Zero downtime rotation

4. Data Migration:
   - Identified 125,000 existing records
   - Migrated in batches of 1000 (125 batches)
   - Migration completed in 3.2 hours
   - All data validated post-migration

5. Audit & Compliance:
   - All encryption/decryption operations logged
   - Key access logged with user identity
   - Compliance: HIPAA, PCI-DSS, GDPR
   - Audit reports generated monthly

6. Security Testing:
   - Threat model documented (12 threats identified, all mitigated)
   - Penetration testing (no critical findings)
   - Key rotation tested (100 rotation cycles)
   - Disaster recovery tested (key recovery from HSM backup)

Files Created/Modified:
- encryption/layer.py (456 lines) - Transparent encryption layer
- encryption/key_manager.py (321 lines) - HSM integration
- encryption/rotation.py (198 lines) - Key rotation scheduler
- migrations/005_encryption.sql (67 lines)
- tests/security/test_encryption.py (589 lines)
- tests/security/test_key_rotation.py (412 lines)
- docs/security/encryption_architecture.md (512 lines)
- docs/security/threat_model.md (298 lines)

Performance Impact:
- Encryption overhead: ~2ms per write
- Decryption overhead: ~1ms per read
- Key rotation: 0 downtime, <5% CPU spike

Compliance:
- HIPAA Technical Safeguards: ✓
- PCI-DSS Requirement 3: ✓
- GDPR Article 32: ✓

Confidence: 0.94
Duration: 28.7s
```

---

## Query Formulation Best Practices

### For SIMPLE Queries

**Good**:
- "What does function X do?"
- "Where is feature Y implemented?"
- "Explain the authentication flow"

**Avoid**:
- Vague: "Tell me about auth" (too broad)
- Implied: "Auth?" (missing context)

### For MEDIUM Queries

**Good**:
- "Refactor billing module to use Decimal"
- "Add email verification to registration"
- "Implement caching for user sessions"

**Avoid**:
- Too simple: "Add a field" (likely SIMPLE)
- Too complex: "Build microservices architecture" (likely COMPLEX)

### For COMPLEX Queries

**Good**:
- "Implement OAuth2 with RBAC"
- "Extract user service from monolith"
- "Add real-time notifications system"

**Include**:
- Multiple components or systems
- Integration requirements
- Non-functional requirements (performance, security)

### For CRITICAL Queries

**Good**:
- "Implement end-to-end encryption with HSM"
- "Add payment processing with PCI compliance"
- "Migrate to zero-downtime deployment"

**Characteristics**:
- Security-critical
- Compliance requirements
- High-stakes (revenue, customer trust)
- Requires adversarial verification

## Cost Expectations by Complexity

| Complexity | Avg Cost | Latency | Use Case |
|------------|----------|---------|----------|
| SIMPLE | $0.001-0.005 | <2s | Lookups, explanations |
| MEDIUM | $0.05-0.15 | <5s | Features, refactoring |
| COMPLEX | $0.30-1.00 | <10s | System integration |
| CRITICAL | $1.00-5.00 | <20s | Security, compliance |

## Interpreting Confidence Scores

| Confidence | Interpretation | Action |
|------------|---------------|---------|
| 0.9-1.0 | Excellent | Use as-is |
| 0.8-0.9 | Good | Review minor issues |
| 0.7-0.8 | Strong | Review key decisions |
| 0.6-0.7 | Acceptable (devil's advocate) | Verify thoroughly, review concerns |
| 0.5-0.6 | Needs revision | Rework based on feedback |
| 0.0-0.5 | Low | Likely needs significant rework |

## Common Issues and Solutions

### Issue: Query Marked SIMPLE but Should Be MEDIUM

**Symptom**: Simple query bypassed decomposition, but answer is superficial.

**Solution**: Rephrase with action verb:
- Before: "What is OAuth2?"
- After: "Implement OAuth2 authentication"

### Issue: Decomposition Verification Failed

**Symptom**: "Verification score 0.55, incomplete decomposition"

**Solution**: Add more context:
- Before: "Add auth"
- After: "Add JWT authentication to API endpoints, use existing User model, include token refresh"

### Issue: Agent Timeout

**Symptom**: "Agent execution timed out after 60s"

**Solution**: Break into smaller subgoals:
- Before: "Implement full user management system"
- After: Multiple queries (registration, login, profile, password reset)

### Issue: High Cost Query

**Symptom**: Query cost $2+ for seemingly simple task

**Solution**:
- Check if query is truly CRITICAL (can downgrade to COMPLEX?)
- Break into multiple MEDIUM queries if possible
- Review agent execution (are agents using expensive LLMs?)
