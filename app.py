from flask import (Flask, request, jsonify, render_template, redirect, session, flash)
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ---------- DATABASE PATH ----------
DB_PATH = os.path.join(os.path.dirname(__file__), "tickets.db")

# ---------- INIT DATABASE ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """)

    # Tickets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    description TEXT,
    category TEXT,
    priority TEXT,
    status TEXT,
    assigned_to INTEGER,
    admin_response TEXT
    )
    """)

    # Default admin
    cursor.execute("""
    INSERT OR IGNORE INTO users
    (username, password, role)
    VALUES (?, ?, ?)
    """, (
        "admin",
        "admin123",
        "admin"
    ))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS technicians(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            specialization TEXT,
            username TEXT UNIQUE,
            password TEXT
        )
        """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_base(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    title TEXT,

    content TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT,
    is_read INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()
# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        selected_role = request.form["role"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, role
            FROM users
            WHERE username=? AND password=? AND role=?
        """, (username, password, selected_role))

        user = cursor.fetchone()

        if user:

            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[2]

            # Technician login
            if user[2] == "technician":

                cursor.execute("""
                    SELECT id, name
                    FROM technicians
                    WHERE username=?
                """, (username,))

                technician = cursor.fetchone()

                if technician:
                    session["technician_id"] = technician[0]
                    session["technician_name"] = technician[1]

            conn.close()

            if user[2] == "admin":
                return redirect("/dashboard")
            elif user[2] == "technician":
                return redirect("/technician-dashboard")
            else:
                return redirect("/user-dashboard")

        conn.close()

        return render_template(
            "login.html",
            error="Invalid username, password, or role."
        )

    return render_template("login.html")

# ---------- TECHNICIAN LOGIN ----------
@app.route("/technician-login", methods=["GET", "POST"])
def technician_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name
            FROM technicians
            WHERE username=? AND password=?
        """, (username, password))

        tech = cursor.fetchone()

        conn.close()

        if tech:
            session.clear()
            session["technician_id"] = tech[0]
            session["technician_name"] = tech[1]
            session["role"] = "technician"

            return redirect("/technician-dashboard")

        return "Invalid Username or Password"

    return render_template("technician_login.html")

# ---------- user dashboard ----------
@app.route("/user-dashboard")
def user_dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total Tickets
    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE user_id = ?
    """, (session["user_id"],))
    total_tickets = cursor.fetchone()[0]

    # Open Tickets
    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE user_id = ?
        AND status = 'Open'
    """, (session["user_id"],))
    open_tickets = cursor.fetchone()[0]

    # In Progress
    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE user_id = ?
        AND status = 'In Progress'
    """, (session["user_id"],))
    progress_tickets = cursor.fetchone()[0]

    # Resolved
    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE user_id = ?
        AND status = 'Resolved'
    """, (session["user_id"],))
    resolved_tickets = cursor.fetchone()[0]

    # Recent Tickets
    cursor.execute("""
        SELECT *
        FROM tickets
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
    """, (session["user_id"],))

    recent_tickets = cursor.fetchall()

    conn.close()

    return render_template(
        "user_dashboard.html",
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        progress_tickets=progress_tickets,
        resolved_tickets=resolved_tickets,
        recent_tickets=recent_tickets
    )
# ---------- TECHNICIAN DASHBOARD ----------
@app.route("/technician-dashboard")
def technician_dashboard():

    # Authentication
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "technician":
        return "Access Denied"
    
    print("Role:", session.get("role"))
    print("Technician ID:", session.get("technician_id"))
    print("Technician Name:", session.get("technician_name"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get technician information from logged-in username
    cursor.execute("""
        SELECT
            id,
            name
        FROM technicians
        WHERE username = ?
    """, (session["username"],))

    technician = cursor.fetchone()

    if not technician:
        conn.close()
        return "Technician account not found."

    tech_id = technician[0]
    technician_name = technician[1]

    # -----------------------
    # Dashboard Statistics
    # -----------------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to = ?
    """, (tech_id,))
    total_tickets = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to = ?
        AND status = 'Open'
    """, (tech_id,))
    open_tickets = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to = ?
        AND status = 'In Progress'
    """, (tech_id,))
    progress_tickets = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to = ?
        AND status = 'Resolved'
    """, (tech_id,))
    resolved_tickets = cursor.fetchone()[0]

    # -----------------------
    # Assigned Tickets
    # -----------------------

    cursor.execute("""
        SELECT
            id,
            title,
            description,
            category,
            priority,
            status,
            COALESCE(technician_note, '')
        FROM tickets
        WHERE assigned_to = ?
        ORDER BY id DESC
    """, (tech_id,))

    tickets = cursor.fetchall()

    conn.close()

    return render_template(
        "technician_dashboard.html",
        technician_name=technician_name,
        tickets=tickets,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        progress_tickets=progress_tickets,
        resolved_tickets=resolved_tickets
    )
