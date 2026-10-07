"""Select whole company documents with simple words and phrases."""

from pathlib import Path
import re


KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"

ITEM_SHIPPING_PHRASES = {
    "get it by", "get it before", "get them by", "get them before",
    "receive it by", "receive it before", "receive them by", "receive them before",
    "have it by", "have it before", "want it by", "want it before",
    "send it to", "send them to", "ship it to", "ship them to",
    "deliver it to", "deliver them to", "it arrive by", "it arrive before",
}

# Match whole words, plus everyday phrases. The full topic document is supplied.
POLICY_TERMS = {
    "returns.md": (
        {"return", "returns", "returning", "returned", "refund", "refunds", "refunded",
         "reimburse", "reimbursement", "label", "restocking", "unused", "worn",
         "exchange", "exchanges", "exchanging", "swap", "swaps", "swapping", "swapped",
         "broken", "broke", "damaged", "damage", "defective", "faulty", "torn",
         "cracked", "shattered", "leaking", "snapped", "malfunctioning"},
        {"send it back", "send back", "change my mind", "money back", "original payment",
         "get my money", "money is back", "back on my card", "back to my card",
         "credited back", "doesn't work", "does not work", "not working", "stopped working"},
    ),
    "shipping.md": (
        {"shipping", "ship", "shipped", "shipment", "delivery", "deliver", "delivered",
         "arrive", "arrives", "arrival", "tracking", "postage", "expedited",
         "international", "internationally", "overseas", "worldwide", "destinations",
         "confirmation", "track", "status", "dispatch", "dispatched", "package", "parcel",
         "subtotal", "alaska", "hawaii", "territories"},
        {"get here", "on its way", "when will i receive my order", "when will i get my order",
         "when do i receive my order", "when can i get my order", "order number", "order id",
         "where is my order", "where's my order", "check my order", "check on my order",
         "order update", "find my order", "haven't received my order", "haven't got my order",
         "my order hasn't arrived", "missed the email", "didn't get the email"}
        | ITEM_SHIPPING_PHRASES,
    ),
    "product_help.md": (
        {"care", "wash", "washing", "clean", "cleaning", "dry", "drying", "dryer",
         "iron", "ironing", "recommend", "suggest", "compare", "comparison", "budget",
         "warm", "warmth", "waterproof", "sizing", "fit", "chest", "measurements",
         "camping", "hiking", "hike", "rainy", "gift"},
        {"size chart", "water resistant", "water-resistant", "half size", "half sizes",
         "which should i choose", "what should i wear", "how should i store"},
    ),
    "shopping_orders.md": (
        {"cart", "basket", "checkout", "order", "orders", "buy", "buying", "purchase",
         "purchasing", "cancel", "cancellation", "cancelled", "canceled", "address",
         "processing", "dispatched", "delivered", "reserve", "reservation"},
        {"place an order", "change my order", "change my address", "address change",
         "how do i shop", "how can i shop"},
    ),
    "payments_promotions.md": (
        {"pay", "payment", "payments", "paid", "billing", "card", "cards", "credit",
         "debit", "visa", "mastercard", "amex", "discover", "wallet", "apple", "google",
         "bitcoin", "crypto", "cryptocurrency", "cash", "checks", "coupon", "coupons",
         "code", "promo", "promotion", "promotions", "discount", "discounts", "trail10",
         "tax", "taxes", "giftcard", "giftcards", "rewards", "loyalty"},
        {"gift card", "gift cards", "sales tax", "money off", "declined payment"},
    ),
    "support_privacy.md": (
        {"contact", "support", "human", "agent", "representative", "hours", "email",
         "phone", "telephone", "call", "hotline", "privacy", "private", "personal",
         "password", "cvv", "pin", "otp", "pickup", "location"},
        {"customer service", "get in touch", "talk to someone", "speak to someone",
         "when are you open", "physical store", "store pickup", "opening hours"},
    ),
}

