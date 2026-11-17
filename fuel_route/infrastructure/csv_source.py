import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fuel_route.domain.stations import StationRow


def read_station_csv(path: Path) -> list[StationRow]:
    """Parse the supplied price CSV; a malformed row aborts the import."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for line, record in enumerate(reader, start=2):
            try:
                price = Decimal(record["Retail Price"].strip())
                if not price.is_finite() or price <= 0:
                    raise ValueError("price must be positive")
                rows.append(
                    StationRow(
                        int(record["OPIS Truckstop ID"]),
                        record["Truckstop Name"].strip(),
                        record["Address"].strip(),
                        record["City"].strip(),
                        record["State"].strip(),
                        int(record["Rack ID"]),
                        price,
                    )
                )
            except (InvalidOperation, ValueError, KeyError, AttributeError) as error:
                raise ValueError(f"{path.name} line {line}: {error!r}") from error
    return rows
