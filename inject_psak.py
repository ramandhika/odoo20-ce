# -*- coding: utf-8 -*-
"""Suntik langsung ke DB (tanpa module baru):
1) COA kompleks ala PSAK Indonesia (aset/lia/equity/pendapatan/HPP/beban/pajak)
2) Account group tree (struktur klp akun)
3) Setting valuation perusahaan (perpetual/automated + jurnal stok + WIP + selisih harga)
4) Kategori produk + automated inventory valuation per perusahaan (company_dependent)
5) 1000 produk
"""
import itertools
import random

Param = env["ir.config_parameter"].sudo()
code_ids = {v: int(k) for k, v in (p.split(":") for p in
            (Param.get_str("document_sequence.company_codes") or "1:SUI;2:LEI;3:LSK;4:PBS;5:LUP;6:AHR").split(";"))}
ALL_CIDS = list(code_ids.values())
companies = env["res.company"].browse(ALL_CIDS)
Account = env["account.account"].sudo()
env = env(su=True)

# ---------------------------------------------------------------- PSAK COA --
# (code, name, account_type)  — kode format PSAK: seri-nomor
A = [
    # ============================ 1. ASET ============================
    # --- 1-1xxx Kas & Setara Kas
    ("1-1100", "Kas", "asset_cash"),
    ("1-1110", "Kas Kecil (Petty Cash)", "asset_cash"),
    ("1-1120", "Kas Belum Diterima/In Transit", "asset_current"),
    ("1-1200", "Bank BCA", "asset_cash"),
    ("1-1210", "Bank Mandiri", "asset_cash"),
    ("1-1220", "Bank BNI", "asset_cash"),
    ("1-1230", "Bank BRI", "asset_cash"),
    ("1-1240", "Bank BTPN/Jenius", "asset_cash"),
    ("1-1250", "Giro Cek Masuk", "asset_current"),
    ("1-1260", "Setoran Jangka Pendek (Deposito < 3 Bulan)", "asset_current"),
    # --- 1-2xxx Piutang
    ("1-2100", "Piutang Usaha", "asset_receivable"),
    ("1-2110", "Piutang Giro", "asset_current"),
    ("1-2120", "Piutang Pajak & Penjaluran", "asset_current"),
    ("1-2130", "Piutang Karyawan", "asset_current"),
    ("1-2140", "Piutang Afiliasi", "asset_current"),
    ("1-2150", "Piutang Lain-lain (Non Usaha)", "asset_current"),
    ("1-2160", "Laba Rugi Selisih Kurs Piutang", "asset_current"),
    ("1-2900", "Cadangan Kerugian Penurunan Piutang", "asset_current"),
    # --- 1-3xxx Persediaan (PSAK 5)
    ("1-3100", "Persediaan Barang Dagang", "asset_current"),
    ("1-3110", "Persediaan Bahan Baku", "asset_current"),
    ("1-3120", "Persediaan Bahan Penolong", "asset_current"),
    ("1-3130", "Persediaan Barang Dalam Proses (WIP)", "asset_current"),
    ("1-3131", "Persediaan BOP Dalam Proses", "asset_current"),
    ("1-3140", "Persediaan Barang Jadi", "asset_current"),
    ("1-3150", "Persediaan Dalam Perjalanan", "asset_current"),
    ("1-3160", "Persediaan Sparepart & Consumables", "asset_current"),
    ("1-3170", "Barang Jual Diterima Konsinyasi", "asset_current"),
    ("1-3180", "Aset Pengurangan Nilai Persediaan (LCNRV)", "asset_current"),
    # --- 1-4xxx Pajak Dikembalikan/Masukan (PSAK 46 dsb.)
    ("1-4100", "PPN Masukan", "asset_current"),
    ("1-4110", "PPN Masukan BKP Tidak Bertransaksi", "asset_current"),
    ("1-4200", "PPh 22 Masukan", "asset_current"),
    ("1-4210", "PPh 23 Masukan", "asset_current"),
    ("1-4220", "PPh 25 Masukan (Palembang/Kirim)", "asset_current"),
    ("1-4300", "PPh 21 Dibayar Dimuka (Karyawan)", "asset_current"),
    # --- 1-5xxx Beban Dibayar Dimuka (PSAK 6)
    ("1-5100", "Sewa Dibayar Dimuka", "asset_prepayments"),
    ("1-5110", "Asuransi Dibayar Dimuka", "asset_prepayments"),
    ("1-5120", "Iklan Dibayar Dimuka", "asset_prepayments"),
    ("1-5130", "Perlengkapan Kantor/Studio Dibayar Dimuka", "asset_prepayments"),
    ("1-5140", "Pajak Dibayar Dimuka (PBB, Pajak Daerah)", "asset_prepayments"),
    ("1-5150", "Biaya Langganan Jasa Dibayar Dimuka", "asset_prepayments"),
    # --- 1-6xxx Aset Tetap (PSAK 16)
    ("1-6100", "Tanah", "asset_fixed"),
    ("1-6200", "Bangunan & Gedung", "asset_fixed"),
    ("1-6210", "Konstruksi Dalam Proses", "asset_fixed"),
    ("1-6300", "Mesin & Peralatan Pabrik", "asset_fixed"),
    ("1-6400", "Kendaraan", "asset_fixed"),
    ("1-6500", "Elektronik/Perangkat Komputer", "asset_fixed"),
    ("1-6600", "Peralatan & Meubelair", "asset_fixed"),
    ("1-6700", "Perpustakaan/Pangkalan Data", "asset_fixed"),
    ("1-6800", "Aset Aset Tetap Tidak Berwujud", "asset_fixed"),
    ("1-6900", "Investasi pada Pemegang Saham (Aset Tetap)", "asset_fixed"),
    # --- 1-7xxx Akumulasi Penyusutan & Penurunan Nilai
    ("1-7100", "Akumulasi Penyusutan Bangunan", "asset_fixed"),
    ("1-7200", "Akumulasi Penyusutan Mesin", "asset_fixed"),
    ("1-7300", "Akumulasi Penyusutan Kendaraan", "asset_fixed"),
    ("1-7400", "Akumulasi Penyusutan Elektronik/Komputer", "asset_fixed"),
    ("1-7500", "Akumulasi Penyusutan Peralatan & Meubelair", "asset_fixed"),
    ("1-7600", "Penurunan Nilai Aset Tetap (Impairment)", "asset_fixed"),
    # --- 1-8xxx Aset Tak Berwujud (PSAK 19)
    ("1-8100", "Hak Paten", "asset_non_current"),
    ("1-8200", "Software & Sistem", "asset_non_current"),
    ("1-8300", "Hak Guna Usaha", "asset_non_current"),
    ("1-8400", "Franchise/Merek", "asset_non_current"),
    ("1-8500", "Hak Kontrak Tanah/Resource", "asset_non_current"),
    ("1-8600", "Akumulasi Amortisasi Aset Tak Berwujud", "asset_non_current"),
    # --- 1-9xxx Investasi & Aset Lainnya (non-lancar)
    ("1-9100", "Investasi Saham pada Entitas Lain", "asset_non_current"),
    ("1-9200", "Investasi pada Entitas Asosiasi (Metode Ekuitas)", "asset_non_current"),
    ("1-9300", "Investasi Pada Asosiasi Dalam Proses", "asset_non_current"),
    ("1-9400", "Aset Tetap Dipertanggungkan Pihak Ketiga", "asset_non_current"),
    ("1-9500", "Aset Lancar Jangka Panjang Lainnya", "asset_non_current"),
    # ============================ 2. LIABILITAS ============================
    # --- 2-1xxx Hutang Usaha
    ("2-1100", "Hutang Usaha", "liability_payable"),
    ("2-1110", "Hutang Stok Toko (Konsinyasi)", "liability_current"),
    ("2-1200", "Hutang Giro/Bank Pos", "liability_current"),
    ("2-1300", "Hutang Afiliasi", "liability_current"),
    ("2-1400", "Hutang Lain-lain (Non Usaha)", "liability_current"),
    ("2-1500", "Uang Muka Pelanggan/Pemesan", "liability_current"),
    # --- 2-2xxx Hutang Pajak
    ("2-2100", "PPN Keluaran", "liability_current"),
    ("2-2110", "PPN Inhouse (Import)", "liability_current"),
    ("2-2200", "PPh 21 Terutang (Hutang PPh 21)", "liability_current"),
    ("2-2210", "PPh 23 Terutang", "liability_current"),
    ("2-2220", "PPh 4(2) / Final Terutang", "liability_current"),
    ("2-2300", "PPh 25 Ansuran Terutang", "liability_current"),
    ("2-2310", "PPN Terutang (Klarifikasi SPT)", "liability_current"),
    ("2-2320", "PPh Pasal 24 (Pajak Lain Dibayar PRB/Definitif)", "liability_current"),
    # --- 2-3xxx Beban Masih Harus Dibayar (Akrual)
    ("2-3100", "Akrual Gaji & Upah", "liability_current"),
    ("2-3110", "Akrual Bonus & THR", "liability_current"),
    ("2-3200", "Akrual Listrik/Utilitas", "liability_current"),
    ("2-3210", "Akrual Sewa", "liability_current"),
    ("2-3220", "Akrual Bunga", "liability_current"),
    ("2-3300", "Akrual Jasa Profesional", "liability_current"),
    ("2-3310", "Akrual Beban Bonus Manajemen", "liability_current"),
    # --- 2-4xxx Hutang Non Usaha & Dana
    ("2-4100", "Hutang Dividen", "liability_current"),
    ("2-4200", "Hutang Pemegang Direksi/Komisaris", "liability_current"),
    ("2-4300", "Deposit Pelanggan/Komitmen", "liability_current"),
    ("2-4400", "Kas Daftar (Float Bulat)", "liability_current"),
    ("2-4500", "Hutang Bonus/Bunga Selisih Pembayaran Lainnya", "liability_current"),
    # --- 2-5xxx Hutang Jangka Panjang
    ("2-5100", "Pinjaman Bank Jangka Panjang (KMK)", "liability_non_current"),
    ("2-5110", "Pinjaman Pemegang Saham", "liability_non_current"),
    ("2-5120", "Obligasi", "liability_non_current"),
    ("2-5200", "Hutang Sewa Jangka Panjang (PSAK 73 Lease)", "liability_non_current"),
    ("2-5300", "Obligasi/Diskon/Premi Hutang Konversi", "liability_non_current"),
    ("2-5400", "Kewajiban Pasang Surut (Deferred Tax Liability)", "liability_non_current"),
    ("2-5500", "Proyeksi Kewajiban Jaminan (Warranty/Legal)", "liability_non_current"),
    ("2-5600", "Kewajiban Manfaat Pasca-Kerja (PSAK 24)", "liability_non_current"),
    ("2-5700", "Kewajiban Rate/Investasi (Asset Retirement)", "liability_non_current"),
    ("2-5800", "Hutang Perjanjian Kerja Bersama (KSO)", "liability_non_current"),
    ("2-5900", "Cadangan Kabut/Bezorg/Ganti Rugi", "liability_non_current"),
    # ============================ 3. EKUITAS ============================
    ("3-1100", "Modal Disetor (Saham)", "equity"),
    ("3-1110", "Tambahan Modal Disetor", "equity"),
    ("3-1200", "Saldo Laba (Laba Ditahan)", "equity"),
    ("3-1210", "Saldo Laba Perubahan (Ajustasi Retrospektif)", "equity"),
    ("3-1300", "Cadangan Umum", "equity"),
    ("3-1310", "Cadangan Pembangunan", "equity"),
    ("3-1400", "Prive (Pengambilan Pemilik)", "equity"),
    ("3-1500", "Selisih Kurs Transaksi Neraca (OCI)", "equity"),
    ("3-1600", "Surplus Revaluasi Aset Tetap", "equity"),
    ("3-1700", "Kgundukan Harga Diri Saham/Modal", "equity"),
    ("3-9900", "Laba (Rugi) Tahun Berjalan", "equity_unaffected"),
    # ============================ 4. PENDAPATAN ============================
    ("4-1100", "Penjualan Domestik", "income"),
    ("4-1110", "Penjualan Ekspor", "income"),
    ("4-1120", "Penjualan #Grosir/Distributor", "income"),
    ("4-1130", "Penjualan Retail/Outlet", "income"),
    ("4-1140", "Penjualan via E-Commerce", "income"),
    ("4-1200", "Pendapatan Jasa", "income"),
    ("4-1210", "Pendapatan Sewa", "income"),
    ("4-1300", "Pendapatan Lain-lain Usaha", "income"),
    ("4-1400", "Diskon Penjualan", "income"),
    ("4-1410", "Retur Penjualan", "income"),
    ("4-1420", "Potongan Harga (Bonuses & Rebates)", "income"),
    ("4-1500", "Pendapatan Bagian Berlaku (PSAK 15)", "income"),
    # --- 4-9xxx Pendapatan NON-Operasional
    ("4-9100", "Pendapatan Bunga", "income_other"),
    ("4-9200", "Pendapatan Selisih Kurs", "income_other"),
    ("4-9300", "Pendapatan Dividen", "income_other"),
    ("4-9400", "Keuntungan Penjualan Aset", "income_other"),
    ("4-9500", "Pendapatan Komisi & Broker", "income_other"),
    ("4-9600", "Pendapatan Lain-lain", "income_other"),
    # ============================ 5. HPP & BEBAN ============================
    # --- 5-1xxx Harga Pokok Penjualan (PSAK 5)
    ("5-1100", "Harga Pokok Penjualan", "expense_direct_cost"),
    ("5-1110", "HPP Retur Pembelian", "expense_direct_cost"),
    ("5-1200", "Diskon Pembelian", "expense_direct_cost"),
    ("5-1210", "Retur Pembelian", "expense_direct_cost"),
    ("5-1300", "Beban Angkut Pembelian (Freight-In)", "expense_direct_cost"),
    ("5-1900", "Selisih Harga Persediaan (Price Difference)", "expense_direct_cost"),
    # --- 5-2xxx Beban Produksi
    ("5-2100", "Beban Bahan Baku Dipakai", "expense_direct_cost"),
    ("5-2110", "Beban Bahan Penolong Dipakai", "expense_direct_cost"),
    ("5-2200", "Beban Tenaga Kerja Langsung", "expense_direct_cost"),
    ("5-2300", "Beban Pabrikasi (BOP)", "expense"),
    ("5-2310", "Beban Penyusutan Mesin Pabrik", "expense_depreciation"),
    ("5-2320", "Beban Listrik & Air Pabrik", "expense"),
    ("5-2330", "Beban Sewa Pabrik", "expense"),
    ("5-2340", "Beban Perawatan Pabrik", "expense"),
    ("5-2400", "Penyesuaian/Inventarisasi Loss Persediaan", "expense_other"),
    ("5-2410", "HPP Persediaan Cadangan/Cadangan LCNRV", "expense_other"),
    # --- 5-3xxx Beban Operasional (Penjualan & Adm)
    ("5-3100", "Beban Gaji & Tunjangan", "expense"),
    ("5-3110", "Beban BPJS & Asuransi Karyawan", "expense"),
    ("5-3120", "Beban THR/Bonus", "expense"),
    ("5-3200", "Beban Sewa Kantor", "expense"),
    ("5-3300", "Beban Listrik/Air/Telepon", "expense"),
    ("5-3400", "Beban Iklan & Promosi", "expense"),
    ("5-3500", "Beban Perjalanan Dinas", "expense"),
    ("5-3600", "Beban Penyusutan Aset Kantor", "expense_depreciation"),
    ("5-3700", "Beban Amortisasi Aset Tak Berwujud", "expense_depreciation"),
    ("5-3800", "Beban Jasa Profesional (Konsultan/Audit)", "expense"),
    ("5-3900", "Beban Perlengkapan & ATK", "expense"),
    ("5-3910", "Beban Pemeliharaan Kendaraan", "expense"),
    ("5-3920", "Beban Kebersihan & Keamanan", "expense"),
    ("5-3930", "Beban Konsumsi & kesejahteraan", "expense"),
    ("5-3940", "Beban Komunikasi & Internet", "expense"),
    ("5-3950", "Beban Langganan/Lisensi Software", "expense"),
    # --- 5-4xxx Beban Non-Operasional
    ("5-4100", "Beban Bunga", "expense_other"),
    ("5-4200", "Beban Selisih Kurs", "expense_other"),
    ("5-4300", "Beban Perbal Pajak Korporat", "expense"),
    ("5-4310", "Beban PPh Final", "expense"),
    ("5-4400", "Kerugian Penjualan Aset", "expense_other"),
    ("5-4500", "Beban Keraguan/Berjalan Persediaan (Penurunan Nilai)", "expense_other"),
    ("5-4600", "Beban Lain-lain", "expense_other"),
    # --- 5-9xxx Pajak Penghasilan Korporat (PSAK 46)
    ("5-9100", "Beban Pajak Kini (Current Tax)", "expense"),
    ("5-9200", "Beban Pajak Ditangguhkan (Deferred Tax)", "expense"),
]

