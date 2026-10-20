"""Setup 6 companies + prefix penomoran dokumen Odoo 20 Community.
Format: [COMPANY_ID]/[SHORT_CODE]/[YYYY]/[MM]/[00001] — counter reset PERTAHUN.
Jalan via: ./venv/bin/python odoo/odoo-bin shell -c odoo20.conf --no-http < this_file
"""
BASE = "/SUI/"  # diganti dinamis per company di bawah
PREF = "{comp}/{code_}/%(year)s/%(month)s/"

companies_code = {"SUI": "PT SUI (Holding)", "LEI": "PT LEI", "LSK": "PT LSK",
                  "PBS": "PT PBS", "LUP": "PT LUP", "AHR": "PT AHR"}

Comp, Seq, User = env["res.company"], env["ir.sequence"], env["res.users"]
env.cr.execute("SELECT id,name FROM res_company")
existing = dict(env.cr.fetchall())

# --- 1) Companies & hierarchy holding ---
main = env.ref("base.main_company")
sui = Comp.search([("name", "=", companies_code["SUI"])], limit=1) or main
sui.write({"name": companies_code["SUI"]})
ids = {"SUI": sui.id}
for code, name in companies_code.items():
    if code == "SUI":
        continue
    rec = Comp.search([("name", "=", name)], limit=1)
    if not rec:
        rec = Comp.create({"name": name, "parent_id": sui.id})
        env.cr.commit()
    ids[code] = rec.id
print("COMPANIES:", ids)

# admin masuk semua companies biar bisa switching
root_user = User.browse([2]) or User.browse(User._uid)
User.browse(env.ref("base.user_admin").id).write(
    {"company_ids": [(6, 0, list(ids.values()))], "company_id": sui.id})

# --- 2) Chart of accounts generic per company (membuat journals default) ---
ct = env["account.chart.template"]
for code, cid in ids.items():
    comp = Comp.browse(cid)
    if not comp.chart_template:
        ct._load("generic", comp, False)
        env.cr.commit()
        print(f"CHART loaded for {code}")
for c in Comp.search([]):
    print("COA", c.name, "->", c.chart_template or "NONE")

# --- 3) Sequences generik (per company) yang tidak lewat journal ---
GEN = {  # short_code -> ir.sequence.code
    "REQ": "odoo.user.request",
    "SORD": None,  # di-set khusus di bawah (ada sequence existing)
    "PORD": None,
    "DPBILL": "account.downpayment",
    "RDP": "account.downpayment.refund",
    "OAP": "account.opening.ap",
    "ADJSP": "stock.scrap",
    "LDCST": "stock.landed.cost",
    "BNK": "account.bank.statement",
}
for code, cid in ids.items():
    comp = Comp.browse(cid)
    for short, seq_code in GEN.items():
        if not seq_code:
            continue
        exist = Seq.search([("code", "=", seq_code), ("company_id", "=", cid)], limit=1)
        if exist:
            continue
        Seq.create({
            "name": f"{short} {comp.name}", "code": seq_code,
            "prefix": PREF.format(comp=code, code_=short),
            "padding": 5, "use_date_range": True, "company_id": cid,
        })
    # SORD / PORD pakai code native agar langsung dipakai dokumennya
    for short, native in (("SORD", "sale.order"), ("PORD", "purchase.order")):
        exist = Seq.search([("code", "=", native), ("company_id", "=", cid)], limit=1)
        if exist:
            exist.write({"prefix": PREF.format(comp=code, code_=short), "padding": 5,
                         "use_date_range": True})
            continue
        Seq.create({
            "name": f"{short} {comp.name}", "code": native,
            "prefix": PREF.format(comp=code, code_=short),
            "padding": 5, "use_date_range": True, "company_id": cid,
        })
env.cr.commit()

# --- 4) Journal sequences per company (jurnal akuntansi) ---
JMAP = {  # journal type -> short codes (main, refund)
    "sale":     ("INV", "RINV"),
    "purchase": ("BILL", "RBILL"),
    "general":  ("JMO", None),
    "bank":     ("PBNK", "BNK"),
    "cash":     ("PBNK", "BNK"),
}
Journal = env["account.journal"]
for code, cid in ids.items():
    comp = Comp.browse(cid)
    for jtype, (main_sc, refund_sc) in JMAP.items():
        for j in Journal.search([("type", "=", jtype), ("company_id", "=", cid)]):
            pref = PREF.format(comp=code, code_=main_sc)
            if j.sequence_id:
                j.sequence_id.write({"prefix": pref, "padding": 5, "use_date_range": True})
            if refund_sc and j.refund_sequence_id and j.refund_sequence:
                j.refund_sequence_id.write({
                    "prefix": PREF.format(comp=code, code_=refund_sc),
                    "padding": 5, "use_date_range": True})
env.cr.commit()

# --- 5) Ringkasan ---
print("=== SEQUENCE SUMMARY ===")
for s in Seq.search([("company_id", "!=", False),
                     ("code", "in", ["sale.order", "purchase.order", "ir.sequence.journal",
                                      "ir.sequence.title", "odoo.user.request",
                                      "account.downpayment", "account.downpayment.refund",
                                      "account.opening.ap", "stock.scrap", "stock.landed.cost",
                                      "account.bank.statement"])]):
    print(s.company_id.code or "?", "|", s.code or s.name, "|", s.prefix, "| noupdate_range:", s.use_date_range)
env.cr.commit()
print("DONE")
