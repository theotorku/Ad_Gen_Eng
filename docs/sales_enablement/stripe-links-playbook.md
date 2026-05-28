# ProPlan Solutions — Stripe Payments & Billing Playbook
### Step-by-Step Dashboard Setup for Frictionless, On-the-Call Closing

This playbook provides exact instructions for configuring Stripe to handle automated recurring billing. Use these configurations to create billing links that you can text or email to DFW HVAC prospects directly during your discovery call.

---

## 1. Product & Pricing Configuration

Create three separate Products in your Stripe Dashboard (`Product Catalog > Add Product`). Follow these naming and pricing parameters:

### Tier 1: ProPlan Starter
*   **Product Name:** `ProPlan Starter — Monthly Campaign Creative`
*   **Description:** `6 seasonally timed ad visual assets per month, delivered as a shared Google Drive folder.`
*   **Pricing model:** `Standard pricing`
*   **Price:** `$297.00`
*   **Billing period:** `Monthly (Recurring)`
*   **Tax behavior:** `Amortized / Excluded (depending on local Texas services tax)`

### Tier 2: ProPlan Campaign *(Anchor Offer)*
*   **Product Name:** `ProPlan Campaign — Monthly Campaign-in-a-Box`
*   **Description:** `10 ad visual assets (3 angles), custom multi-channel copy variants, and high-converting landing-page HTML/copy snippet. Delivered monthly.`
*   **Pricing model:** `Standard pricing`
*   **Price:** `$497.00`
*   **Billing period:** `Monthly (Recurring)`
*   **Tax behavior:** `Amortized / Excluded`

### Tier 3: ProPlan Authority
*   **Product Name:** `ProPlan Authority — Multi-Campaign Suite`
*   **Description:** `20 ad visual assets (4 campaigns/quarter), A/B copy variants, UTM tracking setups, and priority 48-hour turnarounds.`
*   **Pricing model:** `Standard pricing`
*   **Price:** `$997.00`
*   **Billing period:** `Monthly (Recurring)`
*   **Tax behavior:** `Amortized / Excluded`

---

## 2. Setting Up Checkout Payment Links

For each product, generate a Stripe Payment Link (`Payments > Payment Links > New`). Customize the Checkout experience with these settings to minimize friction and collect critical operational data:

### Checkout Options
*   **Require customer phone numbers:** `Checked (Yes)`  
    *(CRITICAL: HVAC owners operate on their cell phones. You need this for text check-ins and delivery follow-up.)*
*   **Require billing address:** `Checked (Yes)`  
    *(Ensures proper tax compliance and credit card verification matching local Texas addresses.)*
*   **Collect tax automatically:** `Optional` *(Check if using Stripe Tax for Texas Services)*
*   **Show confirmation page:** `No`  
    *Choose: "Don't show confirmation page"*
*   **Redirect customer to your website:** `Checked (Yes)`  
    *Redirect URL:* Use your kickoff Google Form or secure intake URL:  
    `https://docs.google.com/forms/d/e/YOUR-GOOGLE-FORM-ID/viewform?entry.123456=Company`  
    *(This ensures the customer immediately transitions from "Paid" to "Onboarding Intake" without stopping.)*

---

## 3. Configuring the "2 Months Free" Annual Prepay Discount

Annual billing locks in cash flow, builds commitment, and halves your churn rate. You have two options to set this up in Stripe:

### Option A: Separate Annual Price (Recommended)
Add an annual price option to each of the three products above in the Stripe Product catalog:
*   **Starter Annual Price:** `$2,970.00 / yearly` *(Saves $594)*
*   **Campaign Annual Price:** `$4,970.00 / yearly` *(Saves $994 — Your best closing wedge)*
*   **Authority Annual Price:** `$9,970.00 / yearly` *(Saves $1,994)*

Generate separate Payment Links for the Annual versions, keeping the same phone and redirect configurations.

### Option B: Promo Code Coupon
If you prefer to use the monthly payment links but apply a discount code live:
1.  Go to `Product Catalog > Coupons > New`.
2.  **Name:** `2 Months Free Annual Prepay`
3.  **ID:** `ANNUAL2FREE`
4.  **Discount type:** `Percentage`
5.  **Percentage off:** `16.67%`
6.  **Duration:** `Forever` *(applies the discount as a flat rate over the annual charge)*
7.  Check `Eligible for promotion codes` so you can type it in checkout.

---

## 4. On-the-Call Closing Script

Do not send an invoice after the call. Complete the payment *while still on the phone*. 

When the client agrees to the Campaign tier, use this exact transition:

> *"Perfect, [Client Name]. I’ve just generated your secure checkout link. I’m texting it to your cell phone right now, and I’ll send a backup copy to your email. It takes about 60 seconds to complete. Go ahead and click that, and I'll stay on the line with you to make sure your brand intake form loads up right after payment. Once that's in, we'll get your first batch of ad creative scheduled for Friday."*

**Pro-Tip:** Keep the payment links saved in your phone's Notes app or as keyboard shortcuts (e.g., `!campaignlink`) so you can fire them off in under 3 seconds during a call.