CATALOG_KEYWORDS = {
    "jacket", "jackets", "raincoat", "raincoats", "fleece", "fleeces",
    "backpack", "backpacks", "daypack", "daypacks", "daypack20", "boot", "boots",
    "tent", "tents", "dress", "dresses", "formalwear", "clothing", "clothes",
    "outfit", "outfits", "catalog", "catalogue", "product", "products",
    "summit", "trail", "ridge", "pine",
}
CATALOG_QUERY_KEYWORDS = {
    "buy", "buying", "purchase", "purchasing", "shop", "shopping", "sell",
    "available", "availability", "restock", "restocking", "reserve", "reservation",
    "size", "sizes", "sizing", "small", "medium", "large", "xl", "fit",
    "color", "colors", "colour", "colours", "forest", "navy", "gray", "grey",
    "brown", "black", "budget", "compare", "comparison", "price", "prices",
    "waterproof", "capacity",
    "care", "wash", "clean", "recommend", "suggest", "warm", "hiking", "camping", "gift",
}
CATALOG_PHRASES = {
    "what do you have", "what items",
    "water resistant", "water-resistant", "half size", "half sizes",
}
RETAIL_STOCK_PHRASES = {"in stock", "out of stock", "stock availability"}
# "Stock" alone is not a product request: the original investing question stays
# outside company context. Named outdoor products can still be asked about stock.
FINANCE_KEYWORDS = {
    "stock", "stocks", "share", "shares", "bond", "bonds", "invest", "investing",
    "investment", "investments", "crypto", "bitcoin", "trading", "portfolio",
    "dividend", "dividends", "securities", "nasdaq",
}

ABOUT_KEYWORDS = {
    "camping", "hiking", "jacket", "jackets", "backpack", "backpacks", "boot",
    "boots", "tent", "tents", "outdoor", "outdoors", "outfitters", "store", "sell",
    "contact", "support", "human", "agent", "representative", "hours",
}
ABOUT_PHRASES = {
    "what can you help", "how can you help", "what do you do", "who are you",
    "what is northwind", "tell me about northwind", "what products", "your products",
    "what can you do",
    "what questions", "what can i ask", "what should i ask", "what topics",
    "customer service", "get in touch", "talk to someone", "speak to someone",
    "when are you open", "opening hours", "business hours", "your phone number",
    "your email", "support email", "can i call", "call you", "telephone support",
}


def load_knowledge() -> list[dict[str, str]]:
    """Read the Markdown files each time so edits take effect immediately."""
    return [
        {"filename": path.name, "content": path.read_text(encoding="utf-8").strip()}
        for path in sorted(KNOWLEDGE_DIR.glob("*.md"))
    ]


