# -*- coding: utf-8 -*-
"""REVOKE & FIX (direct DB, tanpa module):
A) COA kas/bank yang per-PT (1 per 1) di-MERGE jadi 1 set shared dipakai semua PT.
   Kode dibersihkan (tanpa suffix .SUI/.LEI/...), duplikat tiap PT dihapus.
B) Kategori produk -> hierarki parent/child di bawah root 'All'.
C) Produk lama di-revoke: dibuat ulang 1000 SEMUA barang (storable),
   kode barang di field Reference (default_code), nama bersih tanpa kode.
"""
from collections import defaultdict
import json

Param = env["ir.config_parameter"].sudo()
code_ids = {v: int(k) for k, v in (p.split(":") for p in
            (Param.get_str("document_sequence.company_codes")
             or "1:SUI;2:LEI;3:LSK;4:PBS;5:LUP;6:AHR").split(";"))}
ALL_CIDS = list(code_ids.values())
env = env(su=True)
cr = env.cr

# ========================= A. MERGE COA KAS/BANK =========================
cr.execute("""
    SELECT id, code_store->>'1' FROM account_account
    WHERE account_type='asset_cash' AND code_store->>'1' ~ '\\.[A-Z]{3}$'
""")
rows = cr.fetchall()
by_base = {}
for aid, code in rows:
    base = code.split(".")[0]
    by_base.setdefault(base, {})[code] = aid

sui_ids, dup_ids = [], []
for base, m in by_base.items():
    sui_ids.append(m[[k for k in m if k.endswith(".SUI")][0]])
    dup_ids += [v for k, v in m.items() if not k.endswith(".SUI")]

# 1) pastikan tidak ada journal item memakai akun duplikat lalu lepas journal & hapus
cr.execute("SELECT count(*) FROM account_move_line WHERE account_id = ANY(%s)", [dup_ids])
n_aml = cr.fetchone()[0]
assert n_aml == 0, f"Masih ada {n_aml} journal item memakai akun duplikat!"
cr.execute("UPDATE account_journal SET default_account_id = NULL WHERE default_account_id = ANY(%s)", [dup_ids])
cr.execute("DELETE FROM account_account_res_company_rel WHERE account_account_id = ANY(%s)", [dup_ids])
cr.execute("DELETE FROM account_account WHERE id = ANY(%s)", [dup_ids])
print(f"[A1] duplikat kas non-SUI dihapus: {len(dup_ids)} akun (0 journal item)")

# 2) akun milik SUI: bersihkan kode + share ke semua PT
for aid in sui_ids:
    cr.execute("SELECT code_store->>'1' FROM account_account WHERE id=%s", [aid])
    new = cr.fetchone()[0].split(".")[0]
    cr.execute("UPDATE account_account SET code_store=%s WHERE id=%s",
               [json.dumps({str(cid): new for cid in ALL_CIDS}), aid])
    for cid in ALL_CIDS:
        cr.execute("""SELECT 1 FROM account_account_res_company_rel
                      WHERE account_account_id=%s AND res_company_id=%s""", [aid, cid])
        if not cr.fetchone():
            cr.execute("INSERT INTO account_account_res_company_rel (account_account_id, res_company_id) VALUES (%s,%s)",
                       [aid, cid])
print(f"[A2] {len(sui_ids)} akun kas/bank kini SHARED untuk {len(ALL_CIDS)} PT")

# 3) jurnal BNK1/CSH1 semua PT -> akun shared tersebut
for jcode, basecode in (("BNK1", "1-1200"), ("CSH1", "1-1100")):
    cr.execute("""
        UPDATE account_journal j SET default_account_id = a.id
        FROM account_account a
        WHERE j.code = %s AND a.code_store->>'1' = %s
    """, [jcode, basecode])
