"""Exact top-k candidate enumeration for prefix and first-two-token audit rules."""
from collections import defaultdict
import heapq
from itertools import combinations


def cross_group_top_pairs(left, right, limit):
    """Enumerate the largest pair sums without constructing a Cartesian product."""
    left = sorted(left, key=lambda row: (-row["n_rows"], row["merchant_key"]))
    right = sorted(right, key=lambda row: (-row["n_rows"], row["merchant_key"]))
    if not left or not right:
        return
    pending = [(-(left[0]["n_rows"] + right[0]["n_rows"]), 0, 0)]
    seen = {(0, 0)}
    for _ in range(limit):
        if not pending:
            break
        _, i, j = heapq.heappop(pending)
        yield left[i], right[j]
        for a, b in [(i + 1, j), (i, j + 1)]:
            if a < len(left) and b < len(right) and (a, b) not in seen:
                seen.add((a, b))
                heapq.heappush(pending, (-(left[a]["n_rows"] + right[b]["n_rows"]), a, b))


def find_pairs(merchants, limit):
    rows = merchants.select("merchant_key", "split", "n_rows").to_dicts()
    rows.sort(key=lambda row: row["merchant_key"])
    lookup = {row["merchant_key"]: row for row in rows}
    heap = []
    selected = set()

    def offer(left, right):
        a, b = sorted([left["merchant_key"], right["merchant_key"]])
        if left["split"] == right["split"] or (a, b) in selected:
            return
        item = (left["n_rows"] + right["n_rows"], a, b)
        if len(heap) < limit:
            heapq.heappush(heap, item)
            selected.add((a, b))
        elif item > heap[0]:
            old = heapq.heapreplace(heap, item)
            selected.remove((old[1], old[2]))
            selected.add((a, b))

    stack = []
    groups = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = row["merchant_key"]
        while stack and not key.startswith(stack[-1]["merchant_key"]):
            stack.pop()
        for ancestor in stack:
            offer(ancestor, row)
        stack.append(row)
        tokens = key.split()
        if len(tokens) >= 2:
            groups[tuple(tokens[:2])][row["split"]].append(row)
    for splits in groups.values():
        for a, b in combinations(sorted(splits), 2):
            for left, right in cross_group_top_pairs(splits[a], splits[b], limit):
                offer(left, right)
    output = []
    for total, a, b in sorted(heap, reverse=True):
        rules = []
        if b.startswith(a):
            rules.append("prefix")
        if len(a.split()) >= 2 and a.split()[:2] == b.split()[:2]:
            rules.append("first_two_tokens")
        output.append({"key_a": a, "split_a": lookup[a]["split"], "rows_a": lookup[a]["n_rows"],
                       "key_b": b, "split_b": lookup[b]["split"], "rows_b": lookup[b]["n_rows"],
                       "combined_rows": total, "rules": ";".join(rules)})
    return output
