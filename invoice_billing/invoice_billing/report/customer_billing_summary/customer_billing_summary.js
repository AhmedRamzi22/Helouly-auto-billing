// Copyright (c) 2026, ramzi and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Billing Summary"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "frequency",
			label: __("Frequency"),
			fieldtype: "Select",
			options: ["", "Monthly", "Quarterly", "Semi-Annually", "Yearly"],
		},
	],
};
