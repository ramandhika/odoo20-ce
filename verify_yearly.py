comp = env["res.company"].browse(1)
cenv = env(context={"allowed_company_ids": [comp.id]})
with env.cr.savepoint():
    p = cenv["res.partner"].create({"name": "YEARLY"})
    prod = cenv["product.product"].create({"name": "YEARLY", "taxes_id": [(5,0,0)], "supplier_taxes_id": [(5,0,0)]})
    j = cenv["account.journal"].search([("type","=","sale"),("company_id","=",comp.id)],limit=1)
    def inv(date):
        m = cenv["account.move"].create({
            "journal_id": j.id, "company_id": comp.id, "move_type": "out_invoice",
            "partner_id": p.id, "date": date, "invoice_date": date,
            "invoice_line_ids": [(0,0,{"product_id": prod.id, "quantity": 1, "price_unit": 100, "tax_ids": [(5,0,0)]})]})
        m.action_post()
        return m.name
    print("2026-10-05 ->", inv("2026-10-05"))
    print("2026-11-12 ->", inv("2026-11-12"))
    print("2026-12-31 ->", inv("2026-12-31"))
    print("2027-01-05 ->", inv("2027-01-05"), "<= RESET TAHUNAN")
env.cr.rollback(); env.cr.commit()
print("YEARLY TEST DONE (rolled back)")
