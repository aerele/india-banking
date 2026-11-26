frappe.pages["india-banking"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("India Banking"),
		single_column: true,
	});
	set_india_banking_page_title(wrapper.page);

	// hot reload in development
	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_india_banking(wrapper));
	}
};

frappe.pages["india-banking"].on_page_show = function (wrapper) {
	load_india_banking(wrapper);
};

function set_india_banking_page_title(page) {
	page.set_title(__("India Banking"));

	let $title_text = page.get_title_area().find(".title-text");
	if (!$title_text.find("img.india-banking-title-logo").length) {
		$title_text.prepend(
			`<img src="/assets/india_banking/images/india-banking-logo.svg" class="india-banking-title-logo" alt="" style="width: 20px; height: 20px; border-radius: 5px; margin-right: 6px; vertical-align: -4px;" />`
		);
	}
}

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
