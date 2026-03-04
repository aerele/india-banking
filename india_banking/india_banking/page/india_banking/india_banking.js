frappe.pages["india-banking"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("India Banking"),
		single_column: true,
	});

	// hot reload in development
	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_india_banking(wrapper));
	}
};

frappe.pages["india-banking"].on_page_show = function (wrapper) {
	load_india_banking(wrapper);
};

function load_india_banking(wrapper) {
	let $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();

	frappe.require("india_banking.bundle.js").then(() => {
		frappe.india_banking = new frappe.ui.IndiaBanking({
			wrapper: $parent,
			page: wrapper.page,
		});
	});
}
