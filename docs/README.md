# India Banking — Documentation

This folder contains technical documentation, developer guides, and migration notes for the `india_banking` Frappe app.

## Contents

| Folder / File | Purpose |
|---|---|
| [migration/v15-to-v16.md](migration/v15-to-v16.md) | v15 → v16 migration checklist and impact analysis |
| [guides/doctypes/bank-account.md](guides/doctypes/bank-account.md) | Bank Account — what we add, why, and how |
| [guides/doctypes/payment-request.md](guides/doctypes/payment-request.md) | Payment Request override guide |
| [guides/doctypes/payment-order.md](guides/doctypes/payment-order.md) | Payment Order override guide |
| [guides/doctypes/payment-entry.md](guides/doctypes/payment-entry.md) | Payment Entry override guide |
| [guides/doctypes/journal-entry.md](guides/doctypes/journal-entry.md) | Journal Entry hook guide |
| [guides/architecture.md](guides/architecture.md) | App architecture overview |
| [guides/adding-a-bank.md](guides/adding-a-bank.md) | How to add a new bank connector |
| [guides/testing.md](guides/testing.md) | How to run and write tests |
| [assets/](assets/) | Screenshots and images referenced by guides |
| [configuration/settings.md](configuration/settings.md) | India Banking Settings reference |
| [configuration/mode-of-transfer.md](configuration/mode-of-transfer.md) | Mode of Transfer configuration |

## Workflow

1. Pick the doctype you are working on → read its guide in `guides/doctypes/`
2. For new development → follow patterns in `guides/architecture.md`
