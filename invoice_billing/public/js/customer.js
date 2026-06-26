frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(
			__("Generate Next Invoice"),
			() => {
				frappe.call({
					method: "invoice_billing.customer.create_next_invoice",
					args: { customer: frm.doc.name },
					freeze: true,
					freeze_message: __("Generating invoice..."),
					callback(r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Invoice {0} created", [r.message]),
								indicator: "green",
							});
							frappe.set_route("Form", "Sales Invoice", r.message);
						}
					},
				});
			},
			__("Auto Invoice")
		);
	},

	before_custom_customer_invoices_remove(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row && row.invoiced) {
			frappe.msgprint({
				title: __("Not Allowed"),
				indicator: "red",
				message: __("You cannot delete an invoiced row ({0}).", [
					row.invoice_name || row.invoice_date,
				]),
			});
			// Abort the row removal.
			throw __("Cannot delete an invoiced row");
		}
	},
});

// Keep Billing Item amount = qty * rate live in the grid.
frappe.ui.form.on("Customer Billing Item", {
	qty: calculate_amount,
	rate: calculate_amount,
});

function calculate_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}
