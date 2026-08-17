import { createApp } from "vue";
import { createPinia } from "pinia";
import IndiaBankingComponent from "./IndiaBanking.vue";
import { registerGlobalComponents } from "./globals.js";

class IndiaBanking {
	constructor({ wrapper, page }) {
		this.$wrapper = $(wrapper);
		this.page = page;

		// this.page.set_indicator("Beta", "orange");

		this.init();
	}

	init() {
		this.setup_app();
	}

	setup_app() {
		// create a pinia instance
		let pinia = createPinia();

		// create a vue instance
		let app = createApp(IndiaBankingComponent);
		app.use(pinia);

		// register global components
		registerGlobalComponents(app);

		// mount the app
		this.$workflow_builder = app.mount(this.$wrapper.get(0));
	}
}

frappe.provide("frappe.ui");
frappe.ui.IndiaBanking = IndiaBanking;
export default IndiaBanking;
