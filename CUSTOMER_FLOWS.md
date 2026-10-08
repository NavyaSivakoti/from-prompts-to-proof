# Merchant reference and customer journeys

Reviewed October 6, 2026.

Northwind Outfitters is the fictional outdoor merchant defined for this demo.
Its five-product catalog contains a rain jacket, fleece, backpack, hiking boots,
and tent. **REI is the primary merchant reference** because its outdoor clothing
and gear focus closely matches this catalog. REI's storefront shows rain jackets,
fleece, boots, and backpacks. [REI store](https://www.rei.com/)

DICK'S is a useful secondary reference for broader sporting-goods shopping and
order workflows; its site includes sports, footwear, clothing, and outdoor
categories. Gymshark is a fitness-clothing reference, with workout apparel and
guides for activities such as running and lifting. [DICK'S official site and order guide](https://www.dickssportinggoods.com/s/understand-order-status),
[Gymshark store](https://www.gymshark.com/)

The reference informs the customer journeys to cover. Northwind's products,
prices, destinations, fees, promotion, and return conditions are its own explicit
fictional requirements. The source of truth for a Northwind answer is the local
knowledge base, not a real retailer's rules. No affiliation is implied.

## What the merchant references document

REI links order status, returns, shipping, discounts, and customer help from its
store and help pages. [REI help](https://www.rei.com/help)

Gymshark separates product help, orders/delivery, returns/refunds, and
payments/promotions. Its product help includes sizing, care, and restock topics.
[Gymshark help](https://support.gymshark.com/en/),
[product help](https://support.gymshark.com/en/collections/3643098-product)

Gymshark explains promotion eligibility and how discounts interact with shipping.
Its order-change page documents exactly which changes are available and when.
These examples show why a customer needs clear conditions, not a general promise.
[Discount guidance](https://support.gymshark.com/en/articles/11179105-what-discounts-are-available),
[order-change guidance](https://support.gymshark.com/en/articles/11185613-i-want-to-change-my-order-address)

DICK'S distinguishes processing, shipment, cancellation requests, completed
cancellation, and pickup statuses. Its return page offers separate return paths.
These are examples of workflows and status definitions, not Northwind status
records or capabilities. [Order-status guide](https://www.dickssportinggoods.com/s/understand-order-status),
[return guidance](https://www.dickssportinggoods.com/s/return-policy)

## Northwind coverage checklist

This mapping is our design inference from the reference journeys and the current
Northwind requirements.

| Customer stage | Ordinary question | Northwind information or expected behavior |
|---|---|---|
| Discover and compare | Which listed items fit my $60 budget? | Catalog prices, supplied features, and product-selection guidance. No invented product or performance guarantee. |
| Select a variant | Is the Navy jacket available in medium? What about large? | Exact color/size stock: Navy M sold out; Navy L available. |
| Estimate a basket | What does the jacket cost with TRAIL10 and shipping? | $80 minus $8 is $72 merchandise; $5.99 shipping; $77.99 before tax. |
| Understand checkout | Can I pay with Apple Pay? Can you take my payment? | Explain the fictional payment policy; do not claim a payment or functional checkout. |
| Understand an order | What does Processing mean? Where is my tracking email? | Status definitions, processing/dispatch estimates, and email guidance; no actual order lookup. |
| Request a change | Can I cancel before dispatch or change my address? | Human-reviewed request before dispatch, no guarantee; assistant performs no change. |
| Resolve delivery trouble | Tracking says delivered, but I cannot find the parcel. | Check the delivery area and household, then contact human support directly. No promised replacement/refund. |
| Return or report damage | What does a return cost? My tent arrived torn. | Ordinary label deduction, eligibility, damage review, and conditional label rule. |
| Understand a refund | When does an approved refund arrive? | Original payment method; may take 5–7 business days after approval. |
| Care and contact | Can I machine wash the backpack? Can I call support? | Do not machine wash the backpack; damp-cloth care. Fictional email support, no phone hotline. |

The [answer key](ANSWER_KEY.md) lists the expected answers. The eight documents
in `demo/knowledge/` provide the factual requirements, and the evaluation cases
check selected combinations of those facts.

## Facts and actions are separate

The current knowledge base supplies descriptions, policies, and fixed fictional
stock. It does not create a cart, order, payment, reservation, or live stock check.
A chat-only shopping version could retain the same interface while adding a small
inventory/order database and actions that read or update it. Such actions must
return actual results before the chatbot claims success.

For the current demo, keep the prepared prompts, knowledge files, model settings,
and cases fixed during a comparison. Discuss actual answers and grader errors
against the Northwind answer key. Real-store references are not evidence that a
Northwind answer is correct, and a live failure is not guaranteed.