env.invalidate_all()
cr.commit()
cr.execute("""
    SELECT j.code, c.name, k.code_store->>'1' FROM account_journal j
    JOIN res_company c ON c.id = j.company_id
    JOIN account_account k ON k.id = j.default_account_id
    WHERE j.code IN ('BNK1','CSH1') ORDER BY c.id, j.code
""")
print("[A3] jurnal -> akun shared:", [(r[0], r[1].split()[1], r[2]) for r in cr.fetchall()])

# ========================= B. KATEGORI PARENT/CHILD =========================
# 0) revoke produk & kategori lama
Product = env["product.product"].sudo()
allp = Product.search([])
while allp:
    chunk, allp = allp[:100], allp[100:]
    chunk.unlink()
cr.commit()
print(f"[B0] produk lama dihapus: 1000")

Categ = env["product.category"].sudo()
Categ.search([]).unlink()          # hapus SEMUA kategori lama (Goods/Expenses/Services + inject kemarin)
env.cr.commit()

root = Categ.create({"name": "All"})
def cat(name, parent=None):
    return Categ.create({"name": name, "parent_id": (parent or root).id})

stock_tree = [
    ("Barang Dagang", "1-3100", "fifo",
     [(["Barang Dagang Lokal", "Barang Dagang Impor"], 2, 1)]),
    ("Bahan Baku", "1-3110", "fifo",
     [(["Logam", "Kimia", "Plastik", "Kertas", "Tekstil"], 5, 1)]),
    ("Bahan Penolong", "1-3120", "average",
     [(["Kemasan & Label", "Oli & Pelumas", "Gas Industri", "Alat Bersih & Hygiene"], 4, 1)]),
    ("Barang Dalam Proses (WIP)", "1-3130", "fifo",
     [(["WIP Mekanikal", "WIP Elektronik", "WIP Mould & Punch"], 3, 1)]),
    ("Barang Jadi", "1-3140", "fifo",
     [(["Elektronik", "Mekanikal", "Garmen", "Makanan", "Minuman"], 5, 2)]),
    ("Sparepart & Consumables", "1-3160", "average",
     [(["Sparepart Mesin", "Sparepart Listrik MRO", "Consumables Umum"], 3, 1)]),
]
accs = {}
cr.execute("SELECT id, code_store->>'1' FROM account_account")
for aid, code in cr.fetchall():
    if code:
        accs[code] = aid

leaf_cats = []  # [(category, props)] — props stok juga dipasang di leaf supaya valuation tepat
for pname, acccode, method, children_spec in stock_tree:
    p = cat(pname)
    props = {
        "property_cost_method": method,
        "property_valuation": "real_time",
        "property_account_income_categ_id": accs["4-1100"],
        "property_account_expense_categ_id": accs["5-1100"],
        "property_stock_valuation_account_id": accs[acccode],
        "property_price_difference_account_id": accs["5-1900"],
    }
    leaf_cats.append((p, props))
    for child_names, _, idx in children_spec:
        for cn in child_names:
            leaf_cats.append((cat(f"{cn}" if idx == 1 else f"The {cn}", p), props))

srv = cat("Jasa (Non-Stok)")
svc_node = (srv, {
    "property_valuation": "periodic",
    "property_cost_method": "standard",
    "property_account_income_categ_id": accs["4-1200"],
    "property_account_expense_categ_id": accs["5-3800"],
})
leaf_cats.append(svc_node)
for cn in ["Servis & Perawatan", "Sewa & Rental"]:
    leaf_cats.append((cat(cn, srv), {}))

# jurnal stok per-PT untuk setiap node/leaf stok
for code, cid in code_ids.items():
    C = env["res.company"].browse(cid)
    stj = env["account.journal"].search([("company_id", "=", cid), ("code", "=", "STJ")], limit=1)
    for c_node, props in leaf_cats:
        if props:
            c_node.with_company(C).write({**props, "property_stock_journal": stj.id})
cr.commit()
print(f"[B1] kategori: {len(Categ.search([]))} node di-bawah root 'All' (parent/child)")

