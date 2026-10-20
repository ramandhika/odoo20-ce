"""account.move override: starting sequence sesuai format kebutuhan CIE.
  [company code]/[short code]/[YYYY]/[MM]/[00001]
Counter reset TAHUNAN: mekanisme di Odoo 20 CE:
  format YYYY/MM  -> deduksi reset 'month',
  tapi numbering dilanjutkan antar-bulan karena prefix-part + unique-index retry
  (`_locked_increment`) melanjutkan nomor terakhir pada tahun yang sama;
  ganti tahun baru -> prefix yg names berpartibilitas -> autofresh '00001'.
"""
from odoo import fields, models

DEFAULT_SHORT_CODES = {
    "sale": "INV",
    "sale_refund": "RINV",
    "purchase": "BILL",
    "purchase_refund": "RBILL",
    "bank_payment": "PBNK",
    "bank": "BNK",
    "cash": "BNK",
    "general": "JMO",
}


class AccountJournal(models.Model):
    _inherit = "account.journal"

    cie_short_code = fields.Char(
        string="Short Code",
        help="Kode singkat numbering, mis: INV, BILL, RINV, RBILL, PBNK, BNK, JMO."
             " Kosongkan agar diambil otomatis dari tipe jurnal.",
    )

    def cie_compute_short_code(self, move):
        """Return short code string untuk penomoran dokumen di journal ini."""
        self.ensure_one()
        if self.cie_short_code:
            return self.cie_short_code
        if move and move._name == "account.move":
            is_refund = move.is_refund()
            is_payment = bool(move.origin_payment_id) or bool(
                move.env.context.get("is_payment"))
        else:
            is_refund, is_payment = False, bool(
                isinstance(move, dict) and move.get("is_payment"))
        if self.type == "sale":
            return DEFAULT_SHORT_CODES["sale_refund" if is_refund else "sale"]
        if self.type == "purchase":
            return DEFAULT_SHORT_CODES["purchase_refund" if is_refund else "purchase"]
        if self.type in ("bank", "cash"):
            return DEFAULT_SHORT_CODES["bank_payment" if is_payment else "bank"]
        if self.type == "general":
            return DEFAULT_SHORT_CODES["general"]
        return self.code or "DOC"


class AccountMove(models.Model):
    _inherit = "account.move"

    def _cie_company_code(self):
        self.ensure_one()
        param = self.env["ir.config_parameter"].sudo()
        raw = param.get_str("document_sequence.company_codes") or ""
        mapping = {}
        try:
            mapping = dict(p.split(":", 1) for p in raw.split(";") if ":" in p)
        except ValueError:
            pass
        return mapping.get(str(self.company_id.id)) or str(self.company_id.id)

    def _get_starting_sequence(self):
        """Jamin nomor pertama pertamakali posting sesuai format CIE:
        [COMP]/[SHORT]/[YYYY]/[MM]/00000"""
        self.ensure_one()
        year_part, move_date, _is_staggered = self._get_sequence_date_info()
        short = self.journal_id.cie_compute_short_code(self)
        return "%s/%s/%s/%02d/00000" % (
            self._cie_company_code(), short, year_part, move_date.month)

    def _get_next_sequence_format(self):
        """Counter TAHUNAN walau format menampilkan MM:
        saat dokumen baru di bulan baru (seq=0), lanjutkan dari max seq
        se-tahun (prefix COMP/SHORT/YYYY/*) — bukan reset ke 00 setiap bul.
        """
        format_string, format_values = super()._get_next_sequence_format()
        if format_values.get("seq") == 0 and self.journal_id:
            year = format_values.get("year")
            comp = self._cie_company_code()
            short = self.journal_id.cie_compute_short_code(self)
            if year:
                prefix_like = "%s/%s/%04d/%%" % (comp, short, year)
                self.env.cr.execute(
                    "SELECT MAX(sequence_number) FROM account_move WHERE journal_id = %s "
                    "AND sequence_prefix LIKE %s", [self.journal_id.id, prefix_like])
                max_seq = self.env.cr.fetchone()[0] or 0
                if max_seq:
                    format_values["seq"] = max_seq
        return format_string, format_values
