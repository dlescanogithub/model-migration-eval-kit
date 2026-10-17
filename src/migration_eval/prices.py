"""Price table. Figures in the bundled file are [EST] and simulated."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from migration_eval.yamlutil import load_yaml_mapping, require_float, require_str


@dataclass(frozen=True)
class ModelPrice:
    name: str
    provider: str
    usd_per_1k_input: float
    usd_per_1k_output: float
    source: str
    price_date: str


@dataclass(frozen=True)
class PriceTable:
    currency: str
    note: str
    models: dict[str, ModelPrice]

    def for_model(self, name: str) -> ModelPrice:
        if name not in self.models:
            raise KeyError(f"no price for {name}")
        return self.models[name]


def load_prices(path: Path) -> PriceTable:
    data = load_yaml_mapping(path)
    currency = require_str(data, "currency")
    note = require_str(data, "note")
    raw_models = data.get("models")
    if not isinstance(raw_models, dict):
        raise ValueError("prices.models must be a mapping")
    models: dict[str, ModelPrice] = {}
    for name, raw in raw_models.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            raise ValueError("each price entry needs a string name and a mapping")
        entry: dict[str, Any] = {}
        for key, value in raw.items():
            entry[str(key)] = value
        models[name] = ModelPrice(
            name=name,
            provider=require_str(entry, "provider"),
            usd_per_1k_input=require_float(entry, "usd_per_1k_input"),
            usd_per_1k_output=require_float(entry, "usd_per_1k_output"),
            source=require_str(entry, "source"),
            price_date=require_str(entry, "price_date"),
        )
    return PriceTable(currency=currency, note=note, models=models)


def cost_usd(price: ModelPrice, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000.0) * price.usd_per_1k_input + (output_tokens / 1000.0) * price.usd_per_1k_output
