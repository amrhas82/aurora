#!/usr/bin/env python3
"""
Test corpus for complexity assessment validation.

Each entry contains:
- prompt: The actual prompt text
- expected: Expected complexity level (simple/medium/complex)
- category: Category for analysis
- notes: Why this classification is expected
"""

# Format: (prompt, expected_level, category, notes)
TEST_CORPUS = [
    # ==================== SIMPLE PROMPTS ====================

    # Simple - Lookup/Display
    ("what is python", "simple", "lookup", "Basic definition query"),
    ("show me the readme", "simple", "lookup", "Single file display"),
    ("list all files", "simple", "lookup", "Simple listing command"),
    ("where is the config file", "simple", "lookup", "Location query"),
    ("which function handles auth", "simple", "lookup", "Specific function query"),
    ("print the error log", "simple", "lookup", "Display command"),
    ("run the tests", "simple", "command", "Single command execution"),
    ("what does this function do", "simple", "lookup", "Explanation of existing code"),
    ("check if tests pass", "simple", "command", "Single verification"),
    ("find the main entry point", "simple", "lookup", "Single item search"),
    ("who wrote this file", "simple", "lookup", "Git blame query"),
    ("when was this last modified", "simple", "lookup", "Single metadata query"),
    ("show git status", "simple", "command", "Single git command"),
    ("count the lines in this file", "simple", "lookup", "Simple counting"),
    ("what's in the .env file", "simple", "lookup", "File content query"),
    ("open the settings", "simple", "command", "Simple open command"),
    ("is there a dockerfile", "simple", "lookup", "Existence check"),
    ("what version of node", "simple", "lookup", "Version query"),
    ("tell me about this class", "simple", "lookup", "Single item explanation"),
    ("give me the api endpoint", "simple", "lookup", "Single item retrieval"),

    # Simple - Single action
    ("fix the typo in readme", "simple", "fix", "Single obvious fix"),
    ("add a console.log here", "simple", "edit", "Single line addition"),
    ("remove this comment", "simple", "edit", "Single deletion"),
    ("rename this variable to x", "simple", "edit", "Single rename"),
    ("update the version to 2.0", "simple", "edit", "Single value change"),

    # ==================== MEDIUM PROMPTS ====================

    # Medium - Analysis/Explanation
    ("explain how the authentication works", "medium", "analysis", "Requires tracing through code"),
    ("why is this test failing", "medium", "debug", "Requires investigation"),
    ("compare these two approaches", "medium", "analysis", "Requires evaluation"),
    ("analyze the performance of this function", "medium", "analysis", "Requires profiling understanding"),
    ("debug the login issue", "medium", "debug", "Requires investigation"),
    ("what's the difference between these implementations", "medium", "analysis", "Comparison required"),
    ("how does the caching mechanism work", "medium", "analysis", "Requires understanding system"),
    ("evaluate this code for security issues", "medium", "analysis", "Requires security review"),
    ("investigate why users are getting errors", "medium", "debug", "Root cause analysis"),
    ("describe the data flow", "medium", "analysis", "Requires tracing"),

    # Medium - Moderate modification
    ("add error handling to this function", "medium", "edit", "Multiple locations, judgment needed"),
    ("update the api endpoint to use v2", "medium", "edit", "May affect multiple files"),
    ("fix the bug where users can't login", "medium", "fix", "Requires investigation first"),
    ("add logging to the payment flow", "medium", "edit", "Multiple touchpoints"),
    ("refactor this function to be more readable", "medium", "refactor", "Judgment required"),
    ("write a test for this component", "medium", "test", "New test creation"),
    ("add validation to the form", "medium", "edit", "Multiple fields/rules"),
    ("improve the error messages", "medium", "edit", "Multiple messages, judgment"),
    ("convert this to typescript", "medium", "refactor", "Systematic change"),
    ("add pagination to the list", "medium", "feature", "Moderate feature addition"),

    # Medium - Multi-step but bounded
    ("first check if tests pass, then commit", "medium", "workflow", "Explicit multi-step"),
    ("run linting and fix any issues", "medium", "workflow", "Two-part task"),
    ("update dependencies and check for breaking changes", "medium", "workflow", "Multi-step analysis"),
    ("find all uses of deprecated api and list them", "medium", "analysis", "Search and compile"),
    ("add a new route for user profile", "medium", "feature", "Defined scope addition"),

    # ==================== COMPLEX PROMPTS ====================

    # Complex - Major implementation
    ("implement user authentication with oauth", "complex", "feature", "Major feature, multiple components"),
    ("design a caching system for the api", "complex", "architecture", "System design required"),
    ("architect a microservices solution", "complex", "architecture", "High-level design"),
    ("build a real-time notification system", "complex", "feature", "Complex feature, multiple concerns"),
    ("create a complete crud api for products", "complex", "feature", "Full implementation"),
    ("develop a plugin system", "complex", "architecture", "Framework design"),
    ("implement full-text search", "complex", "feature", "Complex feature"),
    ("build an admin dashboard", "complex", "feature", "Large feature, multiple views"),
    ("create a testing framework", "complex", "architecture", "Framework development"),
    ("implement rate limiting across all endpoints", "complex", "feature", "Cross-cutting concern"),

    # Complex - Multi-system/scope
    ("refactor the entire authentication module", "complex", "refactor", "Scope: entire module"),
    ("migrate the database from mysql to postgres", "complex", "migration", "Major migration"),
    ("integrate payment processing with stripe", "complex", "integration", "External integration"),
    ("implement caching across all api endpoints", "complex", "feature", "Cross-cutting implementation"),
    ("update all components to use the new design system", "complex", "refactor", "Codebase-wide change"),
    ("restructure the project to monorepo", "complex", "architecture", "Major restructure"),
    ("optimize performance across the application", "complex", "optimization", "Application-wide"),

    # Complex - With constraints
    ("implement new auth without breaking existing sessions", "complex", "feature", "Feature + constraint"),
    ("refactor the api while maintaining backwards compatibility", "complex", "refactor", "Refactor + constraint"),
    ("migrate to new framework ensuring all tests still pass", "complex", "migration", "Migration + constraint"),
    ("add feature flags while keeping deployment simple", "complex", "feature", "Feature + constraint"),
    ("optimize database queries without changing the schema", "complex", "optimization", "Optimization + constraint"),

    # Complex - Multi-domain
    ("implement authentication on frontend and backend with database storage", "complex", "feature", "Multi-layer"),
    ("add real-time updates using websockets with proper error handling and reconnection", "complex", "feature", "Multiple concerns"),
    ("create api endpoints with authentication, rate limiting, and caching", "complex", "feature", "Multiple features"),
    ("implement ci/cd pipeline with testing, staging, and production deployments", "complex", "devops", "Multi-stage pipeline"),
    ("build a monitoring system with logging, metrics, and alerting", "complex", "feature", "Multiple components"),

    # Complex - Explicit multi-step with conditions
    ("first analyze the current architecture, then design improvements, implement them, and write tests", "complex", "workflow", "Multi-phase project"),
    ("1. review all api endpoints 2. identify security issues 3. fix them 4. add tests", "complex", "workflow", "Numbered complex tasks"),
    ("implement the feature, add tests, update documentation, and create a migration guide", "complex", "workflow", "Multi-deliverable"),
    ("refactor to clean architecture: separate concerns, add interfaces, implement dependency injection", "complex", "refactor", "Multi-part architectural change"),

    # ==================== EDGE CASES ====================

    # Short but complex
    ("design the system", "complex", "edge", "Short but implies full architecture"),
    ("implement oauth", "complex", "edge", "Short but major feature"),
    ("build authentication", "complex", "edge", "Short but significant scope"),

    # Long but simple
    ("can you please show me the contents of the readme file in the root directory", "simple", "edge", "Verbose but single action"),
    ("i would like you to tell me what version of python is being used in this project", "simple", "edge", "Verbose but lookup"),

    # Questions that seem simple but aren't
    ("how should we handle errors across the application", "complex", "edge", "Question implies design decision"),
    ("what's the best architecture for real-time features", "complex", "edge", "Architectural question"),

    # Ambiguous/Context-dependent
    ("add a button", "simple", "edge", "Could be simple or complex depending on context"),
    ("fix the bug", "medium", "edge", "Scope unknown"),
    ("improve performance", "complex", "edge", "Open-ended optimization"),

    # Real-world examples
    ("help me understand why this regex isn't matching", "medium", "real", "Debug with explanation"),
    ("i'm getting a 500 error on the /api/users endpoint, can you help", "medium", "real", "Debug scenario"),
    ("the app crashes when i click submit, fix it", "medium", "real", "Bug fix with investigation"),
    ("write a function that sorts an array", "simple", "real", "Single function implementation"),
    ("create a user registration flow with email verification", "complex", "real", "Multi-step feature"),
    ("add dark mode support to the app", "complex", "real", "Cross-cutting UI change"),
    ("set up docker for local development", "medium", "real", "Environment setup"),
    ("configure eslint with our team's rules", "medium", "real", "Config with judgment"),
    ("implement the search feature from the figma design", "complex", "real", "Feature from spec"),
    ("add input validation following owasp guidelines", "complex", "real", "Security feature"),

    # ==================== CRITICAL PROMPTS ====================

    # Critical - Security
    ("fix security vulnerability in authentication", "critical", "security", "Security keyword override"),
    ("patch the authentication bypass vulnerability", "critical", "security", "Vulnerability + authentication"),
    ("investigate data breach in user table", "critical", "security", "Breach keyword"),
    ("encrypt sensitive payment data", "critical", "security", "Encrypt + payment"),

    # Critical - Production/Emergency
    ("production outage emergency", "critical", "emergency", "Production + emergency keywords"),
    ("fix critical bug in production api", "critical", "emergency", "Critical + production"),
    ("emergency incident response needed", "critical", "emergency", "Emergency + incident"),
    ("production database corruption detected", "critical", "emergency", "Production + corruption"),

    # Critical - Compliance/Legal
    ("ensure gdpr compliance for user data", "critical", "compliance", "GDPR keyword"),
    ("implement hipaa compliant logging", "critical", "compliance", "HIPAA keyword"),
    ("audit payment transaction security", "critical", "compliance", "Audit + payment + security"),
]

