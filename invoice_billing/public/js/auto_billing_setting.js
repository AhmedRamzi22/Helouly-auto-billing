frappe.ui.form.on("Auto Billing Setting", {
	refresh(frm) {
		frm.add_custom_button(__("Send Test Notification"), () => {
			frappe.call({
				method: "invoice_billing.notification.send_test_notification",
				freeze: true,
				freeze_message: __("Sending test notification..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __(
								"Test sent to {0} ({1} customer(s), {2} log(s) created). Check your notifications and email.",
								[r.message.user, r.message.count, r.message.logged]
							),
							indicator: "green",
						});
					}
				},
			});
		});
	},
});
