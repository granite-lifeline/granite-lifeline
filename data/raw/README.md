# Raw Dataset

The original dataset used in this project is not included in this repository due to its size and because it is publicly available from the original source.

## Dataset Information

**Dataset Name:** Automotive OBD-II Dataset

**Provider:** Karlsruhe Institute of Technology (KIT)

**Author:** Marc Weber

**Publication Year:** 2023

**DOI:** 10.35097/1130

**License:** CC BY 4.0

The dataset contains vehicle telemetry signals collected through the OBD-II interface using a KIWI 3 OBD dongle together with the OBD Auto Doctor mobile application.

Available signals include:

* Engine coolant temperature
* Intake manifold absolute pressure (MAP)
* Engine RPM
* Vehicle speed
* Intake air temperature
* Mass air flow (MAF)
* Absolute throttle position
* Ambient air temperature
* Accelerator pedal position D
* Accelerator pedal position E

The recordings cover multiple driving scenarios including urban traffic, free-flow traffic, and congestion conditions.

## Download

Download the dataset from:

https://radar.kit.edu/radar/en/dataset/bCtGxdTklQlfQcAq

## Repository Structure

After downloading, place the extracted files in the following directory:

```text
data/
└── raw/
    ├── 2017-xx-xx_*.csv
    ├── 2018-xx-xx_*.csv
    └── ...
```

No modifications should be applied to the raw files stored in this directory.

Processed datasets generated from the raw data are stored in:

```text
data/processed/
```
