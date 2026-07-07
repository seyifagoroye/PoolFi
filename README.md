PoolFi
Automated infrastructure for rotating savings groups (Ajo/Esusu) in Nigeria.
PoolFi digitizes the informal peer-to-peer savings system practiced by over 80 million Nigerians. Every group member gets a unique Nomba virtual account number. Contributions are detected automatically via webhooks, reconciled in real time, and payouts are disbursed programmatically to the next member in rotation. No WhatsApp coordination. No handwritten ledgers. No disputed receipts.
Built on the DevCareer x Nomba Hackathon 2026 — Build Track: Virtual Accounts as Infrastructure.
Live Demo
API Base URL: https://poolfi-api.onrender.com
Interactive Documentation: https://poolfi-api.onrender.com/docs
Judges can test all endpoints directly from the /docs interface without any additional tooling.
Test Credentials
To test the API, register a coordinator and a member account using POST /api/auth/register, then use POST /api/auth/login to get a JWT token. Paste the token in the Authorize button on the /docs page to access protected endpoints.
Tech Stack
Backend: Python 3.12, FastAPI
Database: PostgreSQL via SQLAlchemy ORM
Migrations: Alembic
Authentication: JWT via python-jose, bcrypt password hashing
Payment Infrastructure: Nomba API (Virtual Accounts, Webhooks, Transfers, Transactions)
HTTP Client: httpx (async)
Hosting: Render (free tier)
Core Features Built
JWT authentication with role-based access control (Coordinator vs Member)
Group creation and management
Per-member Nomba virtual account provisioning (automatic on member addition)
Webhook handler for real-time payment detection
Payment reconciliation engine with underpayment, overpayment, and duplicate detection
Automated payout disbursement via Nomba Transfers API
Transaction and contribution history endpoints
Rate limiting middleware on auth endpoints
HMAC-SHA256 webhook signature verification
API Endpoints
Authentication:
POST /api/auth/register
POST /api/auth/login
Groups:
POST /api/groups
GET /api/groups
GET /api/groups/{group_id}
Members:
POST /api/groups/{group_id}/members
Webhooks:
POST /webhooks/payment
Payouts:
POST /transfers/trigger-payout
Transactions:
GET /transactions/my-contributions
GET /transactions/group/{group_id}/payouts
Project Structure
poolfi/
auth.py — JWT utilities and role dependencies
database.py — SQLAlchemy engine and session management
models.py — Six database models: User, Group, GroupMember, Contribution, Payout, WebhookEvent
schemas.py — Pydantic validation schemas
nomba_client.py — Async Nomba API client with token caching and auto-refresh
main.py — FastAPI app assembly, middleware, and router registration
routers/
auth.py — Registration and login endpoints
groups.py — Group lifecycle endpoints
members.py — Member enrollment with virtual account provisioning
webhooks.py — Nomba payment webhook handler
transfers.py — Payout disbursement engine
transactions.py — Contribution and payout history
alembic/ — Database migration files
Builder
Promise Oluseyi Fagoroye
200-level Electrical and Electronics Engineering, University of Ibadan
Solo builder, DevCareer x Nomba Hackathon 2026
