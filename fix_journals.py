"""Duplikasi jurnal SUI ke anak (LEI, LSK, PBS, LUP, AHR) — 1:1 per kategori."""
Param = env["ir.config_parameter"]
code_ids = {v: int(k) for k, v in (p.split(":") for p in
            (Param.get_str("document_sequence.company_codes") or "1:SUI;2:LEI;3:LSK;4:PBS;5:LUP;6:AHR").split(";"))}
sui = env["res.company"].browse(code_ids["SUI"])
Journal = env["account.journal"]
MAP_COMMENT = {"INV": "Customer Invoices", "BILL": "Vendor Bills", "JMO": "General Journal",
               "PBNK": "Bank", "BNK": "Cash"}
for code, cid in code_ids.items():
    if code == "SUI":
        continue
    comp = env["res.company"].browse(cid)
    if Journal.search_count([("company_id", "=", cid)]) > 0:
        print("skip", code)
        continue
    cenv = env(context={"allowed_company_ids": [cid], "default_company_id": cid})
    for j in Journal.search([("company_id", "=", sui.id)]):
        new = cenv["account.journal"].create({
            "name": f"{j.name} ({comp.name})",
            "code": j.code,
            "type": j.type,
            "company_id": comp.id,
            "currency_id": j.currency_id.id or False,
            "default_account_id": j.default_account_id.id or False,
            "refund_sequence": j.refund_sequence,
            "payment_sequence": j.payment_sequence,
            "show_on_dashboard": True,
        })
        env.cr.commit()
        print(code, "->", j.code, new.id)
env.cr.commit()
for c in env["res.company"].search([]):
    print(c.name, "journals:", env["account.journal"].search_count([("company_id", "=", c.id)]))
print("JOURNALS DONE")