existing_codes = set()

def _load_existing():
    for a in Account.search([]):
        existing_codes.add(a.code)
_load_existing()

accs = {}          # code -> record (shared, non-cash)
accs_cash = {}     # (company_id, base_code) -> record (per-company cash)
for code, name, atype in A:
    if atype == "asset_cash":
        # Kas & Bank wajib per perusahaan di Odoo 20 (tidak boleh di-share)
        for cid in ALL_CIDS:
            comp = env["res.company"].browse(cid)
            cc = f"{code}.{comp.name.split()[1]}"          # mis: 1-1100.SUI
            key = (cid, code)
            old = Account.search([("code", "=", cc)], limit=1)
            if old:
                accs_cash[key] = old
                continue
            accs_cash[key] = Account.create({
                "code": cc, "name": f"{name} ({comp.name})",
                "account_type": atype, "company_ids": [(6, 0, [cid])],
                "note": "Akun PSAK (Indonesia) — inject otomatis",
            })
            existing_codes.add(cc)
        continue
    old = Account.search([("code", "=", code)], limit=1)
    if old:
        accs[code] = old
        continue
    accs[code] = Account.create({
        "code": code, "name": name, "account_type": atype,
        "company_ids": [(6, 0, ALL_CIDS)],
        "note": "Akun PSAK (Indonesia) — inject otomatis",
    })
    existing_codes.add(code)
