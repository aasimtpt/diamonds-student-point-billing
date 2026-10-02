import os
import sys
import sqlite3
import tempfile
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from PIL import Image, ImageDraw, ImageFont, ImageWin
except ImportError:
    Image = ImageDraw = ImageFont = ImageWin = None

try:
    import qrcode
except ImportError:
    qrcode = None

APP_NAME = "Diamond's Student Point"
UPI_ID = "diamondgraphicstpr@cnrb"
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.expanduser("~"), "DiamondStudentPoint")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "billing.db")
LOGO_PATH = os.path.join(BASE_DIR, "diamond_student_point_logo.png")


def money(v):
    return f"₹{float(v):.2f}"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no INTEGER UNIQUE,
            bill_date TEXT NOT NULL,
            subtotal REAL NOT NULL,
            discount REAL NOT NULL,
            total REAL NOT NULL,
            payment_mode TEXT NOT NULL,
            amount_received REAL NOT NULL,
            balance REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            rate REAL NOT NULL,
            qty REAL NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY(bill_id) REFERENCES bills(id)
        )
    """)
    con.commit()
    con.close()


def next_bill_no():
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT COALESCE(MAX(bill_no), 0) + 1 FROM bills")
    n = cur.fetchone()[0]
    con.close()
    return int(n)


class BillingApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x650")
        self.root.minsize(820, 600)

        init_db()

        self.bill_no = next_bill_no()
        self.items = []

        self.rate_var = tk.StringVar()
        self.qty_var = tk.StringVar(value="1")
        self.discount_var = tk.StringVar(value="0")
        self.payment_var = tk.StringVar(value="CASH")
        self.received_var = tk.StringVar(value="0")
        self.change_var = tk.StringVar(value="₹0.00")
        self.subtotal_var = tk.StringVar(value="₹0.00")
        self.total_var = tk.StringVar(value="₹0.00")
        self.bill_label_var = tk.StringVar(value=f"Bill No: {self.bill_no}")
        self.printer_var = tk.StringVar()
