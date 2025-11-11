// Copyright (c) 2022, djs4000 and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Settings', {
  refresh(frm) {
    update_waha_webhook_url(frm);
  },

  session(frm) {
    update_waha_webhook_url(frm);
  }
});

function update_waha_webhook_url(frm) {
  if (!frm.doc) {
    return;
  }

  if (!frm.doc.session) {
    if (frm.doc.waha_webhook_url) {
      frm.set_value('waha_webhook_url', '');
    }
    return;
  }

  frappe.call({
    method: 'frappe_whatsapp_waha.utils.waha_webhook.get_waha_webhook_url',
    args: {
      session: frm.doc.session
    }
  }).then((response) => {
    if (response && response.message && frm.doc.waha_webhook_url !== response.message) {
      frm.set_value('waha_webhook_url', response.message);
    }
  });
}