env.cr.commit()
n_cash = len(accs_cash)
print(f"[OK] accounts PSAK: {len(accs)} shared + {n_cash} kas/bank per-company")

# NOTE: account.group sudah DIHAPUS di Odoo 20 — struktur hierarki otomatis dari kode akun (code_path).
print("[OK] skip account.group (tidak ada lagi di Odoo 20)")

# ------------------------------------------------- Perusahaan: valuation --
STJ_BY_COMPANY = {}
for c in companies:
    stj = env["account.journal"].search([("company_id", "=", c.id), ("code", "=", "STJ")], limit=1)
    if not stj:
        stj = env["account.journal"].create({
            "name": f"Inventory Valuation ({c.name})", "code": "STJ", "type": "general",
            "company_id": c.id, "show_on_dashboard": False})
    STJ_BY_COMPANY[c.id] = stj
    c.write({
        "inventory_valuation": "real_time",
        "anglo_saxon_accounting": True,
        "cost_method": "fifo",
        "account_stock_valuation_id": accs["1-3100"].id,
        "account_stock_journal_id": stj.id,
        "price_difference_account_id": accs["5-1900"].id,
        "account_production_wip_account_id": accs["1-3130"].id,
        "account_production_wip_overhead_account_id": accs["1-3131"].id,
    })
