# Goal
Implement a user authentication system with email verification and password reset functionality. The system should support user registration, login, logout, and password recovery flows.

# Success Criteria
- Users can register with email and password
- Email verification link is sent upon registration
- Users can login with verified email and password
- Users can logout and session is properly cleared
- Users can request password reset via email
- Password reset token expires after 24 hours
- All passwords are hashed using bcrypt
- Unit tests achieve >90% code coverage
- Integration tests cover all user flows
- API endpoints return appropriate status codes

# Constraints
- Budget limit: $5.00
- Maximum iterations: 15
- Must use existing database schema
- Must be compatible with Python 3.9+
- No external authentication services (OAuth, Auth0, etc.)
- Password minimum length: 8 characters
- Email verification token valid for 48 hours
- Rate limiting: 5 login attempts per minute per IP

# Context
This authentication system will be integrated into an existing web application. The application currently uses Flask framework and PostgreSQL database. The user table already exists with columns: id, email, password_hash, is_verified, created_at, updated_at.

The system needs to be production-ready and follow security best practices. Consider edge cases like concurrent login attempts, token replay attacks, and email deliverability issues.