# ---------- TECHNICIAN UPDATE STATUS ----------
@app.route("/technician-update/<int:ticket_id>/<status>")
def technician_update(ticket_id, status):

    if session.get("role") != "technician":
        return redirect("/technician-login")

    tech_id = session["technician_id"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET status=?
        WHERE id=?
        AND assigned_to=?
    """, (
        status,
        ticket_id,
        tech_id
    ))

    conn.commit()
    conn.close()

    return redirect("/technician-dashboard")
# ---------- TECHNICIAN NOTE ----------
@app.route("/technician-note/<int:ticket_id>", methods=["POST"])
def technician_note(ticket_id):

    if session.get("role") != "technician":
        return redirect("/technician-login")

    note = request.form["technician_note"]
    tech_id = session["technician_id"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET technician_note=?
        WHERE id=?
        AND assigned_to=?
    """, (
        note,
        ticket_id,
        tech_id
    ))

    conn.commit()
    conn.close()

    return redirect("/technician-dashboard")
# ---------- register ----------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:

            cursor.execute("""
                INSERT INTO users
                (username, password, role)
                VALUES (?, ?, ?)
            """, (
                username,
                password,
                "user"
            ))

            conn.commit()

            return redirect("/login")

        except sqlite3.IntegrityError:
            return "Username already exists"

        finally:
            conn.close()

    return render_template("register.html")

# ---------- Logout Route ----------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

#-----knowledge-base-----

@app.route("/knowledge-base")
def knowledge_base():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM knowledge_base
    """)

    articles = cursor.fetchall()

    conn.close()

    return render_template(
        "knowledge_base.html",
        articles=articles
    )
#---------knowledge-base---------
@app.route("/admin-knowledge-base")
def admin_knowledge_base():

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM knowledge_base
    """)

    articles = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_knowledge_base.html",
        articles=articles
    )
#-------Knowledge Base Article-----
@app.route("/add-article", methods=["POST"])
def add_article():

    if session.get("role") != "admin":
        return "Access Denied"

    title = request.form.get("title")
    content = request.form.get("content")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO knowledge_base
        (title, content)
        VALUES (?, ?)
    """, (
        title,
        content
    ))

    conn.commit()
    conn.close()

    return redirect("/admin-knowledge-base")

# ---------- AI ANALYSIS ENGINE ----------
def analyze_ticket(message):
    msg = message.lower()

    if any(word in msg for word in [
        "down", "critical", "urgent", "cannot", "can't",
        "not working", "error", "failed"
    ]):
        priority = "High"
    elif any(word in msg for word in [
        "slow", "lag", "delay", "issue"
    ]):
        priority = "Medium"
    else:
        priority = "Low"

    if any(word in msg for word in [
        "internet", "network", "wifi", "connection", "offline"
    ]):
        category = "Network"
    elif any(word in msg for word in [
        "password", "login", "signin", "sign in",
        "account", "authentication", "access"
    ]):
        category = "Authentication"
    elif any(word in msg for word in [
        "slow", "lag", "freeze", "performance", "stuck"
    ]):
        category = "Performance"
    else:
        category = "General"

    return category, priority

# ---------- AI AUTO TECHNICIAN ASSIGNMENT ----------
def auto_assign_technician(category):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM technicians
        WHERE specialization = ?
        ORDER BY RANDOM()
        LIMIT 1
    """, (category,))

    technician = cursor.fetchone()

    conn.close()

    if technician:
        return technician[0]

    return None

