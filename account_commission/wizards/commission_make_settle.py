# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# Copyright 2022 Quartile
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models
from odoo.tools import float_compare


class CommissionMakeSettle(models.TransientModel):
    _inherit = "commission.make.settle"

    settlement_type = fields.Selection(
        selection_add=[("sale_invoice", "Sales Invoices")],
        ondelete={"sale_invoice": "cascade"},
    )

    def _get_agent_lines(self, agent, date_to_agent):
        """Filter sales invoice agent lines for this type of settlement."""
        if self.settlement_type != "sale_invoice":
            return super()._get_agent_lines(agent, date_to_agent)
        return self.env["account.invoice.line.agent"].search(
            [
                ("invoice_date", "<", date_to_agent),
                ("agent_id", "=", agent.id),
                ("settled", "=", False),
            ],
            order="invoice_date",
        )

    def _prepare_settlement_line_vals(self, settlement, line):
        """Prepare extra settlement values when the source is a sales invoice agent
        line.
        """
        res = super()._prepare_settlement_line_vals(settlement, line)
        if self.settlement_type == "sale_invoice":
            lines = self._get_agent_lines(settlement.agent_id, settlement.date_to)
            total_sales = sum(lines.mapped("invoice_id.amount_untaxed"))
            agent_goal = settlement.agent_id.sales_goal
            company_goal = self.env.company.sales_goal
            if float_compare(total_sales, company_goal, precision_digits=2) >= 0 or float_compare(total_sales, agent_goal, precision_digits=2) >= 0:
                percentage = 1
            else:
                percentage_archived = (total_sales * 100) / agent_goal
                if float_compare(percentage_archived, 80, precision_digits=2) >= 0:
                    percentage = 0.8
                elif float_compare(percentage_archived, 40, precision_digits=2) >= 0:
                    percentage = percentage_archived / 100
                elif float_compare(percentage_archived, 40, precision_digits=2) == -1:
                    percentage = 0
            date_percentage = 1
            inv_line = line.object_id
            cust_line = inv_line.move_id.line_ids.filtered(lambda s: s.account_id.user_type_id.type == "receivable")
            days_to_payment = (max(cust_line.matched_credit_ids.mapped("max_date")) - inv_line.move_id.invoice_date_due).days
            if inv_line and days_to_payment > 90:
                date_percentage = 0.8
            elif inv_line and days_to_payment > 120:
                date_percentage = 0.6
            elif inv_line and days_to_payment > 150:
                date_percentage = 0.4
            elif inv_line and days_to_payment > 180:
                date_percentage = 0.2
            elif inv_line and days_to_payment > 181:
                date_percentage = 0
            settled_amount = line.amount * percentage * date_percentage
            res.update(
                {
                    "invoice_agent_line_id": line.id,
                    "date": line.invoice_date,
                    "commission_id": line.commission_id.id,
                    "settled_amount": settled_amount,
                }
            )
        return res
