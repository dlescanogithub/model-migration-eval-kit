"""Directed lineage. An edge predecessor -> successor means predecessor migrates first."""

from __future__ import annotations

from dataclasses import dataclass

from migration_eval.platform_migrations.inventory.models import Manifest


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    effort: int


@dataclass(frozen=True)
class LineageGraph:
    nodes: tuple[Node, ...]
    edges: tuple[tuple[str, str], ...]

    def ids(self) -> tuple[str, ...]:
        return tuple(node.id for node in self.nodes)


def build_graph(manifest: Manifest) -> LineageGraph:
    nodes = [Node(item.id, "dataset", item.effort) for item in manifest.datasets]
    nodes.extend(Node(item.id, "job", item.effort) for item in manifest.jobs)
    nodes.extend(Node(item.id, "model", item.effort) for item in manifest.models)
    known = {node.id for node in nodes}
    if len(known) != len(nodes):
        raise ValueError("manifest has duplicate asset ids")
    edges: set[tuple[str, str]] = set()

    def link(src: str, dst: str) -> None:
        if src not in known or dst not in known:
            raise ValueError(f"unknown endpoint in edge {src} -> {dst}")
        edges.add((src, dst))

    for dataset in manifest.datasets:
        for upstream in dataset.upstream:
            link(upstream, dataset.id)
    for job in manifest.jobs:
        for src in job.datasets_in:
            link(src, job.id)
        for dep in job.depends_on:
            link(dep, job.id)
        for dst in job.datasets_out:
            link(job.id, dst)
        for model_id in job.models:
            link(job.id, model_id)
    for model in manifest.models:
        for dataset_id in model.datasets:
            link(dataset_id, model.id)
        for job_id in model.jobs:
            link(job_id, model.id)
    return LineageGraph(tuple(sorted(nodes, key=lambda node: node.id)), tuple(sorted(edges)))


def successor_map(graph: LineageGraph) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    for src, dst in graph.edges:
        grouped[src].append(dst)
    return {key: tuple(sorted(value)) for key, value in grouped.items()}


def predecessor_map(graph: LineageGraph) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    for src, dst in graph.edges:
        grouped[dst].append(src)
    return {key: tuple(sorted(value)) for key, value in grouped.items()}


def blast_radius(graph: LineageGraph, node_id: str) -> tuple[str, ...]:
    """Downstream assets that wait on node_id, excluding node_id itself."""
    succ = successor_map(graph)
    if node_id not in succ:
        raise KeyError(node_id)
    seen: set[str] = set()
    stack = list(succ[node_id])
    while stack:
        current = stack.pop()
        if current in seen or current == node_id:
            continue
        seen.add(current)
        stack.extend(succ[current])
    return tuple(sorted(seen))