# ---------- AUTO TICKET ----------
def create_ticket_auto(user_id, title, description):

    # AI analyzes the ticket
    category, priority = analyze_ticket(
        f"{title} {description}"
    )

    # AI assigns the best technician
    assigned_to = auto_assign_technician(category)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tickets
        (
            user_id,
            title,
            description,
            category,
            priority,
            status,
            assigned_to,
            admin_response
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        title,
        description,
        category,
        priority,
        "Open",
        assigned_to,
        None
    ))

    conn.commit()

    # Create admin notification
    create_notification(
        f"New ticket created: {title}"
    )

    conn.close()

#---Create Notification Helper--
def create_notification(message):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO notifications(message)
        VALUES(?)
    """, (message,))

    conn.commit()
    conn.close()

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- MANUAL TICKET ----------
@app.route("/ticket", methods=["POST"])
def create_ticket():

    if "user_id" not in session:
        return redirect("/login")

    title = request.form.get("title", "")
    description = request.form.get("description", "")

    user_id = session.get("user_id")

    # AI analyzes ticket
    category, priority = analyze_ticket(
        f"{title} {description}"
    )

    # AI automatically assigns technician
    assigned_to = auto_assign_technician(category)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tickets
        (
            user_id,
            title,
            description,
            category,
            priority,
            status,
            assigned_to,
            admin_response
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        title,
        description,
        category,
        priority,
        "Open",
        assigned_to,
        None
    ))

    conn.commit()

    # Create notification for admin
    create_notification(
        f"New ticket submitted: {title}"
    )

    conn.close()

    return redirect("/user-dashboard")

# ---------- GET TICKETS API ----------
@app.route("/tickets")
def get_tickets():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            title,
            description,
            category,
            priority,
            status,
            admin_response
        FROM tickets
    """)

    tickets = cursor.fetchall()
    conn.close()

    return jsonify(tickets)

#--------my tickets------
@app.route("/my-tickets")
def my_tickets():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            title,
            description,
            category,
            priority,
            status,
            admin_response
        FROM tickets
        WHERE user_id = ?
    """, (session["user_id"],))

    tickets = cursor.fetchall()

    conn.close()

    return render_template(
        "my_tickets.html",
        tickets=tickets
    )

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():

    # Authentication
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # -------------------
    # Dashboard Statistics
    # -------------------

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    open_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='In Progress'")
    in_progress_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Resolved'")
    resolved_tickets = cursor.fetchone()[0]

    # -------------------
    # Search + Filter + Pagination
    # -------------------

    status_filter = request.args.get("status", "")
    search = request.args.get("search", "")

    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    # Main query
    query = """
    SELECT
            t.id,
            t.title,
            t.description,
            t.category,
            t.priority,
            t.status,
            t.admin_response,
            COALESCE(tech.name, 'Unassigned') AS technician_name,
            t.technician_note
        FROM tickets t
        LEFT JOIN technicians tech
        ON t.assigned_to = tech.id
        WHERE 1=1
    """
    params = []

    # Status filter
    if status_filter:
        query += " AND t.status = ?"
        params.append(status_filter)
    # Search filter
    if search:
        query += """
    AND (
        t.title LIKE ?
        OR t.description LIKE ?
        OR t.category LIKE ?
    )
    """

        params.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])

    # Count query (for pagination)
    count_query = """
    SELECT COUNT(*)
    FROM tickets t
    LEFT JOIN technicians tech
    ON t.assigned_to = tech.id
    WHERE 1=1
    """

    count_params = []

    if status_filter:
        count_query += " AND t.status = ?"
        count_params.append(status_filter)

    if search:
        count_query += """
        AND (
            t.title LIKE ?
            OR t.description LIKE ?
            OR t.category LIKE ?
        )
        """
        count_params.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])

    cursor.execute(count_query, count_params)
    total_records = cursor.fetchone()[0]

    # Add Pagination
    query += """
    ORDER BY t.id DESC
    LIMIT ? OFFSET ?
    """

    params.extend([per_page, offset])

    cursor.execute(query, params)
    tickets = cursor.fetchall()

    has_next = (page * per_page) < total_records

    print("Tickets Found:", len(tickets))
    print(tickets)

    conn.close()

    return render_template(
        "dashboard.html",
        tickets=tickets,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_tickets=resolved_tickets,
        admin_name=session.get("username"),
        page=page,
        has_next=has_next
    )

# ---------- ADMIN USERS ----------
@app.route("/admin-users")
def admin_users():

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, role
        FROM users
    """)

    users = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_users.html",
        users=users
    )