def _matching_documents(question: str, documents: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = question.lower().replace("’", "'")
    words = set(re.findall(r"[a-z]+(?:[0-9]+)?", normalized))
    named_product = words.intersection(CATALOG_KEYWORDS)
    retail_stock = any(phrase in normalized for phrase in RETAIL_STOCK_PHRASES)
    financial_request = words.intersection(FINANCE_KEYWORDS) and not named_product and not retail_stock
    payment_request = words.intersection({"pay", "payment", "payments", "accept", "accepted", "wallet"})
    help_keywords, help_phrases = POLICY_TERMS["product_help.md"]
    product_help = words.intersection(help_keywords) or any(phrase in normalized for phrase in help_phrases)
    matches = []
    for document in documents:
        keywords, phrases = POLICY_TERMS.get(document["filename"], (set(), set()))
        topic_match = words.intersection(keywords) or any(phrase in normalized for phrase in phrases)
        if document["filename"] == "catalog.md":
            catalog_query = (words.intersection(CATALOG_QUERY_KEYWORDS)
                             or product_help or any(phrase in normalized for phrase in CATALOG_PHRASES))
            missing_policy = (words.intersection({"price", "prices"})
                              and words.intersection({"match", "matching"})) or re.search(
                                  r"\bpricematch(?:ing)?\b", normalized
                              )
            topic_match = named_product or retail_stock or (
                catalog_query and not financial_request and not missing_policy
            )
        if document["filename"] in {"shopping_orders.md", "product_help.md"} and financial_request:
            topic_match = False
        if document["filename"] == "payments_promotions.md" and financial_request and not payment_request:
            topic_match = False
        if topic_match:
            matches.append(document)
    # Specific policies take precedence over general store information.
    greeting = re.fullmatch(r"\s*(?:hi|hello|hey|good morning|good afternoon|good evening)"
                            r"(?:\s+(?:there|northwind|assistant))?\s*[!.?]*\s*", normalized)
    general_help = re.fullmatch(r"\s*(?:please )?(?:can|could|would) you help(?: me)?(?: out)?[!.?]*\s*",
                               normalized)
    if not matches and (greeting or general_help or words.intersection(ABOUT_KEYWORDS)
                        or any(phrase in normalized for phrase in ABOUT_PHRASES)):
        matches = [document for document in documents if document["filename"] == "about.md"]
    return matches


def _recent_user_topic(
    history: list[dict], documents: list[dict[str, str]], *, follow_item_shipping: bool = False
) -> list[dict[str, str]]:
    for message in reversed(history):
        if message.get("role") == "user":
            prior_matches = _matching_documents(message.get("content", ""), documents)
            if prior_matches:
                normalized = message.get("content", "").lower().replace("’", "'")
                only_shipping = {document["filename"] for document in prior_matches} == {"shipping.md"}
                if follow_item_shipping and only_shipping and any(
                    phrase in normalized for phrase in ITEM_SHIPPING_PHRASES
                ):
                    continue
                return prior_matches
    return []


def retrieve(question: str, history: list[dict] | None = None) -> list[dict[str, str]]:
    """Select the current topic, using a recent user topic for apparent follow-ups.

    History supplies an otherwise missing follow-up topic. An item shipping
    question can also keep the recent product catalog. This is a small heuristic,
    not a semantic conversation engine; assistant messages never select policy.
    """
    documents = load_knowledge()
    matches = _matching_documents(question, documents)
    normalized = question.lower().replace("’", "'").strip()
    if matches:
        if history and any(phrase in normalized for phrase in ITEM_SHIPPING_PHRASES):
            prior_matches = _recent_user_topic(history, documents, follow_item_shipping=True)
            if any(document["filename"] == "catalog.md" for document in prior_matches):
                filenames = {document["filename"] for document in matches} | {"catalog.md"}
                return [document for document in documents if document["filename"] in filenames]
        return matches
    if not history:
        return matches
    follow_up = re.match(r"^(?:yes|no|it(?:'s| is)?|this|that(?:'s| is)?|they|those|here's|here is)\b",
                         normalized) or re.match(
        r"^(?:is|are|was|were|does|do|did|can|could|would|will|should) (?:it|this|that|they|those|these)\b",
        normalized,
    ) or re.fullmatch(r"how (?:long|much)[?!.]*", normalized) or re.match(
        r"^(?:what (?:if|about)|how (?:long|much) (?:does|will|would|is|are) (?:it|this|that|they))\b",
        normalized,
    ) or re.search(
        r"\b(?:about that|do that|check that|help with that)\b", normalized
    )
    identifier = re.search(r"\S+@\S+|\b\d{5,}\b|\+?\d[\d ().-]{6,}\d|\b[a-z]{2,6}[- ]?\d{4,}\b", normalized) or re.match(
        r"^my (?:phone|telephone|mobile|email|e-mail|order number|order id)\b", normalized
    )
    if len(normalized.split()) <= 30 and (follow_up or identifier):
        return _recent_user_topic(history, documents)
    return []


def format_context(documents: list[dict[str, str]]) -> str:
    """Return the exact policy text supplied to the model, or an empty string."""
    return "\n\n".join(document["content"] for document in documents)
