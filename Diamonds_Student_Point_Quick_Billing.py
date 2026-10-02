
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os, tempfile, subprocess

SHOP_NAME = "DIAMOND'S STUDENT POINT"

class BillingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diamond's Student Point - Quick Billing")
        self.root.geometry("760x620")
        self.root.minsize(650, 520)

        self.rows = []
        self.bill_no = self.load_bill_no()

        top = tk.Frame(root, padx=15, pady=12)
        top.pack(fill="x")
        tk.Label(top, text=SHOP_NAME, font=("Arial", 20, "bold")).pack()
        tk.Label(top, text="Quick Billing • Rate × Quantity • 58mm Thermal", font=("Arial", 10)).pack(pady=(3,0))

        entry = tk.Frame(root, padx=15, pady=8)
        entry.pack(fill="x")

        tk.Label(entry, text="Rate", font=("Arial", 13, "bold")).grid(row=0, column=0, padx=5)
        self.rate = tk.Entry(entry, font=("Arial", 18), width=10, justify="right")
        self.rate.grid(row=0, column=1, padx=5)

        tk.Label(entry, text="Qty", font=("Arial", 13, "bold")).grid(row=0, column=2, padx=5)
        self.qty = tk.Entry(entry, font=("Arial", 18), width=8, justify="right")
        self.qty.grid(row=0, column=3, padx=5)

        tk.Button(entry, text="ADD", font=("Arial", 14, "bold"), width=9,
                  command=self.add_line).grid(row=0, column=4, padx=10)

        self.rate.bind("<Return>", lambda e: self.qty.focus())
        self.qty.bind("<Return>", lambda e: self.add_line())
        self.rate.focus()

        cols = ("rate", "qty", "amount")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", height=14)
        self.tree.heading("rate", text="RATE")
        self.tree.heading("qty", text="QTY")
        self.tree.heading("amount", text="AMOUNT")
        self.tree.column("rate", width=180, anchor="e")
        self.tree.column("qty", width=160, anchor="e")
        self.tree.column("amount", width=220, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=15, pady=8)

        self.tree.bind("<Delete>", lambda e: self.delete_selected())

        bottom = tk.Frame(root, padx=15, pady=8)
        bottom.pack(fill="x")

        self.subtotal_var = tk.StringVar(value="₹0.00")
        self.discount_var = tk.StringVar(value="₹0.00")
        self.total_var = tk.StringVar(value="₹0.00")

        tk.Label(bottom, text="Subtotal", font=("Arial", 12, "bold")).pack(side="left")
        tk.Label(bottom, textvariable=self.subtotal_var, font=("Arial", 13)).pack(side="left", padx=(5, 18))

        tk.Label(bottom, text="Discount", font=("Arial", 12, "bold")).pack(side="left")
        self.discount = tk.Entry(bottom, font=("Arial", 14), width=8, justify="right")
        self.discount.pack(side="left", padx=5)
        self.discount.insert(0, "0")
        tk.Label(bottom, text="₹", font=("Arial", 12)).pack(side="left")

        tk.Label(bottom, text="TOTAL", font=("Arial", 16, "bold")).pack(side="right", padx=(20, 5))
        tk.Label(bottom, textvariable=self.total_var, font=("Arial", 22, "bold")).pack(side="right")
        self.discount.bind("<Return>", lambda e: self.update_total())
        self.discount.bind("<KeyRelease>", lambda e: self.update_total())

        actions = tk.Frame(root, padx=15, pady=10)
        actions.pack(fill="x")
        tk.Button(actions, text="DELETE SELECTED", font=("Arial", 12),
                  command=self.delete_selected).pack(side="left", padx=5)
        tk.Button(actions, text="NEW BILL", font=("Arial", 12),
                  command=self.new_bill).pack(side="left", padx=5)
        tk.Button(actions, text="PRINT 58mm", font=("Arial", 13, "bold"),
                  command=self.print_bill).pack(side="right", padx=5)

        self.status = tk.StringVar(value=f"Bill No: {self.bill_no}")
        tk.Label(root, textvariable=self.status, anchor="w", padx=15, pady=5).pack(fill="x")

    def load_bill_no(self):
        path = os.path.join(os.path.expanduser("~"), ".diamond_student_point_billno")
        try:
            with open(path, "r") as f:
                return int(f.read().strip())
        except:
            return 1

    def save_bill_no(self):
        path = os.path.join(os.path.expanduser("~"), ".diamond_student_point_billno")
        with open(path, "w") as f:
            f.write(str(self.bill_no))

    def add_line(self):
        try:
            rate = float(self.rate.get())
            qty = float(self.qty.get())
            if rate < 0 or qty <= 0:
                raise ValueError
        except:
            messagebox.showerror("Invalid entry", "Enter a valid rate and quantity.")
            return

        amount = rate * qty
        self.rows.append((rate, qty, amount))
        self.tree.insert("", "end", values=(f"{rate:.2f}", f"{qty:g}", f"{amount:.2f}"))
        self.update_total()
        self.rate.delete(0, tk.END)
        self.qty.delete(0, tk.END)
        self.rate.focus()

    def update_total(self):
        subtotal = sum(r[2] for r in self.rows)
        try:
            discount = float(self.discount.get() or 0)
            if discount < 0:
                discount = 0
        except ValueError:
            discount = 0
        discount = min(discount, subtotal)
        total = subtotal - discount
        self.subtotal_var.set(f"₹{subtotal:.2f}")
        self.discount_var.set(f"₹{discount:.2f}")
        self.total_var.set(f"₹{total:.2f}")

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

    def new_bill(self):
        if self.rows:
            if not messagebox.askyesno("New Bill", "Clear this bill and start a new one?"):
                return
        self.rows.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.discount.delete(0, tk.END)
        self.discount.insert(0, "0")
        self.update_total()
        self.bill_no += 1
        self.save_bill_no()
        self.status.set(f"Bill No: {self.bill_no}")
        self.rate.focus()

    def receipt_text(self):
        now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
        subtotal = sum(r[2] for r in self.rows)
        try:
            discount = max(0, float(self.discount.get() or 0))
        except ValueError:
            discount = 0
        discount = min(discount, subtotal)
        total = subtotal - discount
        lines = []
        lines.append(SHOP_NAME.center(32))
        lines.append("-" * 32)
        lines.append(f"Bill No: {self.bill_no}")
        lines.append(now)
        lines.append("")
        for rate, qty, amount in self.rows:
            left = f"{rate:g} x {qty:g}"
            lines.append(f"{left:<15}{amount:>17.2f}")
        lines.append("-" * 32)
        lines.append(f"{'SUBTOTAL':<15}{subtotal:>17.2f}")
        lines.append(f"{'DISCOUNT':<15}{discount:>17.2f}")
        lines.append(f"{'TOTAL':<15}{total:>17.2f}")
        lines.append("")
        lines.append("Thank You!".center(32))
        return "\n".join(lines) + "\n\n\n"

    def print_bill(self):
        if not self.rows:
            messagebox.showwarning("Empty bill", "Add at least one line before printing.")
            return

        text = self.receipt_text()

        # Creates a receipt text file and opens it with the Windows default printer.
        # For direct ESC/POS printing, select the Posiflow printer in Windows and
        # use its vendor/driver utility or replace this method with the printer's
        # RAW/ESC-POS driver once the exact USB/COM driver is installed.
        path = os.path.join(tempfile.gettempdir(), f"diamond_bill_{self.bill_no}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

        try:
            os.startfile(path, "print")
        except Exception as e:
            messagebox.showinfo(
                "Receipt created",
                f"Receipt saved here:\n{path}\n\n"
                "Set the Posiflow 58mm printer as the Windows default printer, "
                "then print this receipt from the printer driver."
            )

if __name__ == "__main__":
    root = tk.Tk()
    BillingApp(root)
    root.mainloop()
