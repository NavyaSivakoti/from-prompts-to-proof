# Shopping and Order Guidance

These are fictional Northwind Outfitters shopping and order policies for this
demonstration. The current app is a support chat with static demo information;
it is not a working shopping website. There is no functional cart, checkout,
customer account, order creation, payment processing, or order lookup here.
The assistant must not direct a customer to a nonexistent Northwind shopping
page or claim to have purchased, charged, cancelled, or changed anything.

## Understanding the fictional purchase process

The store policy describes the following conceptual purchase steps. They are
guidance about how an order would work, not actions available in this app.

1. Choose one of the five catalog products and an exact size/color option.
   Check that this option is available in the fixed demo data; an offered
   option that is sold out is not an available purchase.
2. Choose quantities and review the merchandise subtotal. Apply only supplied
   promotion rules. Shipping and tax are separate from the merchandise subtotal.
3. Provide a supported shipping destination in a real purchase workflow. The
   fictional store serves the contiguous 48 United States. The current chat
   cannot validate an address and should not collect private address details.
4. Review available shipping options and all charges before confirming a real
   purchase. Standard shipping uses the supplied standard rate and threshold.
   Expedited options may be available, but an exact expedited rate or guaranteed
   delivery time is not supplied. An exact tax amount is not supplied either.
5. In the fictional store workflow, a successfully accepted checkout would
   produce an order confirmation email. Dispatch would produce a tracking
   email. The current chat cannot perform checkout or send either email.

Payment methods and promotion rules are explained in the separate payment and
promotion policy. The assistant may explain those rules and estimate amounts
from supplied facts, but an estimate is not a completed order or charge.

## What order statuses mean

These are general status definitions. They do not identify the status of any
customer's order, and the assistant has no customer order records.

- Processing: an accepted order is being prepared and has not been dispatched.
  A tracking email may not exist yet. No processing-time guarantee is supplied.
- Dispatched: the order has been handed to the carrier. Tracking information
  is emailed at dispatch. Standard delivery normally takes 3–5 business days
  after dispatch; do not count that estimate from the purchase date.
- Delivered: the carrier reports delivery. The assistant cannot verify that
  record, inspect a customer's package, or guarantee where a package was left.
- Cancelled: human support has confirmed cancellation. A customer's request
  alone does not establish this status. No cancellation refund timing is
  supplied in this policy.

The assistant can explain a status provided by a customer without claiming to
have checked it. It cannot generate an order number, authenticate an account,
look up an order using contact information, inspect a cart, or resend emails.
An order question without a status remains unknown; do not assume dispatch,
delivery, cancellation, or refund approval.

## Cancellation and address-change requests

Before dispatch, a customer may request cancellation or a shipping-address
change from human support at support@northwind.example, a fictional contact.
Send the order number and requested change directly to human support, rather
than sharing private order or address details in this chat.

Human support reviews whether the request can be accepted while the order is
still being prepared. Neither cancellation nor an address change is guaranteed.
The assistant cannot check the order's stage, submit the request, approve it,
update an address, or claim that support has received or accepted the request.

After dispatch, the fictional store cannot cancel the order or change its
shipping address. Human support can provide guidance, but no carrier rerouting
or successful address correction is promised here. A customer seeking to send
an item back after delivery should use the standard return process if eligible:
within 30 days of delivery, unused, and in original condition. A cancellation
request does not bypass those conditions or waive the ordinary return costs.

## Missing or unclear order information

Check spam and junk folders, search for Northwind Outfitters emails, and verify
the email used at checkout if a confirmation or tracking email is missing.
Tracking information may not be available before dispatch. If information is
still missing, contact fictional human support directly with necessary order
details. The assistant cannot recover an order record or send a replacement
email. Detailed shipping, returns, refunds, and arrival-damage rules are in
their respective supplied policies.
