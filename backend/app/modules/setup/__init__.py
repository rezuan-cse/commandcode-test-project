"""First-run setup: the one account that has to exist before anything else.

A brand-new company has no workbook and, on a hosted deployment, no demo accounts
either (`RPCI_SEED_DEMO_USERS=false`). That left a fresh install with zero users
and no way in: the sign-in screen was the only door, and nobody held a key.

This module is that door, and only that door. It answers "does this system still
need its first administrator?" and creates that person. It shuts itself the moment
one account exists, so it cannot be used to mint extra administrators later — from
then on, accounts are created from Administration → Roles & Access.
"""