# Group prompts by expected level for analysis
SIMPLE_PROMPTS = [(p, c, n) for p, level, c, n in TEST_CORPUS if level == "simple"]
MEDIUM_PROMPTS = [(p, c, n) for p, level, c, n in TEST_CORPUS if level == "medium"]
COMPLEX_PROMPTS = [(p, c, n) for p, level, c, n in TEST_CORPUS if level == "complex"]
CRITICAL_PROMPTS = [(p, c, n) for p, level, c, n in TEST_CORPUS if level == "critical"]

# Prompts specifically for edge case testing
EDGE_CASES = [(p, level, c, n) for p, level, c, n in TEST_CORPUS if c == "edge"]

def get_corpus() -> list[tuple[str, str, str, str]]:
    """Return the full test corpus."""
    return TEST_CORPUS

def get_by_category(category: str) -> list[tuple[str, str, str, str]]:
    """Get prompts by category."""
    return [(p, lvl, c, n) for p, lvl, c, n in TEST_CORPUS if c == category]

def get_by_level(level: str) -> list[tuple[str, str, str, str]]:
    """Get prompts by expected level."""
    return [(p, lvl, c, n) for p, lvl, c, n in TEST_CORPUS if lvl == level]

if __name__ == '__main__':
    print(f"Total test cases: {len(TEST_CORPUS)}")
    print(f"  Simple: {len(SIMPLE_PROMPTS)}")
    print(f"  Medium: {len(MEDIUM_PROMPTS)}")
    print(f"  Complex: {len(COMPLEX_PROMPTS)}")
    print(f"  Critical: {len(CRITICAL_PROMPTS)}")
    print(f"  Edge cases: {len(EDGE_CASES)}")
