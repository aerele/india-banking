/* global INDICATORS */
INDICATORS["Payment Ordered"] = "blue";

frappe.listview_settings["Payment Request"] = {
	...frappe.listview_settings["Payment Request"],
	onload: function (listview) {
		$(".page-head").after(
			`<div class="form-message-container">
				<div class="form-message border-bottom yellow">
					<div>
						<b>Warning: </b>The Adhoc Payment Request feature is deprecated. Please create a Payment Entry and pull it into the Payment Order instead.
					</div>
				</div>
			</div>
			`
		);
	},
};
