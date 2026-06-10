"""Repeatable data-room diligence pipeline.

Stages: manifest -> coverage -> reconcile -> scorecard -> requisitions -> report.
Each stage is a pure function over (data room path, configs) returning a dict,
so the whole pipeline re-runs idempotently every time new documents arrive.
"""
