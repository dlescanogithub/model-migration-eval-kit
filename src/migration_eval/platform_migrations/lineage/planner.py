"""Topological waves, one reported cycle, and a longest-path critical path."""

from __future__ import annotations

from dataclasses import dataclass

from migration_eval.platform_migrations.lineage.graph import LineageGraph, predecessor_map, successor_map


@dataclass(frozen=True)
class Wave:
    index: int
    node_ids: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    waves: tuple[Wave, ...]
    blocked: tuple[str, ...]
    cyclic: bool
    cycle: tuple[str, ...]
    critical_path: tuple[str, ...]
    critical_path_effort: int

    @property
    def complete(self) -> bool:
        return not self.blocked


def plan_migration(graph: LineageGraph) -> Plan:
    succ = successor_map(graph)
    indegree = {node.id: 0 for node in graph.nodes}
    for src, destinations in succ.items():
        for dst in destinations:
            indegree[dst] += 1
            _ = src
    ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    waves: list[Wave] = []
    placed: list[str] = []
    index = 1
    while ready:
        wave = tuple(ready)
        waves.append(Wave(index, wave))
        index += 1
        upcoming: list[str] = []
        for node_id in wave:
            placed.append(node_id)
            for nxt in succ[node_id]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    upcoming.append(nxt)
        ready = sorted(set(upcoming))
    blocked = tuple(sorted(set(indegree) - set(placed)))
    cycle = find_cycle(graph) if blocked else ()
    if blocked:
        return Plan(tuple(waves), blocked, True, cycle, (), 0)
    path, effort = _critical_path(graph, tuple(node_id for wave in waves for node_id in wave.node_ids))
    return Plan(tuple(waves), (), False, (), path, effort)


def find_cycle(graph: LineageGraph) -> tuple[str, ...]:
    succ = successor_map(graph)
    color = {node.id: 0 for node in graph.nodes}
    cycle: list[str] = []

    def dfs(node: str, stack: list[str]) -> bool:
        color[node] = 1
        stack.append(node)
        for nxt in succ[node]:
            if color[nxt] == 0:
                if dfs(nxt, stack):
                    return True
            elif color[nxt] == 1:
                start = stack.index(nxt)
                cycle.extend(stack[start:])
                cycle.append(nxt)
                return True
        stack.pop()
        color[node] = 2
        return False

    for node in graph.nodes:
        if color[node.id] == 0 and dfs(node.id, []):
            break
    return tuple(cycle)


def _critical_path(graph: LineageGraph, order: tuple[str, ...]) -> tuple[tuple[str, ...], int]:
    if not order:
        return (), 0
    preds = predecessor_map(graph)
    effort = {node.id: node.effort for node in graph.nodes}
    best_effort: dict[str, int] = {}
    best_path: dict[str, tuple[str, ...]] = {}
    for node_id in order:
        candidates = preds[node_id]
        if not candidates:
            best_effort[node_id] = effort[node_id]
            best_path[node_id] = (node_id,)
            continue
        chosen_effort = -1
        chosen_path: tuple[str, ...] = ()
        for pred in candidates:
            cand_effort = best_effort[pred] + effort[node_id]
            cand_path = best_path[pred] + (node_id,)
            if cand_effort > chosen_effort or (cand_effort == chosen_effort and cand_path < chosen_path):
                chosen_effort = cand_effort
                chosen_path = cand_path
        best_effort[node_id] = chosen_effort
        best_path[node_id] = chosen_path
    winner = min(order, key=lambda node_id: (-best_effort[node_id], best_path[node_id]))
    return best_path[winner], best_effort[winner]
