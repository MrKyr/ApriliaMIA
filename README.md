# Aprilia MIA Telemetry Converters

Python scripts for converting encrypted Aprilia MIA backup exports into standard CSV telemetry files and GPX tracks.

## Features

- **CSV converter (`aprilia_to_csv.py`)** — extracts trip telemetry and activity summaries into CSV files.
- **GPX converter (`aprilia_to_gpx.py`)** — converts recorded GPS tracks into GPX 1.1 files that can be opened in compatible mapping, GPS, and track-analysis applications.

Both scripts use the JSON backup exported by Aprilia MIA as their input.

## Requirements

- Python 3.9 or newer
- The Python [`cryptography`](https://pypi.org/project/cryptography/) package
- A compatible encrypted Aprilia MIA JSON backup export

Install the dependency with:

```bash
python -m pip install cryptography
```

## Usage

Place the scripts and your exported JSON file in a working directory, or provide the path to the JSON file when running a script.

### 1. Convert telemetry to CSV

Run:

```bash
python aprilia_to_csv.py Aprilia_2610271805.json
```

Replace `Aprilia_2610271805.json` with the name or path of your own export file.

The script creates an `Aprilia-Telemetry/` directory containing the generated CSV files, including:

- **Per-trip telemetry files** — timestamped telemetry records for each trip.
- **`trips-summary.csv`** — activity summary records, including a formatted duration and the corresponding telemetry filename when available.
- **`telemetry-index.csv`** — an index of exported telemetry files, with trip identifiers, dates, and row counts.

The summary and index files are generated when activity records are available in the export.

### 2. Convert GPS tracks to GPX

Run:

```bash
python aprilia_to_gpx.py Aprilia_2610271805.json
```

Replace the example filename with your own export.

The script creates an `Aprilia-GPX/` directory containing one `.gpx` file for each trip with at least two valid GPS points.

The GPX files use the GPX 1.1 format and include GPS coordinates, elevation, and timestamps. They can be imported into compatible mapping and GPS applications.

## Input format

The scripts expect an encrypted Aprilia MIA JSON backup export containing trip and activity records. They are not general-purpose converters for arbitrary JSON files.

The export metadata contains the user identifier used by the scripts to derive the decryption key. The scripts decrypt the records locally and do not require uploading the export to an online service.

If the input file is missing, the format is not recognized, or the export contains records that cannot be processed, the scripts report errors or skip invalid records as appropriate.

## Privacy

**Treat your original JSON export and generated telemetry as private data.**

Telemetry may contain GPS coordinates, timestamps, trip history, and other information that reveals where and when you travelled. The original export also contains metadata used during decryption.

- Do not commit your personal JSON export or generated telemetry files to a public repository.
- Keep private exports and output directories outside the repository, or exclude them using `.gitignore`.
- Review GPX and CSV files before sharing them, especially if they contain home, work, or other sensitive locations.

## Limitations

- The scripts depend on the structure and encryption format of the Aprilia MIA backup export. Changes to that format may require code updates.
- GPX output requires at least two valid GPS points per trip.
- The converters process a supplied JSON export; they do not connect directly to the motorcycle or the Aprilia MIA app.

## License

See the source files for the existing copyright and rights notice. No additional licence is granted by this README.
