Param = env["ir.config_parameter"]
code_ids = {v: int(k) for k, v in (p.split(":") for p in Param.get_str("document_sequence.company_codes").split(";"))}
ct = env["account.chart.template"]
for code, cid in code_ids.items():
    comp = env["res.company"].browse(cid)
    if env["account.journal"].search_count([("company_id", "=", cid)]) == 0:
        cenv = env(context={"allowed_company_ids": [cid]})
        cenv["account.chart.template"]._load("generic_coa", comp, False)
        env.cr.commit()
        print("CHART re-loaded for", code)
for c in env["res.company"].search([]):
    n = env["account.journal"].search_count([("company_id", "=", c.id)])
    print(c.name, "-> journals:", n)
env.cr.commit()
print("FIXED")
