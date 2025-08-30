import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from blockchain_supabase import BlockchainSupabaseDB
from datetime import datetime
import time

# ✅ Page Configuration - MUST BE FIRST
st.set_page_config(
    page_title="🎓 Blockchain Student DBMS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 👥 USER DATABASE (In production, use secure database)
USERS_DB = {
    # Students (use student_id from database)
    "student1": {"password": "pass123", "role": "student", "student_id": "1", "name": "student1"},
    "student2": {"password": "pass456", "role": "student", "student_id": "2", "name": "student2"},
    "student3": {"password": "pass789", "role": "student", "student_id": "3", "name": "student3"},

    # Teachers (admin access)
    "teacher1": {"password": "teach123", "role": "teacher", "name": "teacher1"},
    "admin": {"password": "admin123", "role": "teacher", "name": "admin"},
}


# 🔄 Initialize Database with Caching
@st.cache_resource
def init_database():
    return BlockchainSupabaseDB()


# 🔐 Authentication Functions
def authenticate_user(username, password, role):
    """Authenticate user credentials"""
    if username in USERS_DB:
        user = USERS_DB[username]
        if user["password"] == password and user["role"] == role:
            return True, user
    return False, None


def login_page():
    """Display login page"""
    st.title("🎓 Blockchain Student DBMS")
    st.subheader("🔐 Please Login to Continue")

    with st.form("login_form"):
        username = st.text_input("👤 Username", placeholder="Enter your username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
        role = st.selectbox("👥 Login as:", ["student", "teacher"])

        submitted = st.form_submit_button("🚀 Login", use_container_width=True)

        if submitted:
            if username and password:
                is_valid, user_data = authenticate_user(username, password, role)

                if is_valid:
                    # Store user session
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.session_state["user_role"] = role
                    st.session_state["user_data"] = user_data

                    st.success(f"✅ Welcome {username}! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid username, password, or role!")
            else:
                st.warning("⚠️ Please enter both username and password")

    # Demo credentials info
    with st.expander("📋 Demo Credentials"):
        st.markdown("""
        **Students:**
        - Username: `student1`, Password: `pass123`
        - Username: `student2`, Password: `pass456`
        - Username: `student3`, Password: `pass789`

        **Teachers/Admin:**
        - Username: `teacher1`, Password: `teach123`
        - Username: `admin`, Password: `admin123`
        """)


def logout_user():
    """Handle user logout"""
    for key in ["logged_in", "username", "user_role", "user_data"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def student_dashboard(db):
    """Student dashboard with limited access"""
    user_data = st.session_state["user_data"]
    student_id = user_data["student_id"]

    st.title(f"👨‍🎓 Student Dashboard - {st.session_state['username']}")

    # Get student's grades
    df = db.get_student_grades_by_id(student_id)

    if not df.empty:
        # Student metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📊 Total Subjects", df['subject'].nunique())
        with col2:
            avg_grade = df['grade'].mode().iloc[0] if not df.empty else "N/A"
            st.metric("🏆 Most Common Grade", avg_grade)
        with col3:
            # Calculate GPA
            grade_points = {'A+': 4.0, 'A': 4.0, 'B+': 3.3, 'B': 3.0, 'C+': 2.3, 'C': 2.0, 'D': 1.0, 'F': 0.0}
            gpa = df['grade'].map(grade_points).mean()
            st.metric("📈 GPA", f"{gpa:.2f}")
        with col4:
            passing_rate = (df['grade'] != 'F').mean() * 100
            st.metric("✅ Pass Rate", f"{passing_rate:.0f}%")

        # Student's grade table
        st.subheader("📋 Your Grades")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Student analytics
        st.subheader("📊 Your Performance Analytics")
        col1, col2 = st.columns(2)

        with col1:
            # Grade distribution
            grade_counts = df['grade'].value_counts()
            fig = px.bar(
                x=grade_counts.index,
                y=grade_counts.values,
                title="Your Grade Distribution",
                labels={'x': 'Grade', 'y': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Subject performance
            subject_counts = df['subject'].value_counts()
            fig = px.pie(
                values=subject_counts.values,
                names=subject_counts.index,
                title="Subjects Taken"
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("📝 No grades found. Please contact your teacher.")


def teacher_dashboard(db):
    """Teacher dashboard with full admin access"""
    st.title(f"👩‍🏫 Teacher Dashboard - {st.session_state['username']}")

    # Teacher navigation
    operation = st.selectbox(
        "Choose Operation:",
        [
            "📝 Add Student Grade",
            "📊 View All Grades",
            "🔍 Search Students",
            "🗑️ Delete Grade",
            "📈 Analytics Dashboard",
            "⛓️ Blockchain Stats",
            "🔄 Reset Database (Admin)"
        ]
    )

    # Execute teacher operations
    if operation == "📝 Add Student Grade":
        st.subheader("📝 Add New Student Grade")

        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                student_name = st.text_input("👤 Student Name")
                student_id = st.text_input("🆔 Student ID")
                subject = st.text_input("📚 Subject")

            with col2:
                grade = st.selectbox("🏆 Grade", ["A+", "A", "B+", "B", "C+", "C", "D", "F"])
                semester = st.selectbox("📅 Semester", ["Spring", "Summer", "Fall", "Winter"])
                remarks = st.text_area("📝 Remarks")

            submitted = st.form_submit_button("💾 Add Grade", use_container_width=True)

            if submitted and student_name and student_id and subject:
                with st.spinner("Adding grade..."):
                    block, res = db.add_student_grade(student_name, student_id, subject, grade, semester, remarks)
                    if block:
                        st.success(f"✅ Grade added successfully! Block #{block['index']}")
                    else:
                        st.error(f"❌ Error: {res}")

    elif operation == "📊 View All Grades":
        st.subheader("📊 All Student Grades")
        df = db.get_all_grades_sql()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No grades found.")

    elif operation == "🔍 Search Students":
        st.subheader("🔍 Search Students")
        search_term = st.text_input("Search by name, ID, or subject:")
        if search_term:
            df = db.search_students_sql(search_term)
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("No results found.")

    elif operation == "🗑️ Delete Grade":
        st.subheader("🗑️ Delete Student Grade")
        df = db.get_all_grades_sql()
        if not df.empty:
            st.dataframe(df[['id', 'student_name', 'student_id', 'subject', 'grade']], hide_index=True)

            record_id = st.number_input("Record ID to delete:", min_value=1, step=1)
            reason = st.text_area("Reason for deletion:")

            if st.button("🗑️ Delete Record") and record_id:
                block, res = db.delete_student_grade(record_id, reason)
                if block:
                    st.success(f"✅ Record deleted! Block #{block['index']}")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {res}")

    elif operation == "📈 Analytics Dashboard":
        st.subheader("📈 Analytics Dashboard")
        df = db.get_all_grades_sql()
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                grade_counts = df['grade'].value_counts()
                fig = px.bar(x=grade_counts.index, y=grade_counts.values, title="Grade Distribution")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                subject_counts = df['subject'].value_counts()
                fig = px.pie(values=subject_counts.values, names=subject_counts.index, title="Subject Distribution")
                st.plotly_chart(fig, use_container_width=True)

    elif operation == "⛓️ Blockchain Stats":
        st.subheader("⛓️ Blockchain Statistics")
        stats = db.get_blockchain_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("SQL Records", stats['sql_count'])
        with col2:
            st.metric("Blockchain Blocks", stats['blockchain_count'])

        if st.button("🔍 Verify Blockchain"):
            is_valid, message = db.verify_blockchain_integrity()
            if is_valid:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")

    elif operation == "🔄 Reset Database (Admin)":
        st.subheader("🔄 Reset Database")
        st.warning("⚠️ This will delete ALL data permanently!")

        confirm = st.text_input("Type 'RESET' to confirm:")
        if confirm == "RESET" and st.button("🚨 RESET DATABASE"):
            success, message = db.reset_database()
            if success:
                st.success("✅ Database reset successfully!")
                st.rerun()
            else:
                st.error(f"❌ {message}")


# 🚀 MAIN APPLICATION
def main():
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Initialize database
    try:
        db = init_database()
    except Exception as e:
        st.error(f"❌ Database Error: {str(e)}")
        return

    # Check authentication
    if not st.session_state["logged_in"]:
        login_page()
    else:
        # Show logout button in sidebar
        st.sidebar.title("Navigation")
        st.sidebar.write(f"**👤 Logged in as:** {st.session_state['username']}")
        st.sidebar.write(f"**👥 Role:** {st.session_state['user_role'].title()}")

        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout_user()

        # Route to appropriate dashboard
        if st.session_state["user_role"] == "student":
            student_dashboard(db)
        elif st.session_state["user_role"] == "teacher":
            teacher_dashboard(db)


# Run the application
if __name__ == "__main__":
    main()