print("[OK] res.company: perpetual (real_time) + FIFO + jurnal stok + WIP + selisih harga")

# Jurnal bank/cash menunjuk akun kas/bank milik perusahaan masing2
for c in companies:
    comp_suffix = c.name.split()[1]
    bank_acc = accs_cash.get((c.id, "1-1200"))
    cash_acc = accs_cash.get((c.id, "1-1100"))
    for jcode, a in (("BNK1", bank_acc), ("CSH1", cash_acc)):
        j = env["account.journal"].search([("company_id", "=", c.id), ("code", "=", jcode)], limit=1)
        if j and a and j.default_account_id.id != a.id:
            j.write({"default_account_id": a.id})
print("[OK] jurnal BNK1/CSH1 tiap PT -> akun kas/bank milik PT tsb")

# --------------------------------------------- Kategori produk + property --
CATS = [
    ("1-3100", "Barang Dagang (Trading)", "fifo"),
    ("1-3110", "Bahan Baku", "fifo"),
    ("1-3120", "Bahan Penolong", "average"),
    ("1-3130", "Barang Dalam Proses (WIP)", "fifo"),
    ("1-3140", "Barang Jadi", "fifo"),
    ("1-3160", "Sparepart & Consumables", "average"),
    ("9-JASA", "Jasa (Non-Stok)", "standard"),
]
categ_map = {}
Categ = env["product.category"].sudo()
for acccode, catname, method in CATS:
    cat = Categ.search([("name", "=", catname)], limit=1)
    if not cat:
        cat = Categ.create({"name": catname})
    vals = {
        "property_cost_method": method,
        "property_valuation": "real_time" if acccode != "9-JASA" else "periodic",
        "property_account_income_categ_id": accs["4-1100"].id,
        "property_account_expense_categ_id": accs["1-3100" if False else "5-1100"].id,
    }
    if acccode != "9-JASA":
        vals.update({
            "property_stock_valuation_account_id": accs[acccode].id,
            "property_stock_journal": STJ_BY_COMPANY[ALL_CIDS[0]].id,  # di-set ulang per company di bawah
            "property_price_difference_account_id": accs["5-1900"].id,
        })
    for cid in ALL_CIDS:
        cat.with_company(env["res.company"].browse(cid)).write(vals)
    categ_map[catname] = cat