#-------Notifications Page-------
@app.route("/admin-notifications")
def admin_notifications():

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM notifications
        ORDER BY id DESC
    """)

    notifications = cursor.fetchall()

    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications
    )
#---admin-analytics------------
@app.route("/admin-analytics")
def admin_analytics():

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]

    cursor.execute("""
        SELECT category,
               COUNT(*)
        FROM tickets
        GROUP BY category
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)

    category_data = cursor.fetchone()

    top_category = (
        category_data[0]
        if category_data else "N/A"
    )

    conn.close()

    return render_template(
        "analytics.html",
        total_users=total_users,
        total_tickets=total_tickets,
        top_category=top_category
    )

#-------analytics--------
@app.route("/analytics")
def analytics():

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category, COUNT(*)
        FROM tickets
        GROUP BY category
    """)

    category_stats = cursor.fetchall()

    conn.close()

    return render_template(
        "analytics.html",
        category_stats=category_stats
    )

# ---------- CHAT API ----------
@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    user_message = data.get("message", "")
    user_id = session.get("user_id")

    ticket_created = False

    # ---------------- NETWORK ----------------

    if any(word in user_message.lower() for word in [
        "internet", "network", "wifi",
        "connection", "offline"
    ]):

        response = """
🌐 Network issue detected.

Suggested fixes:

• Restart your router
• Reconnect to WiFi
• Check network cables
• Run Windows Network Troubleshooter
"""

        if user_id:
            create_ticket_auto(
                user_id,
                "Network Issue",
                user_message
            )
            ticket_created = True

    # ---------------- AUTHENTICATION ----------------

    elif any(word in user_message.lower() for word in [
        "password",
        "login",
        "signin",
        "account",
        "authentication",
        "access"
    ]):

        response = """
🔐 Authentication issue detected.

Suggested fixes:

• Reset your password
• Verify your username
• Clear browser cache
• Try another browser
"""

        if user_id:
            create_ticket_auto(
                user_id,
                "Authentication Issue",
                user_message
            )
            ticket_created = True

    # ---------------- PERFORMANCE ----------------

    elif any(word in user_message.lower() for word in [
        "slow",
        "lag",
        "freeze",
        "stuck",
        "performance"
    ]):

        response = """
⚡ Performance issue detected.

Suggested fixes:

• Restart your device
• Close unused programs
• Check disk space
• Run antivirus scan
"""

        if user_id:
            create_ticket_auto(
                user_id,
                "Performance Issue",
                user_message
            )
            ticket_created = True

    # ---------------- GENERAL ----------------

    else:

        response = """
💬 Support request received.

Please provide more details so I can better assist you.

Examples:

• My internet is down
• I forgot my password
• My computer is very slow
"""

        if user_id:
            create_ticket_auto(
                user_id,
                "General Support Request",
                user_message
            )
            ticket_created = True

    # ---------------- FINAL MESSAGE ----------------

    if user_id:

        if ticket_created:
            response += """

✅ A support ticket has been created automatically.

You can track it under "My Tickets".
"""

    else:

        response += """

👤 You are currently using Guest Support.

Login or Register to create and track support tickets.
"""

    return jsonify({
        "response": response
    })

# ---------- CHAT UI ----------

@app.route("/chat-ui")
def chat_ui():
    return render_template("chat.html")

# ---------- ADMIN REPLY ----------
@app.route("/reply-ticket/<int:ticket_id>", methods=["POST"])
def reply_ticket(ticket_id):

    admin_response = request.form.get("admin_response")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET admin_response = ?, status = ?
        WHERE id = ?
    """, (
        admin_response,
        "Resolved",
        ticket_id
    ))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------- UPDATE STATUS ----------
@app.route("/update-ticket/<int:ticket_id>/<status>")
def update_ticket(ticket_id, status):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET status = ?
        WHERE id = ?
    """, (
        status,
        ticket_id
    ))

    conn.commit()
    conn.close()

    return redirect("/dashboard")
# =====================================================
# TECHNICIAN MANAGEMENT

@app.route("/technicians")
def technicians():

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        tech.id,
        tech.name,
        tech.email,
        tech.username,
        tech.password,
        tech.specialization,
        COUNT(t.id) AS assigned_count
    FROM technicians AS tech
    LEFT JOIN tickets AS t
        ON tech.id = t.assigned_to
    GROUP BY
        tech.id,
        tech.name,
        tech.email,
        tech.username,
        tech.password,
        tech.specialization
    ORDER BY tech.id DESC
""")

    technicians = cursor.fetchall()

    conn.close()

    return render_template(
        "technicians.html",
        technicians=technicians
    )

