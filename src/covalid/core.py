import itertools


METHODS = [
    "covalid",
    "full_refresh",
    "round_robin",
    "no_nonempty",
    "issued_at_lease",
    "no_causal_constraints",
]


def policy(world, rule):
    if any(world[k] != value for k, value in rule.get("equals", {}).items()):
        return "Deny"
    if any(world[k] < value for k, value in rule.get("minimum", {}).items()):
        return "Deny"
    return "Permit"


def all_worlds(domains):
    keys = sorted(domains)
    return [dict(zip(keys, values)) for values in itertools.product(*(domains[k] for k in keys))]


def consistent(world, evidence, constraints, window, historical_as_lease=False):
    for record in evidence:
        guaranteed = (
            record["kind"] == "lease"
            and record["from"] <= window[0]
            and window[1] <= record["until"]
        )
        if historical_as_lease:
            guaranteed = record["from"] <= window[0]
        if guaranteed and world[record["attribute"]] != record["value"]:
            return False
    for relation in constraints:
        if all(world[k] == v for k, v in relation["if"].items()):
            if any(world[k] != v for k, v in relation["then"].items()):
                return False
    return True


def decide(case, method):
    evidence = list(case["evidence"])
    queries = []
    constraints = [] if method == "no_causal_constraints" else case["constraints"]
    worlds = all_worlds(case["domains"])
    for _ in range(len(case["domains"]) + 1):
        possible = [
            world
            for world in worlds
            if consistent(world, evidence, constraints, case["window"], method == "issued_at_lease")
        ]
        if not possible and method != "no_nonempty":
            return {"decision": "CONFLICT", "queries": queries, "evidence": evidence}
        accepting = [w for w in possible if policy(w, case["policy"]) == "Permit"]
        rejecting = [w for w in possible if policy(w, case["policy"]) != "Permit"]
        if not rejecting and method != "full_refresh":
            return {"decision": "Permit", "queries": queries, "evidence": evidence}
        if possible and not accepting and method != "full_refresh":
            return {"decision": "Deny", "queries": queries, "evidence": evidence}
        remaining = [k for k in sorted(case["domains"]) if k not in queries]
        if not remaining:
            return {
                "decision": "Permit" if accepting and not rejecting else "Deny",
                "queries": queries,
                "evidence": evidence,
            }
        if method == "covalid" and accepting and rejecting:
            pairs = [(a, b) for a in accepting[:8] for b in rejecting[:8]]
            chosen = max(
                remaining,
                key=lambda key: (
                    sum(a[key] != b[key] for a, b in pairs)
                    * case["issuers"][key]["success_probability"]
                    / (case["issuers"][key]["cost"] + case["issuers"][key]["latency"]),
                    key,
                ),
            )
        else:
            chosen = remaining[0]
        queries.append(chosen)
        issuer = case["issuers"][chosen]
        if issuer["available"]:
            evidence.append(
                {
                    "attribute": chosen,
                    "value": case["actual"][chosen],
                    "kind": "lease",
                    "from": case["window"][0],
                    "until": case["window"][1],
                    "revision": issuer["revision"],
                }
            )
    return {"decision": "DEFER", "queries": queries, "evidence": evidence}


def generate(rng, count):
    for index in range(count):
        domains = {
            "member": [False, True],
            "mfa": [False, True],
            "level": [0, 1, 2],
            "color": [0, 1],
        }
        actual = {k: rng.choice(v) for k, v in domains.items()}
        rule = {"equals": {"member": True, "mfa": True}, "minimum": {"level": 1}}
        issuers = {
            k: {
                "cost": rng.uniform(0.1, 1),
                "latency": rng.uniform(0.1, 1),
                "success_probability": 0.9,
                "available": rng.random() < 0.9,
                "revision": 1,
            }
            for k in domains
        }
        evidence = []
        if rng.random() < 0.5:
            evidence.append(
                {
                    "attribute": "mfa",
                    "value": not actual["mfa"],
                    "kind": "historical",
                    "from": 0,
                    "until": 1,
                    "revision": 0,
                }
            )
        yield {
            "id": str(index),
            "family": f"level-{actual['level']}",
            "domains": domains,
            "actual": actual,
            "evidence": evidence,
            "issuers": issuers,
            "constraints": [],
            "policy": rule,
            "window": [2, 3],
        }


def run_case(case, method):
    if not case["window"][0] <= case["window"][1]:
        raise ValueError("Invalid effect window")
    for record in case["evidence"]:
        if (
            record["attribute"] not in case["domains"]
            or record["value"] not in case["domains"][record["attribute"]]
        ):
            raise ValueError("Evidence outside issuer domain")
    return decide(case, method)


def score(case, result):
    actual = policy(case["actual"], case["policy"])
    permit = result["decision"] == "Permit"
    queries = result["queries"]
    return {
        "false_allow": int(permit) if actual != "Permit" else None,
        "unsafe_permit_all": int(permit and actual != "Permit"),
        "completion": int(permit) if actual == "Permit" else None,
        "false_denial": int(not permit) if actual == "Permit" else None,
        "queries": len(queries),
        "query_cost": sum(case["issuers"][q]["cost"] for q in queries),
        "issuer_latency_sum": sum(case["issuers"][q]["latency"] for q in queries),
        "query_failures": sum(not case["issuers"][q]["available"] for q in queries),
        "conflict": int(result["decision"] == "CONFLICT"),
        "legal_effects": int(permit and actual == "Permit"),
    }
