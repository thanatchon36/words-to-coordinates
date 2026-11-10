#!/usr/bin/env bash
# Downloads the open datasets used in the simulation study into ./data
set -euo pipefail
mkdir -p data
curl -sSL -o data/gppd.csv "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv"
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
curl -sSL -o data/ne_110m_land.geojson   "$NE/ne_110m_land.geojson"
curl -sSL -o data/ne_50m_land.geojson    "$NE/ne_50m_land.geojson"
curl -sSL -o data/ne_50m_admin0.geojson  "$NE/ne_50m_admin_0_countries.geojson"
echo "Data downloaded to ./data"
