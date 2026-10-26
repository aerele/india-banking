const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
	path.join(__dirname, "../india_banking/public/js/bank_account.js"),
	"utf8"
);

function setup(canRead, isNew = false) {
	let handlers;
	const calls = [];
	const context = {
		frappe: {
			ui: { form: { on: (_doctype, events) => (handlers = events) } },
			model: { can_read: (doctype) => {
				assert.equal(doctype, "India Banking Connector");
				return canRead;
			} },
			db: { get_value: (...args) => {
				calls.push(["read", ...args]);
				return Promise.resolve({ message: { fetch_bank_balance: 1, fetch_bank_statement: 1 } });
			} },
		},
	};
	vm.runInNewContext(source, context);
	const frm = {
		doc: { name: "TEST-BANK", __islocal: isNew },
		set_df_property: (...args) => calls.push(["field", ...args]),
		events: {
			add_balance_fetch_button: () => calls.push(["balance"]),
			add_statements_fetch_button: () => calls.push(["statements"]),
		},
	};
	return { handlers, frm, calls };
}

test("restricted bank account editors do not query connectors or receive banking actions", () => {
	const { handlers, frm, calls } = setup(false);
	handlers.add_bank_custom_buttons(frm);
	assert.deepEqual(calls, [["field", "bank_balance", "hidden", 1]]);
});

test("authorized users retain subscribed banking actions", async () => {
	const { handlers, frm, calls } = setup(true);
	handlers.add_bank_custom_buttons(frm);
	await Promise.resolve();
	assert.equal(calls[0][0], "read");
	assert.equal(calls[0][1], "India Banking Connector");
	assert.equal(calls[0][2], "TEST-BANK");
	assert.deepEqual(calls.slice(1), [["balance"], ["statements"]]);
});

test("unsaved bank accounts do not query connectors", () => {
	const { handlers, frm, calls } = setup(true, true);
	handlers.add_bank_custom_buttons(frm);
	assert.deepEqual(calls, []);
});
