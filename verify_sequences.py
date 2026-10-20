"""Verifikasi penomoran v2 — raw line_ids (tanpa tax/product). Data test di-rollback."""
from odoo import fields

Param = env["ir.config_parameter"].sudo()
_val = "1:SUI;2:LEI;3:LSK;4:PBS;5:LUP;6:AHR"
_p = Param.search([("key", "=", "document_sequence.company_codes")], limit=1)
if _p:
    _p.value = _val
else:
    Param.create({"key": "document_sequence.company_codes", "value": _val})
env.cr.commit()
code_ids = {v: int(k) for k, v in (p.split(":") for p in Param.get_str("document_sequence.company_codes").split(";"))}
print("PARAM ok")

Move = env["account.move"]
Partner = env["res.partner"]
Journal = env["account.journal"]

def _accounts(cenv):
    receivable = cenv["account.account"].search([("account_type", "=", "asset_receivable")], limit=1)
    payable = cenv["account.account"].search([("account_type", "=", "liability_payable")], limit=1)
    income = cenv["account.account"].search([("account_type", "like", "income")], limit=1)
    expense = cenv["account.account"].search([("account_type", "like", "expense")], limit=1)
    return receivable, payable, income, expense

with env.cr.savepoint():
    partner = Partner.create({"name": "SEQ TEST 2 CUSTOMER"})
    payable = Partner.create({"name": "SEQ TEST 2 VENDOR"})
    report = []
    for code in ["SUI", "LEI", "LSK", "PBS", "LUP", "AHR"]:
        comp = env["res.company"].browse(code_ids[code])
        row = {"company": code}
        cenv = env(context={"allowed_company_ids": [comp.id]})
        rec, pay, inc, exp = _accounts(cenv)
        prod = cenv["product.product"].create({"name": f"SEQT {code}",
            "taxes_id": [(5, 0, 0)], "supplier_taxes_id": [(5, 0, 0)]})
        sale_j = Journal.search([("type", "=", "sale"), ("company_id", "=", comp.id)], limit=1)
        pur_j = Journal.search([("type", "=", "purchase"), ("company_id", "=", comp.id)], limit=1)
        gen_j = Journal.search([("type", "=", "general"), ("code", "in", ("MISC",)), ("company_id", "=", comp.id)], limit=1)
        bank_j = Journal.search([("type", "=", "bank"), ("company_id", "=", comp.id)], limit=1)
        # 1. Customer invoice
        move = cenv["account.move"].create({
            "journal_id": sale_j.id, "company_id": comp.id, "move_type": "out_invoice",
            "partner_id": partner.id, "date": "2026-10-05", "invoice_date": "2026-10-05",
            "invoice_line_ids": [(0, 0, {"product_id": prod.id, "quantity": 1, "price_unit": 100, "tax_ids": [(5, 0, 0)]})]})
        move.action_post()
        row["invoice"] = move.name
        # 2. Credit note RINV
        crn = cenv["account.move"].create({
            "journal_id": sale_j.id, "company_id": comp.id, "move_type": "out_refund",
            "partner_id": partner.id, "date": "2026-10-06", "invoice_date": "2026-10-06",
            "invoice_line_ids": [(0, 0, {"product_id": prod.id, "quantity": 1, "price_unit": 100, "tax_ids": [(5, 0, 0)]})]})
        crn.action_post()
        row["credit_note"] = crn.name
        # 3. Vendor bill BILL
        bill = cenv["account.move"].create({
            "journal_id": pur_j.id, "company_id": comp.id, "move_type": "in_invoice",
            "partner_id": payable.id, "date": "2026-10-07", "invoice_date": "2026-10-07",
            "invoice_line_ids": [(0, 0, {"product_id": prod.id, "quantity": 1, "price_unit": 50, "tax_ids": [(5, 0, 0)]})]})
        bill.action_post()
        row["bill"] = bill.name
        # 4. Manual journal JMO
        jn = cenv["account.move"].create({
            "journal_id": gen_j.id, "company_id": comp.id, "partner_id": partner.id, "date": "2026-10-08",
            "line_ids": [(0, 0, {"account_id": inc.id, "debit": 10, "name": "seq test"}),
                         (0, 0, {"account_id": exp.id, "credit": 10, "name": "seq test"})]})
        jn.action_post()
        row["journal"] = jn.name
        # 5. Payment outgoing PBNK
        pml = cenv["account.payment.method.line"].search([("journal_id", "=", bank_j.id)], limit=1)
        paym = cenv["account.payment"].create({
            "partner_id": payable.id, "journal_id": bank_j.id, "company_id": comp.id, "date": "2026-10-09",
            "payment_type": "outbound", "amount": 10, "payment_method_line_id": pml.id})
        paym.action_post()
        row["payment"] = paym.name
        report.append(row)
    print("=== HASIL PENOMORAN (test semua di-rollback) ===")
    for r in report:
        print(f"{r['company']:4} inv={r['invoice']}  cn={r['credit_note']}  bill={r['bill']}  jmo={r['journal']}  pay={r['payment']}")

print("=== SALE/PURCHASE ORDER (ir.sequence preview) ===")
for code in ["SUI", "LEI", "LSK", "PBS", "LUP", "AHR"]:
    cenv = env(context={"allowed_company_ids": [code_ids[code]]})
    so = cenv["ir.sequence"].next_by_code("sale.order")
    po = cenv["ir.sequence"].next_by_code("purchase.order")
    print(f"{code:4} SO={so}  PO={po}")

env.cr.rollback()
env.cr.commit()
print("DONE — test data discarded")