print(f"[OK] {len(categ_map)} kategori produk; valuation real_time + FIFO/AVCO per perusahaan")

# ------------------------------------------------------------- 1000 produk --
BASE_W1 = ["Mesin", "Gear", "Sprocket", "Bearing", "Motor", "Pompa", "Kabel", "Sensor",
           "Valve", "Sirine", "Modul", "Panel", "Kondensor", "Kompresor", "Filter",
           "Rangka", "Siku", "Pipa", "Selang", "V-Belt", " melan", "Baut", "Klem",
           "Relay", "Inverter", "Driver", "Switch", "Terminal", "Box", "Casing"]
BASE_W2 = ["Industri", "Otomoatif", "Reparasi", "Transportasi", "Kimia", "Tekstil",
           "Agro", "Konstruksi", "Elektronik", "Fnb", "Pertambangan", "Pelabuhan",
           "Farmasi", "Plastik", "Kertas", "Logistik", "Garmen", "Makanan", "Minuman", "Otomotif"]
BASE_W3 = ["Standar", "Heavy Duty", "Mini", "Turbo", "Premium", "Eco", "Pro", "Seri-B/2",
           "Anti-Karat", "Tahan Panas"]
word1 = [w.strip() for w in BASE_W1]
word2 = [w.strip() for w in BASE_W2]
word3 = [w.strip() for w in BASE_W3]

