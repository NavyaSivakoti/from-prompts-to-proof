# Payments, Promotions, and Tax

These are fictional Northwind Outfitters shopping policies for this demonstration.
There is no functional Northwind checkout or payment service in this demo.
The assistant can explain these written policies and calculate hypothetical
totals, but it cannot take a payment, apply a code, inspect a transaction, or
complete a purchase.

## Currency and payment methods

All catalog prices are in U.S. dollars (USD).
The fictional checkout policy accepts Visa, Mastercard, American Express,
and Discover credit or debit cards, plus Apple Pay and Google Pay.
It does not accept cash, checks, or cryptocurrency, including Bitcoin.
Northwind does not offer gift cards or a rewards/loyalty program in this demo.

## The public demo promotion

TRAIL10 is a public demo code for 10% off the merchandise subtotal when the
merchandise subtotal before the discount is at least $50.
The $50 minimum counts merchandise only; shipping and tax do not count.
Only one promotion code can be used per order. TRAIL10 does not discount shipping.
No other promotion codes or promotions are supplied. Do not invent an additional
code, discount, promotion, expiry date, or stacking exception.

For hypothetical totals, calculate the merchandise discount and round amounts
to the nearest cent. Subtract the discount before checking shipping eligibility.
Use the shipping policy: standard shipping is free when the merchandise subtotal
after discounts and before tax is at least $75; otherwise it costs $5.99.
Do not count shipping or tax toward the free-standard-shipping threshold.

Examples:
- The $80 Summit Rain Jacket qualifies for TRAIL10: the discount is $8,
  merchandise becomes $72, standard shipping costs $5.99, and the total before
  tax including standard shipping is $77.99.
- One $45 Daypack20 Backpack does not qualify for TRAIL10 because its
  merchandise subtotal is below $50, even if shipping makes the overall total
  exceed $50. Its merchandise subtotal remains $45.

## Tax

Sales tax depends on the shipping address. No tax rates or ZIP-code tax table
are supplied. The assistant cannot look up a tax rate, quote an exact tax amount
from a ZIP code, or invent a tax exemption.
If the customer supplies a tax amount, the assistant may add that amount to a
hypothetical total. Tax does not change free-standard-shipping eligibility.

## A failed payment

For a failed or declined payment, suggest that the customer check their billing
information privately and contact their bank or human support if help is needed.
Do not assert a specific reason for the failure without supplied evidence.
Do not ask the customer to share a full card number, card security code/CVV,
PIN, one-time passcode/OTP, password, or other payment credentials in this chat.
The assistant cannot retry a payment, remove a charge, check a bank account,
contact the bank, or resolve the transaction itself.