# ---------- ADD TECHNICIAN ----------
@app.route("/add-technician", methods=["POST"])
def add_technician():

    if session.get("role") != "admin":
        return "Access Denied"

    name = request.form["name"]
    email = request.form["email"]
    username = request.form["username"]
    password = request.form["password"]
    specialization = request.form["specialization"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # technicians table
    cursor.execute("""
    INSERT INTO technicians
    (name, email, specialization, username, password)
    VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        email,
        specialization,
        username,
        password
    ))

    # users table
    cursor.execute("""
    INSERT INTO users
    (username, password, role)
    VALUES (?, ?, ?)
    """, (
        username,
        password,
        "technician"
    ))

    # Save technician details
    cursor.execute("""
        INSERT INTO technicians
        (name, email, specialization, username, password)
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        email,
        specialization,
        username,
        password
    ))

    # Create login account automatically
    cursor.execute("""
        INSERT INTO users
        (username, password, role)
        VALUES (?, ?, ?)
    """, (
        username,
        password,
        "technician"
    ))

    conn.commit()
    conn.close()

    return redirect("/technicians")

# ---------- EDIT TECHNICIAN ----------
@app.route("/edit-technician/<int:id>", methods=["GET", "POST"])
def edit_technician(id):

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        specialization = request.form["specialization"]

        # technicians table
        cursor.execute("""
        INSERT INTO technicians
        (name, email, specialization, username, password)
        VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            email,
            specialization,
            username,
            password
        ))

        # users table
        cursor.execute("""
        INSERT INTO users
        (username, password, role)
        VALUES (?, ?, ?)
        """, (
            username,
            password,
            "technician"
        ))

        # Update technicians table
        cursor.execute("""
            UPDATE technicians
            SET
                name = ?,
                email = ?,
                username = ?,
                password = ?,
                specialization = ?
            WHERE id = ?
        """, (
            name,
            email,
            username,
            password,
            specialization,
            id
        ))

        # Update corresponding login account
        cursor.execute("""
            UPDATE users
            SET
                username = ?,
                password = ?
            WHERE role = 'technician'
            AND username = (
                SELECT username
                FROM technicians
                WHERE id = ?
            )
        """, (
            username,
            password,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/technicians")

    cursor.execute(
        "SELECT * FROM technicians WHERE id=?",
        (id,)
    )

    technician = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_technician.html",
        technician=technician
    )

# ---------- Delete Technician ----------
@app.route("/delete-technician/<int:tech_id>")
def delete_technician(tech_id):

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Remove ticket assignments first
    cursor.execute("""
        UPDATE tickets
        SET assigned_to = NULL
        WHERE assigned_to = ?
    """, (tech_id,))

    # Delete technician
    cursor.execute("""
        DELETE FROM technicians
        WHERE id = ?
    """, (tech_id,))

    conn.commit()
    conn.close()

    return redirect("/technicians")

# ---------- View Assigned Tickets ----------
@app.route("/technician-tickets/<int:tech_id>")
def technician_tickets(tech_id):

    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Technician information
    cursor.execute("""
        SELECT
            name,
            email,
            specialization
        FROM technicians
        WHERE id=?
    """, (tech_id,))

    technician = cursor.fetchone()

    # Assigned tickets
    cursor.execute("""
        SELECT
            id,
            title,
            description,
            category,
            priority,
            status,
            admin_response
        FROM tickets
        WHERE assigned_to=?
        ORDER BY id DESC
    """, (tech_id,))

    tickets = cursor.fetchall()

    conn.close()

    return render_template(
        "technician_tickets.html",
        technician=technician,
        tickets=tickets
    )
#-------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT id, category
    FROM tickets
    WHERE assigned_to IS NULL
""")

tickets = cursor.fetchall()

for ticket_id, category in tickets:
    tech_id = auto_assign_technician(category)
    if tech_id:
        cursor.execute(
            "UPDATE tickets SET assigned_to=? WHERE id=?",
            (tech_id, ticket_id)
        )

conn.commit()
conn.close()

print("Old tickets assigned successfully.")
# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)