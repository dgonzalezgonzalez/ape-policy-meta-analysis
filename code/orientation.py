"""Rules for directional coding. Probabilities are judgments, not ground truth."""
import math
import json
from paths import ROOT
PROTOCOL = json.loads((ROOT/'data/direction_protocol.json').read_text(encoding='utf-8'))
DESC_TH = PROTOCOL['baseline']['ambiguity_max']
MARGIN_TH = PROTOCOL['baseline']['margin']
SUPPORT_TH = PROTOCOL['baseline']['support']


def legacy_orientation(inc, dec, low, descriptive, margin_th=.20, desc_th=.60):
    """Correct the old probability inversion, without rewriting cached answers."""
    if any(x is None or not math.isfinite(x) for x in (inc, dec, low, descriptive)):
        return 0, "missing response", None, False
    a, b = inc - dec, 1 - 2 * low
    margin = (a + b) / 2
    agrees = a * b > 0
    if descriptive >= desc_th:
        return 0, "descriptive outcome", margin, agrees
    if abs(margin) < margin_th:
        return 0, "uncertain or conflicting directions", margin, agrees
    return (1 if margin > 0 else -1), "combined legacy rule", margin, agrees


def orientation(answers, margin_th=MARGIN_TH, desc_th=DESC_TH,
                support_th=SUPPORT_TH, opposite_ceiling=None, apply_qualifiers=True):
    """Require explicit support for a beneficiary direction; retain intent separately."""
    def p(key):
        value = answers.get(key, {}).get("noul")
        return value if isinstance(value, (int, float)) and 0 <= value <= 1 else None
    up, down, ambiguous = p("higher_benefits"), p("lower_benefits"), p("direction_ambiguous")
    gi, gd = p("goal_increase"), p("goal_decrease")
    if any(x is None for x in (up, down, ambiguous, gi, gd)):
        return {"sign": 0, "reason": "missing response", "margin": None,
                "goal_sign": 0, "agreement": False}
    gap, goal_gap = up - down, gi - gd
    goal_sign = (1 if goal_gap > 0 else -1) if abs(goal_gap) >= margin_th and max(gi, gd) >= support_th else 0
    qualifier = next((key for key in PROTOCOL['semantic_safeguards']['questions']
                      if apply_qualifiers and p(key) is not None and
                      p(key) >= PROTOCOL['semantic_safeguards']['probability_threshold'] and
                      (key == 'group_composition' or ambiguous >=
                       PROTOCOL['semantic_safeguards']['qualifier_ambiguity_min'])), None)
    if qualifier:
        sign, reason = 0, 'measurement qualifier: '+qualifier
    elif ambiguous >= desc_th:
        sign, reason = 0, "ambiguous economic direction"
    elif (abs(gap) < margin_th or max(up, down) < support_th or
          (opposite_ceiling is not None and min(up, down) > opposite_ceiling)):
        sign, reason = 0, "insufficient directional evidence"
    else:
        sign, reason = (1 if gap > 0 else -1), "beneficiary outcome direction"
    return {"sign": sign, "reason": reason, "margin": gap,
            "goal_sign": goal_sign, "agreement": sign != 0 and sign == goal_sign}
