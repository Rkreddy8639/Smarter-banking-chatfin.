# Smarter Banking – Chatfin

A B.Tech academic project: a simulated digital banking web app built with Flask, MySQL, Bootstrap and a transparent rule-based fraud screening module.

## Features
- Customer registration and login (Werkzeug password hashing)
- Demo account with ₹10,000 starting balance
- Account dashboard and transaction history
- Transfers between Chatfin demo accounts
- Basic fraud screening and admin fraud-alert view
- Rule-based banking FAQ chatbot
- Database health endpoint at `/api/health`

> **Important:** This is an educational simulation. It is not connected to banks, payment rails or real money. Do not enter real banking credentials or personal financial data. The fraud screening is illustrative and must not be represented as production-grade machine learning.

## Requirements
- Python 3.10+
- MySQL 8+
- Git (optional)

## Local setup (Windows PowerShell)
1. Install MySQL Server and MySQL Workbench.
2. Create a database and user:
   - Open MySQL Workbench and run `database/schema.sql`.
   - Or create your own database/user and update `DATABASE_URL`.
3. Open this project folder in VS Code.
4. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
5. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
6. Copy `.env.example` to `.env`, then update the MySQL username/password and set a long random `SECRET_KEY`.
7. Run:
   ```powershell
   python app.py
   ```
8. Open `http://127.0.0.1:5000`.

## First use
- Register two separate customer accounts using different email addresses.
- Copy the recipient's account number from the recipient's dashboard.
- Sign in to the sender account and use Transfer.
- Try a transfer of ₹25,000 or more to see the demo fraud-review behavior.

## Admin setup
For a classroom demo only, register an account, then use MySQL Workbench:
```sql
UPDATE users SET role='admin' WHERE email='your-email@example.com';
```
Log out and back in, then open `/admin`. Never expose an admin account with a weak password.

## Tests
```powershell
pytest -q
```

## Deployment (Render + managed MySQL)
1. Push the project to a private or public GitHub repository. Do not commit `.env`.
2. Create a MySQL database with a managed provider that permits connections from your app host. Copy its connection details.
3. In Render, create a **Web Service** connected to the GitHub repository.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Add environment variables in Render:
   - `SECRET_KEY`: long random secret
   - `DATABASE_URL`: `mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE?charset=utf8mb4`
   - `FLASK_DEBUG`: `0`
7. Deploy and test `https://YOUR-SERVICE.onrender.com/api/health`.
8. Register test accounts and validate transfers.

Database providers and Render plan/pricing/availability can change. Check the provider's current MySQL support and networking rules before creating the database. Do not assume a free tier is permanent.

## Suggested demo flow
1. Register sender and recipient accounts.
2. Log in as sender and show the dashboard.
3. Transfer ₹500 to recipient.
4. Show sender debit and recipient credit in transaction history.
5. Trigger fraud review using a ₹25,000+ demo transfer.
6. Show the alert from an admin account.
7. Ask the chatbot: "How do I transfer money?"

## Project architecture
Browser (Bootstrap templates + JavaScript) → Flask routes → SQLAlchemy → MySQL.
The fraud screening module is called before demo transfers are posted. It uses simple, explainable rules.

## Limitations and future improvements
- Add CSRF protection, rate limiting, password reset, email verification and audit logging.
- Add a proper service layer and database migrations (Alembic).
- Use a labelled, representative dataset and evaluate precision, recall, F1 and false-positive rate before claiming ML fraud detection.
- Add two-factor authentication and robust transfer idempotency.
- For production financial software, use a regulated payment/banking provider and independent security review.
