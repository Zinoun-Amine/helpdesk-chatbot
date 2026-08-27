from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_TECHNICIANS = (
    "Amine Zinoun",
    "Sofia El Idrissi",
    "Youssef Bensaid",
    "Nabil Cherkaoui",
)

STANDARD_CATEGORIES = (
    "Wincar", "Messagerie", "Citrix", "Matériel", "Internet",
    "Logiciel Système", "Sage", "Windows", "APPCC", "Réseau",
    "Outillages SAV", "GestorNet", "CRM", "Auto Naps", "Poste IP Phone",
    "Reporting", "Ligne VPN", "Consommable", "Ligne Téléphonique", "GSM",
    "Moovapps", "PayRoll", "RIAPP", "Qalitel Doc", "GDoc",
    "Contrat de Vente", "Sage Paie & RH", "Microsoft Teams", "WebEX",
    "GENERAFI", "Site Web", "AppGCMA", "VPN_FortiClient", "Fidélisation",
    "Optimmo", "SMS", "SRM", "Qalitel Compar", "Antivirus", "SLV",
    "VOXCO", "Intranet", "Devopps", "C.Conformité", "eSeller", "TPE",
    "OPEL",
)


def find_file(filename: str = "ticket.xlsx") -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / filename
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError(f"Could not locate {filename} from {Path(__file__).resolve()}")


def load_category_counts(file_path: Path) -> pd.Series:
    frame = pd.read_excel(file_path)
    frame.columns = [str(column).strip() for column in frame.columns]
    category_column = "itilcategory_name"
    if category_column not in frame.columns:
        raise ValueError(f"Missing required column: {category_column}")

    category_lookup = {category.casefold(): category for category in STANDARD_CATEGORIES}
    categories = frame[category_column].astype("string").str.strip()
    validated = categories.map(lambda value: category_lookup.get(value.casefold()) if pd.notna(value) else None)
    return validated.dropna().value_counts().reindex(STANDARD_CATEGORIES, fill_value=0)


def balance_categories(
    category_counts: pd.Series,
    technicians: Iterable[str],
) -> dict[str, list[tuple[str, int]]]:
    technician_names = [name.strip() for name in technicians if name.strip()]
    if not technician_names:
        raise ValueError("At least one technician is required")
    if len(set(technician_names)) != len(technician_names):
        raise ValueError("Technician names must be unique")

    assignments = {name: [] for name in technician_names}
    loads = {name: 0 for name in technician_names}

    # Largest-first assignment keeps the maximum workload difference small.
    for category, count in category_counts.sort_values(ascending=False).items():
        technician = min(technician_names, key=lambda name: (loads[name], name))
        ticket_count = int(count)
        assignments[technician].append((str(category), ticket_count))
        loads[technician] += ticket_count

    return assignments


def print_report(assignments: dict[str, list[tuple[str, int]]], total_tickets: int) -> None:
    loads = {name: sum(count for _, count in rows) for name, rows in assignments.items()}
    target = total_tickets / len(assignments)

    print(f"Categories: {sum(len(rows) for rows in assignments.values())}")
    print(f"Tickets: {total_tickets}")
    print(f"Ideal tickets per technician: {target:.2f}")
    print(f"Workload range: {max(loads.values()) - min(loads.values())} tickets")
    print()

    for technician, rows in assignments.items():
        print(f"{technician}: {len(rows)} categories, {loads[technician]} tickets ({loads[technician] - target:+.2f} vs ideal)")
        for category, count in rows:
            print(f"  - {category}: {count}")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Balance ticket categories between technicians.")
    parser.add_argument("--file", type=Path, default=find_file(), help="Path to ticket.xlsx")
    parser.add_argument(
        "--technicians",
        nargs=4,
        metavar=("TECH1", "TECH2", "TECH3", "TECH4"),
        default=DEFAULT_TECHNICIANS,
        help="Exactly four technician names",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    counts = load_category_counts(arguments.file)
    assignments = balance_categories(counts, arguments.technicians)
    print_report(assignments, int(counts.sum()))
