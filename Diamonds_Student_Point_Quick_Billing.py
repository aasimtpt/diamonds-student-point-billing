import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import sqlite3
import tempfile

SHOP_NAME = "DIAMOND'S STUDENT POINT"
APP_DIR = os.path.join(os.path.expanduser("~"), "DiamondStudentPoint")
DB_PATH = os.path.join(APP_DIR, "billing.db")
BILLNO_PATH = os.path.join(APP_DIR, "billno.txt")
os.makedirs(APP_DIR, exist_ok=True)


class BillingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diamond's Student Point - Quick Billing")
        self.root.geometry("1050x720")
        self.root.minsize(900, 620)

        self.rows = []
        # Create the database/tables before reading the next bill number.
        self.init_db()
        self.bill_no = self.load_bill_no()

        self.build_ui()
        self.update_total()

    # ---------- Database ----------
    def db(self):
        return sqlite3.connect(DB_PATH)

    def init_db(self):
        # If an incomplete/corrupt database file exists, recreate it safely.
        if os.path.exists(DB_PATH):
            try:
                with sqlite3.connect(DB_PATH) as test_con:
                    test_con.execute("PRAGMA integrity_check").fetchone()
            except sqlite3.DatabaseError:
                try:
                    os.remove(DB_PATH)
                except OSError:
                    pass

        with self.db() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS bills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_no INTEGER NOT NULL UNIQUE,
                    bill_date TEXT NOT NULL,
                    subtotal REAL NOT NULL,
                    discount REAL NOT NULL,
                    total REAL NOT NULL,
                    payment_mode TEXT NOT NULL,
                    amount_received REAL NOT NULL,
                    balance REAL NOT NULL
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS bill_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id INTEGER NOT NULL,
                    rate REAL NOT NULL,
                    qty REAL NOT NULL,
                    amount REAL NOT NULL,
                    FOREIGN KEY(bill_id) REFERENCES bills(id)
                )
            """)

    def load_bill_no(self):
        try:
            with open(BILLNO_PATH, "r", encoding="utf-8") as f:
                value = int(f.read().strip())
                return max(1, value)
        except (FileNotFoundError, ValueError, OSError):
            # Database tables have already been created in __init__.
            with self.db() as con:
                row = con.execute("SELECT COALESCE(MAX(bill_no), 0) FROM bills").fetchone()
                return int(row[0]) + 1 if row else 1

    def save_bill_no(self):
        with open(BILLNO_PATH, "w", encoding="utf-8") as f:
            f.write(str(self.bill_no))

    # ---------- Main UI ----------
    def build_ui(self):
        top = tk.Frame(self.root, padx=15, pady=10)
        top.pack(fill="x")
        tk.Label(top, text=SHOP_NAME, font=("Arial", 21, "bold")).pack()
        tk.Label(top, text="Quick Billing • Rate × Quantity • 58mm Thermal",
                 font=("Arial", 10)).pack(pady=(2, 0))

        tabs = ttk.Notebook(self.root)
        tabs.pack(fill="both", expand=True, padx=10, pady=5)

        self.bill_tab = tk.Frame(tabs)
        self.history_tab = tk.Frame(tabs)
        self.report_tab = tk.Frame(tabs)
        tabs.add(self.bill_tab, text="  NEW BILL  ")
        tabs.add(self.history_tab, text="  PREVIOUS BILLS  ")
        tabs.add(self.report_tab, text="  SALES REPORT  ")
        self.tabs = tabs

        self.build_bill_tab()
        self.build_history_tab()
        self.build_report_tab()

        self.status = tk.StringVar(value=f"Bill No: {self.bill_no}")
        tk.Label(self.root, textvariable=self.status, anchor="w",
                 padx=15, pady=5).pack(fill="x")

    def build_bill_tab(self):
        entry = tk.Frame(self.bill_tab, padx=15, pady=10)
        entry.pack(fill="x")

        tk.Label(entry, text="Rate", font=("Arial", 13, "bold")).grid(row=0, column=0, padx=5)
        self.rate = tk.Entry(entry, font=("Arial", 18), width=10, justify="right")
        self.rate.grid(row=0, column=1, padx=5)

        tk.Label(entry, text="Qty", font=("Arial", 13, "bold")).grid(row=0, column=2, padx=5)
        self.qty = tk.Entry(entry, font=("Arial", 18), width=8, justify="right")
        self.qty.grid(row=0, column=3, padx=5)

        tk.Button(entry, text="ADD", font=("Arial", 14, "bold"), width=9,
                  command=self.add_line).grid(row=0, column=4, padx=12)

        self.rate.bind("<Return>", lambda e: self.qty.focus())
        self.qty.bind("<Return>", lambda e: self.add_line())

        cols = ("rate", "qty", "amount")
        self.tree = ttk.Treeview(self.bill_tab, columns=cols, show="headings", height=14)
        self.tree.heading("rate", text="RATE")
        self.tree.heading("qty", text="QTY")
        self.tree.heading("amount", text="AMOUNT")
        self.tree.column("rate", width=230, anchor="e")
        self.tree.column("qty", width=180, anchor="e")
        self.tree.column("amount", width=280, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=15, pady=5)
        self.tree.bind("<Delete>", lambda e: self.delete_selected())

        summary = tk.Frame(self.bill_tab, padx=15, pady=7)
        summary.pack(fill="x")

        self.subtotal_var = tk.StringVar(value="₹0.00")
        self.total_var = tk.StringVar(value="₹0.00")
        self.discount_var = tk.StringVar(value="₹0.00")
        self.received_var = tk.StringVar(value="0.00")
        self.balance_var = tk.StringVar(value="₹0.00")

        tk.Label(summary, text="Subtotal", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(summary, textvariable=self.subtotal_var, font=("Arial", 12)).grid(row=0, column=1, sticky="w", padx=(5, 20))

        tk.Label(summary, text="Discount", font=("Arial", 12, "bold")).grid(row=0, column=2, sticky="w")
        self.discount = tk.Entry(summary, font=("Arial", 14), width=9, justify="right")
        self.discount.grid(row=0, column=3, padx=5)
        self.discount.insert(0, "0")

        tk.Label(summary, text="Payment", font=("Arial", 12, "bold")).grid(row=0, column=4, sticky="w", padx=(15, 5))
        self.payment = ttk.Combobox(summary, values=["CASH", "UPI"], state="readonly", width=8, font=("Arial", 12))
        self.payment.set("CASH")
        self.payment.grid(row=0, column=5, padx=5)

        tk.Label(summary, text="Received", font=("Arial", 12, "bold")).grid(row=0, column=6, sticky="w", padx=(15, 5))
        self.received = tk.Entry(summary, textvariable=self.received_var, font=("Arial", 14), width=10, justify="right")
        self.received.grid(row=0, column=7, padx=5)

        tk.Label(summary, text="Change", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=8)
        tk.Label(summary, textvariable=self.balance_var, font=("Arial", 13, "bold")).grid(row=1, column=1, sticky="w", padx=5)

        tk.Label(summary, text="TOTAL", font=("Arial", 16, "bold")).grid(row=1, column=6, sticky="e", pady=8)
        tk.Label(summary, textvariable=self.total_var, font=("Arial", 21, "bold")).grid(row=1, column=7, sticky="e", padx=5)

        self.discount.bind("<KeyRelease>", lambda e: self.update_total())
        self.discount.bind("<Return>", lambda e: self.received.focus())
        self.received.bind("<KeyRelease>", lambda e: self.update_balance())
        self.payment.bind("<<ComboboxSelected>>", lambda e: self.payment_changed())

        actions = tk.Frame(self.bill_tab, padx=15, pady=10)
        actions.pack(fill="x")
        tk.Button(actions, text="DELETE SELECTED", font=("Arial", 11),
                  command=self.delete_selected).pack(side="left", padx=4)
        tk.Button(actions, text="CLEAR BILL", font=("Arial", 11),
                  command=self.clear_current).pack(side="left", padx=4)
        tk.Button(actions, text="SAVE & PRINT", font=("Arial", 13, "bold"),
                  command=self.save_and_print).pack(side="right", padx=4)

        self.rate.focus()

    # ---------- History ----------
    def build_history_tab(self):
        search = tk.Frame(self.history_tab, padx=12, pady=10)
        search.pack(fill="x")

        tk.Label(search, text="Search Bill No / Date / Payment:", font=("Arial", 11, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search, textvariable=self.search_var, font=("Arial", 13), width=28)
        self.search_entry.pack(side="left", padx=8)
        tk.Button(search, text="SEARCH", command=self.refresh_history).pack(side="left", padx=4)
        tk.Button(search, text="SHOW ALL", command=lambda: [self.search_var.set(""), self.refresh_history()]).pack(side="left", padx=4)
        tk.Button(search, text="REPRINT SELECTED", font=("Arial", 11, "bold"),
                  command=self.reprint_selected).pack(side="right", padx=4)

        cols = ("bill", "date", "subtotal", "discount", "total", "payment", "received", "change")
        self.history_tree = ttk.Treeview(self.history_tab, columns=cols, show="headings", height=18)
        headings = {
            "bill":"BILL NO", "date":"DATE / TIME", "subtotal":"SUBTOTAL",
            "discount":"DISCOUNT", "total":"TOTAL", "payment":"PAYMENT",
            "received":"RECEIVED", "change":"CHANGE"
        }
        widths = {"bill":80,"date":160,"subtotal":100,"discount":90,"total":100,"payment":90,"received":100,"change":90}
        for c in cols:
            self.history_tree.heading(c, text=headings[c])
            self.history_tree.column(c, width=widths[c], anchor="e")
        self.history_tree.pack(fill="both", expand=True, padx=12, pady=5)
        self.history_tree.bind("<Double-1>", lambda e: self.reprint_selected())
        self.refresh_history()

    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        q = self.search_var.get().strip()
        with self.db() as con:
            if q:
                rows = con.execute("""
                    SELECT id, bill_no, bill_date, subtotal, discount, total,
                           payment_mode, amount_received, balance
                    FROM bills
                    WHERE CAST(bill_no AS TEXT) LIKE ?
                       OR bill_date LIKE ?
                       OR payment_mode LIKE ?
                    ORDER BY id DESC
                """, (f"%{q}%", f"%{q}%", f"%{q.upper()}%")).fetchall()
            else:
                rows = con.execute("""
                    SELECT id, bill_no, bill_date, subtotal, discount, total,
                           payment_mode, amount_received, balance
                    FROM bills ORDER BY id DESC
                """).fetchall()
        for r in rows:
            self.history_tree.insert("", "end", iid=str(r[0]),
                                     values=(r[1], r[2], f"₹{r[3]:.2f}", f"₹{r[4]:.2f}",
                                             f"₹{r[5]:.2f}", r[6], f"₹{r[7]:.2f}", f"₹{r[8]:.2f}"))

    def reprint_selected(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("Select bill", "Select a previous bill first.")
            return
        bill_id = int(selected[0])
        text = self.make_receipt_from_id(bill_id)
        self.print_text(text, f"diamond_reprint_{bill_id}.txt")

    # ---------- Reports ----------
    def build_report_tab(self):
        controls = tk.Frame(self.report_tab, padx=12, pady=12)
        controls.pack(fill="x")

        tk.Button(controls, text="TODAY", font=("Arial", 11, "bold"),
                  command=self.show_today_report).pack(side="left", padx=4)
        tk.Button(controls, text="THIS MONTH", font=("Arial", 11, "bold"),
                  command=self.show_month_report).pack(side="left", padx=4)
        tk.Button(controls, text="REFRESH", command=self.refresh_current_report).pack(side="left", padx=4)

        self.report_title = tk.StringVar(value="Today's Sales")
        tk.Label(self.report_tab, textvariable=self.report_title,
                 font=("Arial", 18, "bold")).pack(pady=5)

        cards = tk.Frame(self.report_tab, padx=12, pady=5)
        cards.pack(fill="x")
        self.card_sales = tk.StringVar(value="₹0.00")
        self.card_bills = tk.StringVar(value="0")
        self.card_cash = tk.StringVar(value="₹0.00")
        self.card_upi = tk.StringVar(value="₹0.00")

        self.make_card(cards, "TOTAL SALES", self.card_sales, 0)
        self.make_card(cards, "BILLS", self.card_bills, 1)
        self.make_card(cards, "CASH", self.card_cash, 2)
        self.make_card(cards, "UPI", self.card_upi, 3)

        self.report_tree = ttk.Treeview(self.report_tab, columns=("payment","bills","sales"), show="headings", height=10)
        for c, h, w in [("payment","PAYMENT",180),("bills","BILLS",150),("sales","SALES",250)]:
            self.report_tree.heading(c, text=h)
            self.report_tree.column(c, width=w, anchor="center")
        self.report_tree.pack(fill="x", padx=12, pady=15)

        self.show_today_report()

    def make_card(self, parent, title, variable, col):
        f = tk.Frame(parent, relief="groove", bd=1, padx=18, pady=10)
        f.grid(row=0, column=col, padx=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(f, text=title, font=("Arial", 10, "bold")).pack()
        tk.Label(f, textvariable=variable, font=("Arial", 17, "bold")).pack(pady=(4,0))

    def get_report(self, start, end):
        with self.db() as con:
            row = con.execute("""
                SELECT COUNT(*), COALESCE(SUM(total),0),
                       COALESCE(SUM(CASE WHEN payment_mode='CASH' THEN total ELSE 0 END),0),
                       COALESCE(SUM(CASE WHEN payment_mode='UPI' THEN total ELSE 0 END),0)
                FROM bills WHERE bill_date >= ? AND bill_date < ?
            """, (start, end)).fetchone()
            modes = con.execute("""
                SELECT payment_mode, COUNT(*), COALESCE(SUM(total),0)
                FROM bills WHERE bill_date >= ? AND bill_date < ?
                GROUP BY payment_mode ORDER BY payment_mode
            """, (start, end)).fetchall()
        return row, modes

    def show_today_report(self):
        today = datetime.now().strftime("%Y-%m-%d")
        row, modes = self.get_report(today, "9999-12-31")
        self.report_title.set("Today's Sales")
        self.set_report_cards(row, modes)

    def show_month_report(self):
        now = datetime.now()
        start = now.strftime("%Y-%m-01")
        end_year = now.year + (1 if now.month == 12 else 0)
        end_month = 1 if now.month == 12 else now.month + 1
        end = f"{end_year:04d}-{end_month:02d}-01"
        row, modes = self.get_report(start, end)
        self.report_title.set(now.strftime("Sales Report - %B %Y"))
        self.set_report_cards(row, modes)

    def refresh_current_report(self):
        title = self.report_title.get()
        if title.startswith("Sales Report"):
            self.show_month_report()
        else:
            self.show_today_report()

    def set_report_cards(self, row, modes):
        count, sales, cash, upi = row
        self.card_sales.set(f"₹{sales:.2f}")
        self.card_bills.set(str(count))
        self.card_cash.set(f"₹{cash:.2f}")
        self.card_upi.set(f"₹{upi:.2f}")
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        for mode, bills, total in modes:
            self.report_tree.insert("", "end", values=(mode, bills, f"₹{total:.2f}"))

    # ---------- Billing ----------
    def add_line(self):
        try:
            rate = float(self.rate.get())
            qty = float(self.qty.get())
            if rate < 0 or qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid entry", "Enter a valid rate and quantity.")
            return
        amount = rate * qty
        self.rows.append((rate, qty, amount))
        self.tree.insert("", "end", values=(f"{rate:.2f}", f"{qty:g}", f"{amount:.2f}"))
        self.update_total()
        self.rate.delete(0, tk.END)
        self.qty.delete(0, tk.END)
        self.rate.focus()

    def get_discount(self):
        try:
            d = float(self.discount.get() or 0)
            return max(0, d)
        except ValueError:
            return 0

    def get_values(self):
        subtotal = sum(r[2] for r in self.rows)
        discount = min(self.get_discount(), subtotal)
        total = subtotal - discount
        return subtotal, discount, total

    def update_total(self):
        subtotal, discount, total = self.get_values()
        self.subtotal_var.set(f"₹{subtotal:.2f}")
        self.total_var.set(f"₹{total:.2f}")
        self.update_balance()

    def payment_changed(self):
        if self.payment.get() == "UPI":
            self.received.delete(0, tk.END)
            self.received.insert(0, f"{self.get_values()[2]:.2f}")
        self.update_balance()

    def update_balance(self):
        total = self.get_values()[2]
        try:
            received = float(self.received.get() or 0)
        except ValueError:
            received = 0
        change = max(0, received - total)
        self.balance_var.set(f"₹{change:.2f}")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        indexes = sorted([self.tree.index(i) for i in selected], reverse=True)
        for i in indexes:
            del self.rows[i]
        for i in selected:
            self.tree.delete(i)
        self.update_total()

    def clear_current(self):
        if self.rows and not messagebox.askyesno("Clear bill", "Clear the current bill?"):
            return
        self.rows.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.discount.delete(0, tk.END)
        self.discount.insert(0, "0")
        self.payment.set("CASH")
        self.received.delete(0, tk.END)
        self.received.insert(0, "0")
        self.update_total()
        self.rate.focus()

    # ---------- Saving / printing ----------
    def save_and_print(self):
        if not self.rows:
            messagebox.showwarning("Empty bill", "Add at least one line before printing.")
            return

        subtotal, discount, total = self.get_values()
        mode = self.payment.get()
        try:
            received = float(self.received.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid amount", "Enter a valid amount received.")
            return

        if mode == "CASH" and received < total:
            messagebox.showwarning("Amount insufficient", f"Received ₹{received:.2f}, but total is ₹{total:.2f}.")
            return

        if mode == "UPI":
            received = total

        change = max(0, received - total)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.db() as con:
            cur = con.execute("""
                INSERT INTO bills
                (bill_no,bill_date,subtotal,discount,total,payment_mode,amount_received,balance)
                VALUES (?,?,?,?,?,?,?,?)
            """, (self.bill_no, now, subtotal, discount, total, mode, received, change))
            bill_id = cur.lastrowid
            con.executemany("""
                INSERT INTO bill_items (bill_id,rate,qty,amount)
                VALUES (?,?,?,?)
            """, [(bill_id, r, q, a) for r, q, a in self.rows])

        text = self.make_receipt(
            self.bill_no, now, self.rows, subtotal, discount, total, mode, received, change
        )
        self.print_text(text, f"diamond_bill_{self.bill_no}.txt", clear_after=False)

        self.bill_no += 1
        self.save_bill_no()
        self.status.set(f"Bill No: {self.bill_no}")
        self.refresh_history()
        self.show_today_report()
        self.clear_current()

    def make_receipt(self, bill_no, date_text, rows, subtotal, discount, total, mode, received, change):
        lines = [
            SHOP_NAME.center(32),
            "-" * 32,
            f"Bill No: {bill_no}",
            date_text,
            ""
        ]
        for rate, qty, amount in rows:
            left = f"{rate:g} x {qty:g}"
            lines.append(f"{left:<15}{amount:>17.2f}")
        lines += [
            "-" * 32,
            f"{'SUBTOTAL':<15}{subtotal:>17.2f}",
            f"{'DISCOUNT':<15}{discount:>17.2f}",
            f"{'TOTAL':<15}{total:>17.2f}",
            f"{'PAYMENT':<15}{mode:>17}",
            f"{'RECEIVED':<15}{received:>17.2f}",
            f"{'CHANGE':<15}{change:>17.2f}",
            "",
            "Thank You!".center(32),
            "",
            ""
        ]
        return "\n".join(lines)

    def make_receipt_from_id(self, bill_id):
        with self.db() as con:
            b = con.execute("""
                SELECT bill_no,bill_date,subtotal,discount,total,payment_mode,amount_received,balance
                FROM bills WHERE id=?
            """, (bill_id,)).fetchone()
            items = con.execute("""
                SELECT rate,qty,amount FROM bill_items WHERE bill_id=? ORDER BY id
            """, (bill_id,)).fetchall()
        if not b:
            return ""
        bill_no, date_text, subtotal, discount, total, mode, received, change = b
        return self.make_receipt(bill_no, date_text, items, subtotal, discount, total, mode, received, change)

    def print_text(self, text, filename, clear_after=False):
        path = os.path.join(tempfile.gettempdir(), filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            os.startfile(path, "print")
        except Exception:
            messagebox.showinfo(
                "Receipt created",
                f"Receipt saved here:\n{path}\n\n"
                "Set the Posiflow 58mm printer as the Windows default printer."
            )
        if clear_after:
            self.clear_current()


if __name__ == "__main__":
    root = tk.Tk()
    BillingApp(root)
    root.mainloop()
