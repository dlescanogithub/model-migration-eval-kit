# Adapt this to a real client

Keep the client's name out of the repository. Use a codename in fixtures.

1. Run discovery ([DISCOVERY.md](DISCOVERY.md)) and write the answers in the client's own system, not in this public-shaped tree.
2. Export a manifest that matches the scanner. Start with one wave, not the whole estate.
3. Replace Aerolito team ids with the client's role names only if this copy of the repo stays private to that engagement. Otherwise keep roles generic (`team-data`).
4. Set parity tolerances from the client's acceptance rules. The defaults are exact aggregates and the local PSI/KS bands.
5. Re-decide registry stages versus aliases ([playbook/decisions.md](playbook/decisions.md)). Do not point `MLMIG_PROVIDER` at `real`. Build a connector in a separate private repo when they ask for one.
6. Run the rollback drill on a non-production registry. This simulator is the rehearsal, not the drill.
7. Put fees, rate cards, and headcount in the commercial workspace. They do not belong in this playbook.
