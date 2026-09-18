"""
Canonical Predicate Normalization
==================================

WHY THIS MATTERS:
    The old pipeline stored "acquired", "acquires", "buy", "purchased" as four
    separate edge types in the knowledge graph.  This means graph queries for
    acquisition relationships only match one surface form, missing most edges.

HOW IT WORKS:
    Every extracted verb is lemmatized and looked up in CANONICAL_PREDICATE_MAP.
    If a match is found the canonical ALL_CAPS form is used as the edge label.
    Unknown predicates fall back to the uppercase lemma so the graph remains
    consistent even for verbs not in the dictionary.

IMPROVEMENT OVER OLD CODE:
    Old:  "acquired", "buys", "purchase" → 3 different relationship types
    New:  all three → "ACQUIRED"           → 1 canonical relationship type
"""

# ---------------------------------------------------------------------------
# Master mapping: lemma (lowercase) → canonical predicate (UPPER_SNAKE_CASE)
# ---------------------------------------------------------------------------
CANONICAL_PREDICATE_MAP: dict[str, str] = {

    # --- Acquisition / Merger -----------------------------------------------
    "acquire":   "ACQUIRED",
    "buy":       "ACQUIRED",
    "purchase":  "ACQUIRED",
    "obtain":    "ACQUIRED",
    "takeover":  "ACQUIRED",
    "absorb":    "ACQUIRED",
    "merge":     "MERGED_WITH",
    "combine":   "MERGED_WITH",
    "consolidate": "MERGED_WITH",
    "spin":      "SPUN_OFF",
    "divest":    "DIVESTED",

    # --- Founding / Creation ------------------------------------------------
    "found":     "FOUNDED",
    "establish": "FOUNDED",
    "incorporate": "FOUNDED",
    "create":    "CREATED",
    "start":     "FOUNDED",
    "launch":    "LAUNCHED",
    "introduce": "LAUNCHED",
    "pioneer":   "PIONEERED",
    "invent":    "INVENTED",
    "build":     "BUILT",
    "construct": "BUILT",

    # --- Employment / Leadership --------------------------------------------
    "employ":    "EMPLOYS",
    "hire":      "EMPLOYS",
    "recruit":   "EMPLOYS",
    "appoint":   "APPOINTED",
    "promote":   "PROMOTED",
    "elect":     "ELECTED",
    "nominate":  "NOMINATED",
    "work":      "WORKS_AT",
    "join":      "JOINED",
    "leave":     "LEFT",
    "resign":    "RESIGNED_FROM",
    "fire":      "TERMINATED",
    "dismiss":   "TERMINATED",
    "lead":      "LEADS",
    "head":      "LEADS",
    "manage":    "MANAGES",
    "oversee":   "MANAGES",
    "run":       "MANAGES",
    "direct":    "DIRECTS",
    "chair":     "CHAIRS",
    "serve":     "SERVES_AS",
    "succeed":   "SUCCEEDED",

    # --- Development / Production -------------------------------------------
    "develop":   "DEVELOPED",
    "produce":   "PRODUCED",
    "manufacture": "MANUFACTURED",
    "make":      "PRODUCED",
    "design":    "DESIGNED",
    "engineer":  "ENGINEERED",
    "deploy":    "DEPLOYED",
    "ship":      "SHIPPED",
    "distribute": "DISTRIBUTES",
    "sell":      "SELLS",
    "market":    "MARKETS",

    # --- Partnership / Collaboration ----------------------------------------
    "partner":   "PARTNERED_WITH",
    "collaborate": "COLLABORATED_WITH",
    "cooperate": "COLLABORATED_WITH",
    "ally":      "ALLIED_WITH",
    "team":      "PARTNERED_WITH",
    "associate": "ASSOCIATED_WITH",
    "affiliate": "AFFILIATED_WITH",

    # --- Investment / Funding -----------------------------------------------
    "invest":    "INVESTED_IN",
    "fund":      "FUNDED",
    "finance":   "FUNDED",
    "back":      "FUNDED",
    "sponsor":   "SPONSORED",
    "grant":     "GRANTED",
    "raise":     "RAISED",
    "support":   "SUPPORTS",

    # --- Location / Headquarters --------------------------------------------
    "locate":    "LOCATED_IN",
    "headquarter": "HEADQUARTERED_IN",
    "base":      "BASED_IN",
    "operate":   "OPERATES_IN",
    "expand":    "EXPANDED_TO",
    "enter":     "ENTERED_MARKET_IN",

    # --- Ownership / Control ------------------------------------------------
    "own":       "OWNS",
    "control":   "CONTROLS",
    "hold":      "HOLDS",
    "possess":   "OWNS",
    "operate":   "OPERATES",

    # --- Technology / Use ---------------------------------------------------
    "use":       "USES",
    "apply":     "USES",
    "adopt":     "ADOPTED",
    "implement": "IMPLEMENTED",
    "integrate": "INTEGRATED",
    "leverage":  "USES",
    "power":     "POWERED_BY",
    "enable":    "ENABLES",

    # --- Release / Publication ----------------------------------------------
    "release":   "RELEASED",
    "publish":   "PUBLISHED",
    "announce":  "ANNOUNCED",
    "unveil":    "ANNOUNCED",
    "reveal":    "ANNOUNCED",
    "disclose":  "DISCLOSED",
    "report":    "REPORTED",

    # --- Agreement / Contract -----------------------------------------------
    "sign":      "SIGNED_AGREEMENT_WITH",
    "agree":     "AGREED_WITH",
    "contract":  "CONTRACTED_WITH",
    "license":   "LICENSED_TO",
    "sublicense": "SUBLICENSED_TO",
    "authorize": "AUTHORIZED",
    "approve":   "APPROVED",
    "certify":   "CERTIFIED",
    "comply":    "COMPLIES_WITH",

    # --- Competition --------------------------------------------------------
    "compete":   "COMPETES_WITH",
    "rival":     "COMPETES_WITH",
    "challenge": "COMPETES_WITH",

    # --- Supply / Provide ---------------------------------------------------
    "supply":    "SUPPLIES",
    "provide":   "PROVIDES",
    "offer":     "OFFERS",
    "deliver":   "DELIVERS",
    "source":    "SOURCED_FROM",

    # --- Regulation / Legal -------------------------------------------------
    "regulate":  "REGULATED_BY",
    "sue":       "SUED",
    "fine":      "FINED",
    "investigate": "INVESTIGATED_BY",
    "ban":       "BANNED",
    "block":     "BLOCKED",
    "sanction":  "SANCTIONED",

    # --- Includes / Contains ------------------------------------------------
    "include":   "INCLUDES",
    "contain":   "INCLUDES",
    "comprise":  "INCLUDES",
    "consist":   "INCLUDES",
    "feature":   "FEATURES",

    # --- Representation / Identity ------------------------------------------
    "represent": "REPRESENTS",
    "become":    "BECAME",
    "remain":    "REMAINS",
    "replace":   "REPLACED",
}


def normalize_predicate(verb_lemma: str) -> str:
    """
    Convert a verb lemma to its canonical predicate form.

    Examples:
        normalize_predicate("acquired")  → "ACQUIRED"
        normalize_predicate("buys")      → "ACQUIRED"   (after lemmatization)
        normalize_predicate("flubbed")   → "FLUBBED"    (unknown → uppercased)

    Args:
        verb_lemma: The lemma form of the verb (lowercase expected).

    Returns:
        Canonical predicate string in UPPER_SNAKE_CASE.
    """
    lemma = verb_lemma.lower().strip()
    return CANONICAL_PREDICATE_MAP.get(lemma, lemma.upper().replace(" ", "_"))