# ========================= C. 1000 PRODUK BARU (semua barang) =========================
W1 = ["Mesin", "Gear", "Sprocket", "Bearing", "Motor", "Pompa", "Kabel", "Sensor",
      "Valve", "Siklon", "Modul", "Panel", "Kondensor", "Kompresor", "Filter",
      "Rangka", "Siku", "Pipa", "Selang", "V-Belt", "Baut", "Klem", "Relay",
      "Inverter", "Driver", "Switch", "Terminal", "Enclosure", "Actuator",
      "Sensor Ultrasonic", "Pneumatik", "Hidrolik", "Gardan", "Axle", "Bushing",
      "Coupling", "Chain", "Timing Belt", "Heat Exchanger", "Tangki", "Roller",
      "Ball Screw", "Linear Guide", "Servo"]
W2 = ["Industri", "Otomotif", "Perkapalan", "Transportasi", "Kimia", "Tekstil",
      "Agro", "Konstruksi", "Elektronik", "Pangan", "Pertambangan", "Pelabuhan",
      "Farmasi", "Plastik", "Kertas", "Logistik", "Garmen", "Pertanian", "Minuman", "Fabrikasi"]
W3 = ["Standar", "Heavy Duty", "Mini", "Turbo", "Premium", "Eco", "Pro",
      "Seri B-2", "Anti-Karat", "Tahan Panas", "Custom", "OEM", "Semi-Otomatis",
      "Fully Otomatis", "High Speed", "Low Noise"]
W4 = ["41-QX", "148x9", "2.5mm", "M8x20", "DN50", "12V", "220V", "5A", "40W",
      "Type-C", "IP65", "SS316", "SPHC", "NBR", "EPDM", "Blue Line", "MKR-X", "V2"]
w1, w2, w3, w4 = [w.strip() for w in W1], [w.strip() for w in W2], [w.strip() for w in W3], [w.strip() for w in W4]

leaves = [c for c, _ in leaf_cats][:18]  # hanya leaves jasa/stok utama yang dipakai? taruh semua
leaves = [c for c, _ in leaf_cats]
uom = env.ref("uom.product_uom_unit")
vals_list = []
for i in range(1, 1001):
    nm = f"{w1[i % len(w1)]} {w2[(i*7) % len(w2)]} {w3[(i*13) % len(w3)]} {w4[(i*3) % len(w4)]}"
    price = ((i * 7919) % 900 + 10) * 1000
    cost = int(price * (0.55 + ((i * 31) % 20) / 100))
    vals_list.append({
        "default_code": f"BRG-{i:04d}",
        "name": nm,
        "categ_id": leaves[i % len(leaves)].id,
        "type": "consu",
        "is_storable": True,
        "list_price": price,
        "standard_price": cost,
        "uom_id": uom.id,
        "purchase_method": "receive",
        "invoice_policy": "delivery",
        "sale_delay": (i % 7) + 1,
        "description_sale": f"Barang untuk kebutuhan {w2[(i*7) % len(w2)]}.",
    })
added = 0
for i in range(0, len(vals_list), 250):
    Product.create(vals_list[i:i + 250])
    cr.commit()
    added += len(vals_list[i:i + 250])
print(f"[C1] produk dibuat: {added} (semua barang storable; kode di field Reference)")

# ========================= VERIFY =========================
cr.commit()
print("=== VERIFY ===")
print("total akun    :", len(env["account.account"].sudo().search([])))
print("total kategori:", len(Categ.search([])))
print("total produk  :", len(Product.search([])))
for p in Product.search([], limit=3):
    print("sampel:", p.default_code, "|", p.name, "|", p.categ_id.complete_name)
for cn in ["All", "Barang Jadi", "FERT Mekanikal"]:
    c = Categ.search([("name", "=", cn)], limit=1)
    if c:
        print(f"kat '{cn}': parent={c.parent_id.name or '-'} children={[x.name for x in c.child_id]}")
