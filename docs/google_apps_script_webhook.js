/**
 * Google Apps Script — Intake Webhook Forwarder
 *
 * Paste this into the Script Editor of the Google Sheet linked to your intake form.
 * (Extensions → Apps Script)
 *
 * SETUP:
 *   1. Replace WEBHOOK_URL with your deployed Flask endpoint.
 *   2. Replace SHARED_SECRET with the value you set in INTAKE_WEBHOOK_SECRET (.env).
 *      Leave blank to skip signature verification during local dev.
 *   3. Replace COLUMN_KEYS with the snake_case keys matching your vertical config
 *      intake_questions in the same order as your Google Form fields.
 *   4. Click "Save", then run setupTrigger() once to create the form trigger.
 *
 * NOTE: If running locally, expose Flask via:  ngrok http 5000
 *       Then use the ngrok HTTPS URL as WEBHOOK_URL.
 */

const WEBHOOK_URL   = "https://your-domain.com/intake/webhook";   // ← CHANGE THIS
const SHARED_SECRET = "";   // ← CHANGE THIS (match INTAKE_WEBHOOK_SECRET in .env)

// Column order must match your Google Form field order exactly.
const COLUMN_KEYS = [
  "timestamp",        // col 0 — added automatically by Google Forms; can be skipped
  "full_name",        // col 1
  "email",            // col 2
  "phone",            // col 3
  "occupation",       // col 4
  "annual_income_range",    // col 5
  "primary_financial_goal", // col 6
  "existing_investments",   // col 7
  "risk_tolerance",         // col 8
  "key_concern",            // col 9
];

function onFormSubmit(e) {
  const values = e.values;                    // array of cell values in column order
  const payload = { _source: "google_forms" };

  COLUMN_KEYS.forEach(function(key, i) {
    if (key !== "timestamp" && values[i] !== undefined) {
      payload[key] = values[i];
    }
  });

  const body = JSON.stringify(payload);
  const options = {
    method: "post",
    contentType: "application/json",
    payload: body,
    muteHttpExceptions: true,
  };

  // Attach HMAC-SHA256 signature if a shared secret is configured.
  if (SHARED_SECRET) {
    const sig = computeHmacSha256(SHARED_SECRET, body);
    options.headers = { "X-Intake-Signature": sig };
  }

  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    Logger.log("Webhook response: " + response.getContentText());
  } catch (err) {
    Logger.log("Webhook error: " + err.toString());
  }
}

function computeHmacSha256(secret, message) {
  const key  = Utilities.computeHmacSha256Signature(message, secret);
  return key.map(function(b) {
    return ("0" + (b & 0xff).toString(16)).slice(-2);
  }).join("");
}

/** Run this once in the Apps Script editor to attach the form submit trigger. */
function setupTrigger() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ScriptApp.newTrigger("onFormSubmit")
    .forSpreadsheet(ss)
    .onFormSubmit()
    .create();
  Logger.log("Trigger created successfully.");
}
