from datetime import timedelta
from app import app, db, Invoice

with app.app_context():
    invoices = Invoice.query.all()
    for inv in invoices:
        if inv.invoice_date:
            inv.invoice_date = inv.invoice_date + timedelta(hours=5)
    db.session.commit()
    print(f"Fixed time for {len(invoices)} invoice(s).")
