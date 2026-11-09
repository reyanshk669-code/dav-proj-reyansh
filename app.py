import hashlib
import hmac
import os
from pathlib import Path
import secrets

import mysql.connector
import pandas as pd
import streamlit as st

PASSWORD_ITERATIONS = 310_000


def get_mysql_config():
    secret_paths = (
        Path(__file__).resolve().parent / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    )
    secret_config = (
        st.secrets.get("mysql", {})
        if any(path.is_file() for path in secret_paths)
        else {}
    )
    return {
        "host": secret_config.get("host") or os.getenv("MYSQL_HOST", "localhost"),
        "port": int(secret_config.get("port") or os.getenv("MYSQL_PORT", "3306")),
        "database": secret_config.get("database")
        or os.getenv("MYSQL_DATABASE", "student_portal"),
        "user": secret_config.get("user") or os.getenv("MYSQL_USER", ""),
        "password": secret_config.get("password") or os.getenv("MYSQL_PASSWORD", ""),
    }


def get_admin_credentials():
    secret_paths = (
        Path(__file__).resolve().parent / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    )
    auth_config = (
        st.secrets.get("auth", {})
        if any(path.is_file() for path in secret_paths)
        else {}
    )
    return {
        "username": auth_config.get("admin_username")
        or os.getenv("ADMIN_USERNAME", ""),
        "password": auth_config.get("admin_password")
        or os.getenv("ADMIN_PASSWORD", ""),
    }


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (AttributeError, TypeError, ValueError):
        return False


def authenticate_account(connection, username, password):
    admin_credentials = get_admin_credentials()
    if (
        admin_credentials["username"]
        and admin_credentials["password"]
        and hmac.compare_digest(
            username.encode("utf-8"),
            admin_credentials["username"].encode("utf-8"),
        )
        and hmac.compare_digest(
            password.encode("utf-8"),
            admin_credentials["password"].encode("utf-8"),
        )
    ):
        return {"role": "admin", "username": admin_credentials["username"]}

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT username, password_hash, role
            FROM portal_accounts
            WHERE username = %s
            """,
            (username,),
        )
        account = cursor.fetchone()
        if (
            account
            and account["role"] in {"admin", "teacher"}
            and verify_password(password, account["password_hash"])
        ):
            return {"role": account["role"], "username": account["username"]}
        return None
    finally:
        cursor.close()


def list_accounts(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT username, role, created_by, created_at
            FROM portal_accounts
            ORDER BY created_at DESC
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def accounts_table_exists(connection):
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE %s", ("portal_accounts",))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def create_account(connection, username, password, role, created_by):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO portal_accounts (username, password_hash, role, created_by)
            VALUES (%s, %s, %s, %s)
            """,
            (username, hash_password(password), role, created_by),
        )
        connection.commit()
        return True
    except mysql.connector.IntegrityError:
        connection.rollback()
        return False
    finally:
        cursor.close()


def load_results(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                s.full_name,
                s.course,
                s.year_of_study,
                r.subject,
                r.assessment_name,
                r.marks_obtained,
                r.total_marks,
                r.assessment_date
            FROM students AS s
            JOIN student_results AS r ON r.student_id = s.student_id
            ORDER BY s.full_name, r.subject, r.assessment_name
            """
        )
        return pd.DataFrame(cursor.fetchall())
    finally:
        cursor.close()


def list_students(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT student_id, full_name, email, course, year_of_study
            FROM students
            ORDER BY full_name
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def add_student(connection, full_name, email, course, year_of_study):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO students (full_name, email, course, year_of_study)
            VALUES (%s, %s, %s, %s)
            """,
            (full_name, email, course, year_of_study),
        )
        connection.commit()
        return True
    except mysql.connector.IntegrityError:
        connection.rollback()
        return False
    finally:
        cursor.close()


