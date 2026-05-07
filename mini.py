import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import datetime
import hashlib
import webbrowser
import csv

# ------------------- Configuration -------------------
DB_FILE = "library.db"
MAX_DAYS = 14
FINE_PER_DAY = 10
DEFAULT_ADMIN = ("admin", "admin")


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class LibraryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Library Management System")
        self.root.geometry("1020x680")

        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()

        self._create_tables()

        self.current_user = None

        self._build_login_ui()

    # ---------------- Database ----------------
    def _create_tables(self):

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT,
                category TEXT,
                file_path TEXT,
                lender_name TEXT,
                issue_date TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'Available'
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                user TEXT,
                action TEXT,
                timestamp TEXT,
                details TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                user TEXT,
                amount REAL,
                timestamp TEXT
            )
        ''')

        self.conn.commit()

        # Default Admin
        self.cursor.execute(
            "SELECT id FROM users WHERE username=?",
            (DEFAULT_ADMIN[0],)
        )

        if not self.cursor.fetchone():
            self.cursor.execute(
                '''
                INSERT INTO users
                (username, password_hash, role, full_name)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    DEFAULT_ADMIN[0],
                    hash_pw(DEFAULT_ADMIN[1]),
                    'admin',
                    'Administrator'
                )
            )

            self.conn.commit()

        # Sample Books
        self.cursor.execute("SELECT COUNT(*) FROM books")

        if self.cursor.fetchone()[0] == 0:
            sample_books = [
                ("Python Programming", "Author A", "Programming", "", "", "", "", "Available"),
                ("Data Structures", "Author B", "CS", "", "", "", "", "Available"),
                ("Algorithms", "Author C", "CS", "", "", "", "", "Available")
            ]

            self.cursor.executemany(
                '''
                INSERT INTO books
                (title, author, category, file_path,
                lender_name, issue_date, due_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                sample_books
            )

            self.conn.commit()

    # ---------------- Login UI ----------------
    def _build_login_ui(self):

        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#283593")
        header.pack(fill="x")

        tk.Label(
            header,
            text="Digital Library Management System",
            bg="#283593",
            fg="white",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        frame = tk.Frame(self.root, bg="#f0f4f7", pady=30)
        frame.pack()

        tk.Label(frame, text="Username:", bg="#f0f4f7").grid(row=0, column=0, padx=6, pady=6)
        tk.Label(frame, text="Password:", bg="#f0f4f7").grid(row=1, column=0, padx=6, pady=6)

        self.login_user_var = tk.StringVar()
        self.login_pass_var = tk.StringVar()

        tk.Entry(frame, textvariable=self.login_user_var, width=30).grid(row=0, column=1)
        tk.Entry(frame, textvariable=self.login_pass_var, show="*", width=30).grid(row=1, column=1)

        btn_frame = tk.Frame(frame, bg="#f0f4f7")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Login", command=self._login).grid(row=0, column=0, padx=6)

        ttk.Button(
            btn_frame,
            text="Register (Student)",
            command=self._register_student
        ).grid(row=0, column=1, padx=6)

        ttk.Button(
            btn_frame,
            text="Quit",
            command=self._quit
        ).grid(row=0, column=2, padx=6)

        tk.Label(
            self.root,
            text="Default Admin: admin / admin",
            bg="#f0f4f7"
        ).pack()

    # ---------------- Login ----------------
    def _login(self):

        username = self.login_user_var.get().strip()
        password = self.login_pass_var.get()

        if not username or not password:
            messagebox.showwarning(
                "Input Error",
                "Please enter username and password"
            )
            return

        password_hash = hash_pw(password)

        self.cursor.execute(
            '''
            SELECT username, password_hash, role, full_name
            FROM users
            WHERE username=?
            ''',
            (username,)
        )

        user = self.cursor.fetchone()

        if not user:
            messagebox.showerror("Login Failed", "Username not found")
            return

        if password_hash != user[1]:
            messagebox.showerror("Login Failed", "Incorrect password")
            return

        self.current_user = {
            "username": user[0],
            "role": user[2],
            "full_name": user[3] or user[0]
        }

        messagebox.showinfo(
            "Welcome",
            f"Logged in as {self.current_user['full_name']}"
        )

        self._build_main_ui()

    # ---------------- Register ----------------
    def _register_student(self):

        top = tk.Toplevel(self.root)
        top.title("Register Student")

        tk.Label(top, text="Username:").grid(row=0, column=0, padx=6, pady=6)
        tk.Label(top, text="Password:").grid(row=1, column=0, padx=6, pady=6)
        tk.Label(top, text="Full Name:").grid(row=2, column=0, padx=6, pady=6)

        username_var = tk.StringVar()
        password_var = tk.StringVar()
        fullname_var = tk.StringVar()

        tk.Entry(top, textvariable=username_var).grid(row=0, column=1)
        tk.Entry(top, textvariable=password_var, show="*").grid(row=1, column=1)
        tk.Entry(top, textvariable=fullname_var).grid(row=2, column=1)

        def create_user():

            if not username_var.get().strip() or not password_var.get().strip():
                messagebox.showwarning(
                    "Input Error",
                    "Username and Password required"
                )
                return

            try:
                self.cursor.execute(
                    '''
                    INSERT INTO users
                    (username, password_hash, role, full_name)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        username_var.get().strip(),
                        hash_pw(password_var.get().strip()),
                        "student",
                        fullname_var.get().strip()
                    )
                )

                self.conn.commit()

                messagebox.showinfo(
                    "Success",
                    "Student registered successfully"
                )

                top.destroy()

            except sqlite3.IntegrityError:
                messagebox.showerror(
                    "Error",
                    "Username already exists"
                )

        ttk.Button(
            top,
            text="Create",
            command=create_user
        ).grid(row=3, column=0, columnspan=2, pady=8)

    # ---------------- Main UI ----------------
    def _build_main_ui(self):

        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#283593")
        header.pack(fill="x")

        tk.Label(
            header,
            text="Digital Library Management System",
            bg="#283593",
            fg="white",
            font=("Arial", 16, "bold")
        ).pack(side="left", padx=10)

        tk.Label(
            header,
            text=f"User: {self.current_user['username']} ({self.current_user['role']})",
            bg="#283593",
            fg="white"
        ).pack(side="right", padx=10)

        ttk.Button(
            header,
            text="Logout",
            command=self._logout
        ).pack(side="right", padx=6)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#f0f4f7")
        btn_frame.pack(fill="x", pady=8)

        ttk.Button(
            btn_frame,
            text="Display Books",
            command=self._display_books
        ).grid(row=0, column=0, padx=6)

        if self.current_user["role"] == "admin":

            ttk.Button(
                btn_frame,
                text="Add Book",
                command=self._add_book_ui
            ).grid(row=0, column=1, padx=6)

            ttk.Button(
                btn_frame,
                text="Dashboard",
                command=self._dashboard_ui
            ).grid(row=0, column=2, padx=6)

        ttk.Button(
            btn_frame,
            text="Issue Book",
            command=self._issue_book_ui
        ).grid(row=0, column=3, padx=6)

        ttk.Button(
            btn_frame,
            text="Return Book",
            command=self._return_book_ui
        ).grid(row=0, column=4, padx=6)

        # Search
        search_frame = tk.Frame(self.root, bg="#f0f4f7")
        search_frame.pack(fill="x", padx=10, pady=6)

        tk.Label(search_frame, text="Search:").pack(side="left")

        self.search_var = tk.StringVar()

        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=40
        )

        search_entry.pack(side="left", padx=6)

        search_entry.bind(
            "<KeyRelease>",
            lambda e: self._display_books()
        )

        # Table
        columns = (
            "ID",
            "Title",
            "Author",
            "Category",
            "Status",
            "Lender",
            "Issue Date",
            "Due Date"
        )

        self.tree = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=18
        )

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self._display_books()

    # ---------------- Display Books ----------------
    def _display_books(self):

        for row in self.tree.get_children():
            self.tree.delete(row)

        self.cursor.execute(
            '''
            SELECT id, title, author, category,
            status, lender_name, issue_date, due_date
            FROM books
            ORDER BY id
            '''
        )

        rows = self.cursor.fetchall()

        search_text = self.search_var.get().strip().lower()

        for row in rows:

            if search_text:
                haystack = " ".join(
                    [str(x or "").lower() for x in row[:4]]
                )

                if search_text not in haystack:
                    continue

            tag = "green" if row[4] == "Available" else "red"

            self.tree.insert(
                "",
                "end",
                values=row,
                tags=(tag,)
            )

        self.tree.tag_configure("green", background="#d0f0c0")
        self.tree.tag_configure("red", background="#ffcdd2")

    # ---------------- Add Book ----------------
    def _add_book_ui(self):

        if self.current_user["role"] != "admin":
            messagebox.showwarning(
                "Permission",
                "Only admin can add books"
            )
            return

        top = tk.Toplevel(self.root)
        top.title("Add Book")

        tk.Label(top, text="Title:").grid(row=0, column=0, padx=6, pady=6)
        tk.Label(top, text="Author:").grid(row=1, column=0, padx=6, pady=6)
        tk.Label(top, text="Category:").grid(row=2, column=0, padx=6, pady=6)

        title_var = tk.StringVar()
        author_var = tk.StringVar()
        category_var = tk.StringVar()

        tk.Entry(top, textvariable=title_var).grid(row=0, column=1)
        tk.Entry(top, textvariable=author_var).grid(row=1, column=1)
        tk.Entry(top, textvariable=category_var).grid(row=2, column=1)

        def save_book():

            title = title_var.get().strip()

            if not title:
                messagebox.showwarning(
                    "Input Error",
                    "Title required"
                )
                return

            self.cursor.execute(
                '''
                INSERT INTO books
                (title, author, category, status)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    title,
                    author_var.get().strip(),
                    category_var.get().strip(),
                    "Available"
                )
            )

            self.conn.commit()

            messagebox.showinfo(
                "Added",
                f"Book '{title}' added successfully"
            )

            top.destroy()

            self._display_books()

        ttk.Button(
            top,
            text="Save",
            command=save_book
        ).grid(row=3, column=0, columnspan=2, pady=8)

    # ---------------- Issue Book ----------------
    def _issue_book_ui(self):

        top = tk.Toplevel(self.root)
        top.title("Issue Book")

        tk.Label(top, text="Book ID:").grid(row=0, column=0, padx=6, pady=6)

        book_id_var = tk.StringVar()

        tk.Entry(top, textvariable=book_id_var).grid(row=0, column=1)

        def issue_book():

            book_id = book_id_var.get().strip()

            if not book_id.isdigit():
                messagebox.showerror(
                    "Error",
                    "Invalid Book ID"
                )
                return

            self.cursor.execute(
                '''
                SELECT title, status
                FROM books
                WHERE id=?
                ''',
                (book_id,)
            )

            book = self.cursor.fetchone()

            if not book:
                messagebox.showerror(
                    "Error",
                    "Book not found"
                )
                return

            if book[1] != "Available":
                messagebox.showwarning(
                    "Unavailable",
                    "Book already issued"
                )
                return

            issue_date = datetime.datetime.now()

            due_date = issue_date + datetime.timedelta(days=MAX_DAYS)

            self.cursor.execute(
                '''
                UPDATE books
                SET lender_name=?,
                    issue_date=?,
                    due_date=?,
                    status=?
                WHERE id=?
                ''',
                (
                    self.current_user["username"],
                    issue_date.strftime("%Y-%m-%d"),
                    due_date.strftime("%Y-%m-%d"),
                    "Issued",
                    book_id
                )
            )

            self.conn.commit()

            messagebox.showinfo(
                "Issued",
                f"Book issued successfully\nDue Date: {due_date.strftime('%Y-%m-%d')}"
            )

            top.destroy()

            self._display_books()

        ttk.Button(
            top,
            text="Issue",
            command=issue_book
        ).grid(row=1, column=0, columnspan=2, pady=8)

    # ---------------- Return Book ----------------
    def _return_book_ui(self):

        top = tk.Toplevel(self.root)
        top.title("Return Book")

        tk.Label(top, text="Book ID:").grid(row=0, column=0, padx=6, pady=6)

        book_id_var = tk.StringVar()

        tk.Entry(top, textvariable=book_id_var).grid(row=0, column=1)

        def return_book():

            book_id = book_id_var.get().strip()

            self.cursor.execute(
                '''
                SELECT lender_name, due_date
                FROM books
                WHERE id=?
                ''',
                (book_id,)
            )

            book = self.cursor.fetchone()

            if not book:
                messagebox.showerror(
                    "Error",
                    "Book not found"
                )
                return

            fine = 0

            if book[1]:

                due_date = datetime.datetime.strptime(
                    book[1],
                    "%Y-%m-%d"
                )

                today = datetime.datetime.now()

                if today > due_date:
                    days = (today - due_date).days
                    fine = days * FINE_PER_DAY

            self.cursor.execute(
                '''
                UPDATE books
                SET lender_name='',
                    issue_date='',
                    due_date='',
                    status='Available'
                WHERE id=?
                ''',
                (book_id,)
            )

            self.conn.commit()

            messagebox.showinfo(
                "Returned",
                f"Book returned successfully\nFine: ₹{fine}"
            )

            top.destroy()

            self._display_books()

        ttk.Button(
            top,
            text="Return",
            command=return_book
        ).grid(row=1, column=0, columnspan=2, pady=8)

    # ---------------- Dashboard ----------------
    def _dashboard_ui(self):

        top = tk.Toplevel(self.root)
        top.title("Dashboard")

        self.cursor.execute("SELECT COUNT(*) FROM books")
        total_books = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM books WHERE status='Issued'"
        )

        issued_books = self.cursor.fetchone()[0]

        available_books = total_books - issued_books

        tk.Label(
            top,
            text=f"Total Books: {total_books}",
            font=("Arial", 12)
        ).pack(pady=6)

        tk.Label(
            top,
            text=f"Issued Books: {issued_books}",
            font=("Arial", 12)
        ).pack(pady=6)

        tk.Label(
            top,
            text=f"Available Books: {available_books}",
            font=("Arial", 12)
        ).pack(pady=6)

    # ---------------- Logout ----------------
    def _logout(self):

        self.current_user = None

        self._build_login_ui()

    # ---------------- Quit ----------------
    def _quit(self):

        self.conn.commit()
        self.conn.close()

        self.root.destroy()


# ---------------- Run Application ----------------
if __name__ == "__main__":

    root = tk.Tk()

    app = LibraryApp(root)

    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: (
            app.conn.commit(),
            app.conn.close(),
            root.destroy()
        )
    )

    root.mainloop()
