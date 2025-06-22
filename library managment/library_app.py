import tkinter as tk
from tkinter import messagebox
import sqlite3
import os

DB_NAME = "library.db"

# ---------- Database Setup ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Books table
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL
        )
    ''')

    # Borrowed Books table
    c.execute('''
        CREATE TABLE IF NOT EXISTS borrowed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # History table
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT
        )
    ''')

    # Default admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", "admin123", "admin"))

    # Add default books if none exist
    c.execute("SELECT COUNT(*) FROM books")
    if c.fetchone()[0] == 0:
        default_books = [
            "Python Programming",
            "Learn C in One Day",
            "Mastering JavaScript",
            "Data Structures and Algorithms",
            "Introduction to AI",
            "Database Design Fundamentals",
            "Clean Code",
            "Design Patterns in Python",
            "Networking Essentials",
            "Linux Basics for Hackers",
            "Operating Systems Concepts",
            "Computer Architecture",
            "Web Development with Flask",
            "HTML & CSS for Beginners",
            "Machine Learning with Python"
        ]
        c.executemany("INSERT INTO books (title) VALUES (?)", [(book,) for book in default_books])

    conn.commit()
    conn.close()

# ---------- Backend Logic ----------
class LibraryDB:
    def __init__(self):
        init_db()

    def register_user(self, username, password):
        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                          (username, password, "user"))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, username, password):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
            row = c.fetchone()
            return row[0] if row else None

    def get_user_id(self, username):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username=?", (username,))
            row = c.fetchone()
            return row[0] if row else None

    def add_book(self, title):
        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO books (title) VALUES (?)", (title,))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_available_books(self):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT title FROM books
                WHERE id NOT IN (SELECT book_id FROM borrowed)
            ''')
            return [row[0] for row in c.fetchall()]

    def borrow_book(self, book_title, username):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM books WHERE title=?", (book_title,))
            book = c.fetchone()
            user_id = self.get_user_id(username)
            if book:
                book_id = book[0]
                try:
                    c.execute("INSERT INTO borrowed (book_id, user_id) VALUES (?, ?)",
                              (book_id, user_id))
                    c.execute("INSERT INTO history (username, action) VALUES (?, ?)",
                              (username, f"Borrowed '{book_title}'"))
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False
            return False

    def return_book(self, book_title, username):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            user_id = self.get_user_id(username)
            c.execute("SELECT id FROM books WHERE title=?", (book_title,))
            book = c.fetchone()
            if book:
                book_id = book[0]
                c.execute("DELETE FROM borrowed WHERE book_id=? AND user_id=?", (book_id, user_id))
                if c.rowcount > 0:
                    c.execute("INSERT INTO history (username, action) VALUES (?, ?)",
                              (username, f"Returned '{book_title}'"))
                    conn.commit()
                    return True
        return False

    def get_user_history(self, username):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT action FROM history WHERE username=?", (username,))
            return [row[0] for row in c.fetchall()]

    def export_report(self, filename="library_report.txt"):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT u.username, b.title
                FROM borrowed br
                JOIN users u ON br.user_id = u.id
                JOIN books b ON br.book_id = b.id
            ''')
            rows = c.fetchall()
        with open(filename, "w") as f:
            f.write("Library Borrowed Books Report\n\n")
            for username, title in rows:
                f.write(f"{username} is borrowing '{title}'\n")
        return filename

# ---------- GUI Frontend ----------
class LibraryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Library Login")
        self.db = LibraryDB()
        self.current_user = None
        self.current_role = None
        self.build_login_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def build_login_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="Library Management System", font=("Arial", 16)).pack(pady=10)
        tk.Label(self.root, text="Username").pack()
        self.login_user_entry = tk.Entry(self.root)
        self.login_user_entry.pack()
        tk.Label(self.root, text="Password").pack()
        self.login_pass_entry = tk.Entry(self.root, show="*")
        self.login_pass_entry.pack()

        tk.Button(self.root, text="Login", command=self.login).pack(pady=5)
        tk.Button(self.root, text="Register", command=self.build_register_screen).pack()

    def build_register_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="Register New User", font=("Arial", 14)).pack(pady=10)
        tk.Label(self.root, text="Username").pack()
        self.reg_user_entry = tk.Entry(self.root)
        self.reg_user_entry.pack()
        tk.Label(self.root, text="Password").pack()
        self.reg_pass_entry = tk.Entry(self.root, show="*")
        self.reg_pass_entry.pack()
        tk.Button(self.root, text="Register", command=self.register_user).pack(pady=5)
        tk.Button(self.root, text="Back to Login", command=self.build_login_screen).pack()

    def build_main_screen(self):
        self.clear_screen()
        tk.Label(self.root, text=f"Welcome, {self.current_user}", font=("Arial", 14)).grid(row=0, column=0, columnspan=4, pady=10)

        self.book_display = tk.Text(self.root, height=10, width=50)
        self.book_display.grid(row=1, column=0, columnspan=4, padx=10)
        self.show_books()

        self.book_entry = tk.Entry(self.root, width=30)
        self.book_entry.grid(row=2, column=1, padx=5, pady=10)
        tk.Label(self.root, text="Book Name").grid(row=2, column=0)

        tk.Button(self.root, text="Borrow", command=self.borrow_book).grid(row=3, column=0)
        tk.Button(self.root, text="Return", command=self.return_book).grid(row=3, column=1)

        if self.current_role == "admin":
            tk.Button(self.root, text="Add Book", command=self.add_book).grid(row=3, column=2)

        tk.Button(self.root, text="Logout", command=self.build_login_screen).grid(row=3, column=3)
        tk.Button(self.root, text="View History", command=self.view_history).grid(row=4, column=0, pady=5)
        tk.Button(self.root, text="Export Report", command=self.export_report).grid(row=4, column=1, pady=5)

    def login(self):
        username = self.login_user_entry.get().strip()
        password = self.login_pass_entry.get().strip()
        role = self.db.login_user(username, password)
        if role:
            self.current_user = username
            self.current_role = role
            self.build_main_screen()
        else:
            messagebox.showerror("Login Failed", "Incorrect credentials.")

    def register_user(self):
        username = self.reg_user_entry.get().strip()
        password = self.reg_pass_entry.get().strip()
        if self.db.register_user(username, password):
            messagebox.showinfo("Success", "Registered! You can log in now.")
            self.build_login_screen()
        else:
            messagebox.showerror("Error", "Username already exists.")

    def show_books(self):
        self.book_display.delete(1.0, tk.END)
        books = self.db.get_available_books()
        self.book_display.insert(tk.END, "Available Books:\n\n" + "\n".join(books) if books else "No books available.")

    def add_book(self):
        title = self.book_entry.get().strip()
        if self.db.add_book(title):
            messagebox.showinfo("Success", f"'{title}' added.")
            self.book_entry.delete(0, tk.END)
            self.show_books()
        else:
            messagebox.showerror("Error", "Book already exists or invalid.")

    def borrow_book(self):
        book = self.book_entry.get().strip()
        if self.db.borrow_book(book, self.current_user):
            messagebox.showinfo("Success", f"'{book}' borrowed.")
            self.book_entry.delete(0, tk.END)
            self.show_books()
        else:
            messagebox.showerror("Error", "Book unavailable or already borrowed.")

    def return_book(self):
        book = self.book_entry.get().strip()
        if self.db.return_book(book, self.current_user):
            messagebox.showinfo("Success", f"'{book}' returned.")
            self.book_entry.delete(0, tk.END)
            self.show_books()
        else:
            messagebox.showerror("Error", "You didn't borrow this book.")

    def view_history(self):
        history = self.db.get_user_history(self.current_user)
        messagebox.showinfo("History", "\n".join(history) if history else "No activity yet.")

    def export_report(self):
        file = self.db.export_report()
        messagebox.showinfo("Report Exported", f"Saved to '{file}'")

# ---------- Run App ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = LibraryApp(root)
    root.mainloop()
