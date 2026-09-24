# Implementation summary

A new validation-only module and CLI were added. The production parser and defaults were
not changed. The CLI gates all work on exact annual legacy reproduction, resolves spatial overlap at
the exact year–IK–OPS-code level, preserves suppressed components, retains 99-only institutions as
unresolved, records residuals without redistribution, builds parallel site/IK datasets, calculates
structural metrics, creates conservative longitudinal crosswalks, and audits existing geography and
repository-local OPS evidence. All outputs are isolated in this directory.
