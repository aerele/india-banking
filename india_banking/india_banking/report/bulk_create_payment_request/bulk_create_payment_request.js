// Copyright (c) 2025, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt
frappe.provide("erpnext.utils");

frappe.query_reports["Bulk Create Payment Request"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
      default: frappe.defaults.get_user_default("Company"),
    },
    {
      fieldname: "_for",
      label: __("For"),
      fieldtype: "Select",
      options: "Payables\nOrder Advance",
      reqd: 1,
      default: "Payables",
    },
    {
      fieldname: "report_date",
      label: __("Posting Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "finance_book",
      label: __("Finance Book"),
      fieldtype: "Link",
      options: "Finance Book",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "cost_center",
      label: __("Cost Center"),
      fieldtype: "Link",
      options: "Cost Center",
      get_query: () => {
        var company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            company: company,
          },
        };
      },
    },
    {
      fieldname: "party_account",
      label: __("Payable Account"),
      fieldtype: "Link",
      options: "Account",
      get_query: () => {
        var company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            company: company,
            account_type: "Payable",
            is_group: 0,
          },
        };
      },
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "ageing_based_on",
      label: __("Ageing Based On"),
      fieldtype: "Select",
      options: "Posting Date\nDue Date\nSupplier Invoice Date",
      default: "Due Date",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "range",
      label: __("Ageing Range"),
      fieldtype: "Data",
      default: "30, 60",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "payment_terms_template",
      label: __("Payment Terms Template"),
      fieldtype: "Link",
      options: "Payment Terms Template",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "party_type",
      label: __("Party Type"),
      fieldtype: "Autocomplete",
      options: get_party_type_options(),
      on_change: function () {
        frappe.query_report.set_filter_value("party", "");
        frappe.query_report.toggle_filter_display(
          "supplier_group",
          frappe.query_report.get_filter_value("party_type") !== "Supplier"
        );
      },
    },
    {
      fieldname: "party",
      label: __("Party"),
      fieldtype: "MultiSelectList",
      options: "party_type",
      get_data: function (txt) {
        if (!frappe.query_report.filters) return;

        let party_type = frappe.query_report.get_filter_value("party_type");
        if (!party_type) return;

        return frappe.db.get_link_options(party_type, txt);
      },
    },
    {
      fieldname: "supplier_group",
      label: __("Supplier Group"),
      fieldtype: "Link",
      options: "Supplier Group",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "group_by_party",
      label: __("Group By Supplier"),
      fieldtype: "Check",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "based_on_payment_terms",
      label: __("Based On Payment Terms"),
      fieldtype: "Check",
    },
    {
      fieldname: "show_remarks",
      label: __("Show Remarks"),
      fieldtype: "Check",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "show_future_payments",
      label: __("Show Future Payments"),
      fieldtype: "Check",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "for_revaluation_journals",
      label: __("Revaluation Journals"),
      fieldtype: "Check",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "ignore_accounts",
      label: __("Group by Voucher"),
      fieldtype: "Check",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "in_party_currency",
      label: __("In Party Currency"),
      fieldtype: "Check",
      depends_on: "eval: doc._for == 'Payables'",
    },
    {
      fieldname: "handle_employee_advances",
      label: __("Handle Employee Advances"),
      fieldtype: "Check",
      depends_on: "eval: doc._for == 'Payables'",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (data && data.bold) {
      value = value.bold();
    }
    return value;
  },
  get_datatable_options(options) {
    options.checkboxColumn = true;
    return options;
  },
  onload: function (report) {
    let switch_icon = `
		<div title="Switch to Bulk Update Payment Request">
		<svg class="icon  icon-md" style="" aria-hidden="true" >
			<use class="" href="#icon-change"></use>
		</svg>
		</div>`;
    let switch_element = frappe.query_report.page.add_inner_button(
      switch_icon,
      () => {
        frappe.set_route("query-report", "Bulk Update Payment Request", {
          company: frappe.query_report.get_filter_value("company"),
          transaction_date: [
            frappe.datetime.get_today(),
            frappe.datetime.get_today(),
          ],
        });
      }
    );
    if ($("#switch-button").length > 0) {
      $("#switch-button").remove();
      $(`[title="Bulk Create Payment Request"]`)
        .parent()
        .append(switch_element);
    } else {
      $(`[title="Bulk Create Payment Request"]`)
        .parent()
        .append(switch_element);
    }

    setTimeout(() => {
      $('[class="inner-group-button"]').hide();
      $('[data-label="Create%20Card"]').hide();
      let status_message = frappe.query_report.$status.html();
      let newStatus = status_message.replace(
        "click on Rebuild",
        "click on Rebuild or Generate New Report"
      );

      let new_message = `<div style="color: #ff4008;">${newStatus}</>`;
      frappe.query_report.$status.html(new_message);
    }, 1000);

    frappe.query_report.page.add_inner_button("Goto Payment Request", () => {
      frappe.set_route("List", "Payment Request");
    });

    report.page.add_inner_button(__("Accounts Payable Summary"), function () {
      var filters = report.get_values();
      frappe.set_route("query-report", "Accounts Payable Summary", {
        company: filters.company,
      });
    });

    report.page.add_action_item(__("Create Payment Request"), function () {
      let checked_rows_indexes = report.datatable?.rowmanager.getCheckedRows();
      let checked_rows = checked_rows_indexes?.map((i) => report.data[i]);

      if (!checked_rows) {
        return;
      }

      if (checked_rows && checked_rows.length === 0) {
        frappe.throw("Select one or more rows");
      }

      frappe.call({
        method:
          "india_banking.india_banking.report.bulk_create_payment_request.bulk_create_payment_request.create_bulk_payment_request",
        args: {
          invoices: checked_rows,
          filters: frappe.query_report.get_filter_values(),
        },
        async: false,
        callback: function (r) {
          $('[data-original-title="Reload Report"]').click();
        },
      });
    });
  },
};

// erpnext.utils.add_dimensions("Accounts Payable", 10);

function get_party_type_options() {
  let options = [];
  frappe.db
    .get_list("Party Type", {
      filters: { account_type: "Payable" },
      fields: ["name"],
    })
    .then((res) => {
      res.forEach((party_type) => {
        options.push(party_type.name);
      });
    });
  return options;
}

frappe.router.on("change", () => {
  window.location.reload();
});
