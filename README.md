# Student performance analysis

Streamlit dashboard backed by MySQL. One username/password login routes
administrators to account management and teachers to student performance and
data entry. Administrators can create both teacher and additional admin
accounts. Account passwords are stored as salted PBKDF2 hashes.

## MySQL setup

In MySQL Workbench, sign in with your existing root connection and run
`mysql_setup.sql`. It creates the `student_portal` schema, student and
assessment tables, a `portal_accounts` table, and demo data for eight students.
The inserts are safe to run again.

Then run `.streamlit/provision_app_user.local.sql` as root. It creates the
MySQL service account `dav` (or updates its password) and gives it the
SELECT/INSERT/UPDATE privileges the app needs. The app connects as `dav`; this
is a database account, not a teacher login.

The local `.streamlit/secrets.toml` contains the database and app admin
credentials and is ignored by Git. The configured initial admin username is
`admin`; its password is set locally in `.streamlit/secrets.toml`.

Change the initial admin password before sharing or deploying the app. Do not
commit the secrets file.

If you already set up MySQL before, connect as root in Workbench and run
`portal_accounts_setup.sql` to add the account table without rerunning the demo
seed. The admin panel displays a setup message until that table exists.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Sign in on the single login form. The configured initial admin is `admin`;
its password is set locally in `.streamlit/secrets.toml`. Admins can open
**Admin panel** and create either `teacher` or `admin` accounts. The account
role determines access after login. Teachers cannot self-register.
