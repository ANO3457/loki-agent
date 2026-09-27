# LOKI Business Rules & Assertions
Define the business expectations and rules that LOKI should assert when attacking your app.
LOKI evaluates these criteria during stress testing and exploratory sessions.
## Critical Business Assertions
- Action buttons must disable upon click to prevent concurrent double-submissions.
- Unhandled JavaScript exceptions in the browser console are classified as critical failures.
- Forms must display contextual error banners rather than blank pages or unstyled crash screens.
- Financial transactions (payments, transfers) must have deterministic server idempotency locks.