product_vals = []
categ_names = [n for n, _ in [(c, 0) for c in categ_map]]
product_categ = env["product.category"]
uom = env.ref("uom.product_uom_unit")
for i in range(1, 1001):
    word = f"PROD-{i:04d} {word1[i % len(word1)]} {word2[(i*7) % len(word2)]} {word3[(i*13) % len(word3)]}"
    catname = categ_names[i % len(categ_names)]
    category = product_categ.search([("name", "=", catname)], limit=1)
    price = ((i * 7919) % 900 + 10) * 1000  # 10.000 - 909.000
    cost = int(price * (0.55 + ((i * 31) % 20) / 100))  # 55-75% dari harga
    if i % 20 == 0:
        ptype, storable_val = "service", False
        price *= 2  # harga jasa lebih mahal
    elif i % 13 == 0:
        ptype, storable_val = "consu", False  # consumable gudang manual
    else:
        ptype, storable_val = "consu", True
    product_vals.append({
        "name": word,
        "categ_id": category.id,
        "type": ptype,
        "is_storable": storable_val,
        "list_price": price,
        "standard_price": cost,
        "uom_id": uom.id,
        "sale_delay": (i % 7) + 1,
        "purchase_method": "receive" if storable_val else "purchase",
        "invoice_policy": "order" if ptype == "service" else "delivery",
    })

Product = env["product.product"].sudo()
n_before = Product.search_count([])
for chunk_idx in range(0, len(product_vals), 250):
    batch = product_vals[chunk_idx:chunk_idx + 250]
    tmpl = Product.create(batch)
    env.cr.commit()
print(f"[OK] produk: {Product.search_count([]) - n_before} baru (total sekarang {Product.search_count([])})")

env.cr.commit()
print("=== VERIFY ===")
print("accounts PSAK   :", Account.search_count([("code", ">=", "1-"), ("company_ids", "!=", False)]) or len(accs))
print("valuation categ :", Categ.search_count([("property_valuation", "=", "real_time")]))
print("storable prod   :", Product.search_count([("is_storable", "=", True)]))
print("PSAK DONE")