def save_assessment(
    connection,
    student_id,
    subject,
    assessment_name,
    marks_obtained,
    total_marks,
    assessment_date,
):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO student_results (
                student_id, subject, assessment_name, marks_obtained,
                total_marks, assessment_date
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                marks_obtained = %s,
                total_marks = %s,
                assessment_date = %s
            """,
            (
                student_id,
                subject,
                assessment_name,
                marks_obtained,
                total_marks,
                assessment_date,
                marks_obtained,
                total_marks,
                assessment_date,
            ),
        )
        connection.commit()
    except mysql.connector.Error:
        connection.rollback()
        raise
    finally:
        cursor.close()


def show_data_entry(connection):
    st.subheader("Add student")
    with st.form("add_student_form", clear_on_submit=True):
        full_name = st.text_input("Student name")
        email = st.text_input("Student email")
        course = st.text_input("Course")
        year_of_study = st.number_input(
            "Year of study", min_value=1, max_value=8, value=1
        )
        submitted = st.form_submit_button("Save student")
    if submitted:
        if not full_name.strip() or not email.strip() or not course.strip():
            st.error("Enter the student's name, email, and course.")
        elif add_student(
            connection,
            full_name.strip(),
            email.strip(),
            course.strip(),
            year_of_study,
        ):
            st.success("Student saved.")
            st.rerun()
        else:
            st.error("A student with that email already exists.")

    st.divider()
    st.subheader("Add or update an assessment score")
    students = list_students(connection)
    if not students:
        st.info("Save a student before adding assessment scores.")
        return

    student_by_id = {student["student_id"]: student for student in students}
    with st.form("assessment_form", clear_on_submit=True):
        student_id = st.selectbox(
            "Student",
            options=list(student_by_id),
            format_func=lambda value: (
                f"{student_by_id[value]['full_name']} — "
                f"{student_by_id[value]['course']}"
            ),
        )
        subject = st.text_input("Subject")
        assessment_name = st.text_input("Assessment name", value="Midterm")
        marks_obtained = st.number_input(
            "Marks earned", min_value=0.0, value=0.0, step=0.5
        )
        total_marks = st.number_input(
            "Total marks", min_value=0.5, value=100.0, step=0.5
        )
        assessment_date = st.date_input("Assessment date")
        submitted = st.form_submit_button("Save assessment")

    if submitted:
        if not subject.strip() or not assessment_name.strip():
            st.error("Enter both a subject and an assessment name.")
        elif marks_obtained > total_marks:
            st.error("Marks earned cannot be greater than total marks.")
        else:
            save_assessment(
                connection,
                student_id,
                subject.strip(),
                assessment_name.strip(),
                marks_obtained,
                total_marks,
                assessment_date,
            )
            st.success("Assessment saved. A matching student/subject/assessment was updated.")
            st.rerun()


def show_analysis(connection):
    results = load_results(connection)
    if results.empty:
        st.info("No assessment results yet. Add a student and assessment in the Data entry tab.")
        return

    results["marks_obtained"] = results["marks_obtained"].astype(float)
    results["total_marks"] = results["total_marks"].astype(float)
    results["score_percent"] = (
        results["marks_obtained"] / results["total_marks"] * 100
    )

    with st.sidebar:
        st.header("Filters")
        courses = ["All courses", *sorted(results["course"].unique())]
        selected_course = st.selectbox("Course", courses)
        subjects = ["All subjects", *sorted(results["subject"].unique())]
        selected_subject = st.selectbox("Subject", subjects)
        pass_mark = st.slider("Pass mark (%)", min_value=0, max_value=100, value=50)

    filtered_results = results
    if selected_course != "All courses":
        filtered_results = filtered_results[
            filtered_results["course"] == selected_course
        ]
    if selected_subject != "All subjects":
        filtered_results = filtered_results[
            filtered_results["subject"] == selected_subject
        ]

    student_averages = (
        filtered_results.groupby(
            ["student_id", "full_name", "course", "year_of_study"],
            as_index=False,
        )["score_percent"]
        .mean()
        .rename(columns={"score_percent": "average_score"})
    )

    total_students = len(student_averages)
    average_score = filtered_results["score_percent"].mean()
    pass_rate = (
        filtered_results["score_percent"].ge(pass_mark).mean() * 100
    )

    first, second, third, fourth = st.columns(4)
    first.metric("Students", total_students)
    second.metric("Assessments", len(filtered_results))
    third.metric("Average score", f"{average_score:.1f}%")
    fourth.metric("Pass rate", f"{pass_rate:.1f}%")

    st.subheader("Average score by course")
    course_averages = (
        filtered_results.groupby("course", as_index=False)["score_percent"]
        .mean()
        .rename(columns={"score_percent": "Average score (%)"})
        .sort_values("Average score (%)", ascending=False)
    )
    st.bar_chart(
        course_averages,
        x="course",
        y="Average score (%)",
        y_label="Average score (%)",
        alt="Average assessment scores by course",
    )

    st.subheader("Average score by subject")
    subject_averages = (
        filtered_results.groupby("subject", as_index=False)["score_percent"]
        .mean()
        .rename(columns={"score_percent": "Average score (%)"})
        .sort_values("Average score (%)", ascending=False)
    )
    st.bar_chart(
        subject_averages,
        x="subject",
        y="Average score (%)",
        y_label="Average score (%)",
        alt="Average assessment scores by subject",
    )

    st.subheader("Student performance")
    student_averages["average_score"] = student_averages["average_score"].round(1)
    student_averages = student_averages.rename(
        columns={
            "full_name": "Student",
            "course": "Course",
            "year_of_study": "Year",
            "average_score": "Average score (%)",
        }
    ).drop(columns=["student_id"])
    st.dataframe(
        student_averages.sort_values("Average score (%)", ascending=False),
        hide_index=True,
        alt="Average assessment scores by student",
    )

    with st.expander("Assessment records"):
        detail_columns = [
            "full_name",
            "course",
            "subject",
            "assessment_name",
            "marks_obtained",
            "total_marks",
            "score_percent",
            "assessment_date",
        ]
        details = filtered_results[detail_columns].copy()
        details["score_percent"] = details["score_percent"].round(1)
        st.dataframe(
            details.rename(
                columns={
                    "full_name": "Student",
                    "course": "Course",
                    "subject": "Subject",
                    "assessment_name": "Assessment",
                    "marks_obtained": "Marks",
                    "total_marks": "Total marks",
                    "score_percent": "Score (%)",
                    "assessment_date": "Date",
                }
            ),
            hide_index=True,
            alt="Filtered student assessment records",
        )


def show_dashboard(connection):
    st.title("Student performance analysis")
    user = st.session_state["auth_user"]
    st.caption(f"Signed in as {user['username']} ({user['role']}).")

    with st.sidebar:
        if st.button("Log out"):
            del st.session_state["auth_user"]
            st.rerun()

    if user["role"] == "admin":
        admin_tab, analysis_tab, data_entry_tab = st.tabs(
            ["Admin panel", "Analysis", "Data entry"]
        )
        with admin_tab:
            show_admin_panel(connection, user["username"])
        with analysis_tab:
            show_analysis(connection)
        with data_entry_tab:
            show_data_entry(connection)
    else:
        analysis_tab, data_entry_tab = st.tabs(["Analysis", "Data entry"])
        with analysis_tab:
            show_analysis(connection)
        with data_entry_tab:
            show_data_entry(connection)


def show_admin_panel(connection, admin_username):
    st.subheader("Create account")
    st.caption("Administrators can create teacher accounts and additional admins.")
    if not accounts_table_exists(connection):
        st.error("The application accounts table has not been created in MySQL yet.")
        st.info(
            "In Workbench, connect as root and run "
            "portal_accounts_setup.sql. Then refresh this page."
        )
        return

    with st.form("create_account_form", clear_on_submit=True):
        username = st.text_input("Username", key="account_username")
        role = st.selectbox(
            "Account type", ["teacher", "admin"], key="account_role"
        )
        password = st.text_input(
            "Password", type="password", key="account_password"
        )
        confirm_password = st.text_input(
            "Confirm password", type="password", key="account_confirm_password"
        )
        submitted = st.form_submit_button("Create account")

    if submitted:
        clean_username = username.strip()
        if not clean_username or not password:
            st.error("Enter a username and password.")
        elif len(clean_username) > 80:
            st.error("Usernames must be 80 characters or fewer.")
        elif clean_username.casefold() == admin_username.casefold():
            st.error("That username is already used by the configured administrator.")
        elif role not in {"admin", "teacher"}:
            st.error("Choose a valid account type.")
        elif len(password) < 8:
            st.error("Use a password with at least 8 characters.")
        elif password != confirm_password:
            st.error("The passwords do not match.")
        elif create_account(
            connection, clean_username, password, role, admin_username
        ):
            st.success(f"{role.title()} account '{clean_username}' created.")
        else:
            st.error("That username already exists.")

    st.divider()
    st.subheader("Application accounts")
    accounts = list_accounts(connection)
    if accounts:
        st.dataframe(
            accounts,
            hide_index=True,
            alt="Application accounts created by administrators",
        )
    else:
        st.info("No additional accounts have been created yet.")


def show_login(connection):
    st.title("Student performance analysis")
    st.caption("Sign in with your account.")
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        account = authenticate_account(connection, username.strip(), password)
        if account:
            st.session_state["auth_user"] = account
            st.rerun()
        st.error("Username or password is incorrect.")


def main():
    st.set_page_config(page_title="Student performance analysis", layout="wide")
    config = get_mysql_config()
    if not config["user"] or not config["password"]:
        st.error(
            "MySQL connection credentials are missing. Configure the [mysql] "
            "section in .streamlit/secrets.toml."
        )
        st.stop()

    try:
        connection = mysql.connector.connect(**config)
    except mysql.connector.Error as error:
        st.error(f"Could not connect to MySQL: {error}")
        st.info(
            "In Workbench, connect as root, run mysql_setup.sql, then run "
            ".streamlit/provision_app_user.local.sql. Refresh this page after setup."
        )
        st.stop()

    try:
        user = st.session_state.get("auth_user")
        if (
            isinstance(user, dict)
            and user.get("role") in {"admin", "teacher"}
            and isinstance(user.get("username"), str)
        ):
            show_dashboard(connection)
        else:
            st.session_state.pop("auth_user", None)
            show_login(connection)
    except mysql.connector.Error as error:
        if error.errno == 1146:
            st.error(
                "The portal_accounts table is missing. In MySQL Workbench, "
                "connect as root and run portal_accounts_setup.sql."
            )
        else:
            st.error(f"MySQL query failed: {error}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
