# CBS socio-demographic analysis (Task 4.6)
# Data: CBS wijken en buurten 2024, selected buurten in the context area

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import os

# settings
GPKG = "cbs_with_reduced_fields.gpkg"  
GEMEENTEN = "cbs_gemeente_Rotterdam_Schiedam.gpkg"       # Rotterdam and Schiedam, for comparison
M4H = "BU05991926"                   # Rotterdam Nieuw Mathenesse (M4H)
EXCLUDE = "BU06060203"                # Schiedam industrial buurt, almost no residents
OUT = "cbs_output"
os.makedirs(OUT, exist_ok=True)

# load data
gdf = gpd.read_file(GPKG)
gdf = gdf[gdf["buurtcode"] != EXCLUDE]

#CBS uses large negative numbers for missing or secret values
num = gdf.select_dtypes("number").columns
gdf[num] = gdf[num].where(gdf[num] > -99990)

m4h = gdf[gdf["buurtcode"] == M4H].iloc[0]
city = gpd.read_file(GEMEENTEN).set_index("gemeentenaam")
rotterdam = city.loc["Rotterdam"]
schiedam = city.loc["Schiedam"]
others = gdf[gdf["buurtcode"] != M4H]

#need weighted mean
def weighted_mean(df, col, weight):
    d = df[[col, weight]].dropna()
    return (d[col] * d[weight]).sum() / d[weight].sum()


#variables
age = {
    "percentagePersonen0Tot15Jaar": "0-14",
    "percentagePersonen15Tot25Jaar": "15-24",
    "percentagePersonen25Tot45Jaar": "25-44",
    "percentagePersonen45Tot65Jaar": "45-64",
    "percentagePersonen65JaarEnOuder": "65+",
}
households = {
    "percentageEenpersoonshuishoudens": "Single-person",
    "percentageHuishoudensZonderKinderen": "Without children",
    "percentageHuishoudensMetKinderen": "With children",
}
facilities = {
    "groteSupermarktGemiddeldeAfstandInKm": "Large supermarket",
    "winkelsOvDagelijkseLevensmGemAfstInKm": "Daily groceries",
    "huisartsenpraktijkGemiddeldeAfstandInKm": "GP practice",
    "apotheekGemiddeldeAfstandInKm": "Pharmacy",
    "kinderdagverblijfGemiddeldeAfstandInKm": "Day care",
    "basisonderwijsGemiddeldeAfstandInKm": "Primary school",
    "treinstationGemiddeldeAfstandInKm": "Train station",
}
housing = ["percentageKoopwoningen", "percHuurwoningenInBezitWoningcorporaties"]
cars = "personenautosPerHuishouden"

#summary table
# person-based variables are weighted by residents, household-based by households,housing-based by number of dwellings
weights = {}
for c in list(age) + list(facilities):
    weights[c] = "aantalInwoners"
for c in list(households) + [cars]:
    weights[c] = "aantalHuishoudens"
for c in housing:
    weights[c] = "woningvoorraad"

rows = []
for col, w in weights.items():
    rows.append({
        "variable": col,
        "study_area": round(weighted_mean(gdf, col, w), 2),
        "surrounding": round(weighted_mean(others, col, w), 2),
        "M4H": m4h[col],
        "Rotterdam": rotterdam[col],
        "Schiedam": schiedam[col],
    })
summary = pd.DataFrame(rows)
summary.to_csv(f"{OUT}/summary_table.csv", index=False)
print(summary.to_string(index=False))

#Figure 1: age pie chart
values = [weighted_mean(gdf, c, "aantalInwoners") for c in age]
plt.figure(figsize=(5, 5))
plt.pie(values, labels=age.values(), autopct="%1.0f%%", startangle=90)
plt.title("Age structure - study area")
plt.savefig(f"{OUT}/01_age_pie.png", dpi=150, bbox_inches="tight")
plt.close()

#figure 2: household types per buurt 
hh = gdf.set_index("buurtnaam")[list(households)].dropna()
hh.loc["ROTTERDAM (city)"] = rotterdam[list(households)]
hh.loc["SCHIEDAM (city)"] = schiedam[list(households)]
hh = hh.rename(columns=households).sort_values("Single-person")
hh.plot.barh(stacked=True, figsize=(8, 6), width=0.75)
plt.xlabel("% of households")
plt.ylabel("")
plt.title("Household composition per buurt")
plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False)
plt.savefig(f"{OUT}/02_households.png", dpi=150, bbox_inches="tight")
plt.close()


# Figures 3 and 4: map of cars per househoul and map of social housing
def make_map(col, title, filename):
    ax = gdf.plot(column=col, cmap="OrRd", legend=True, edgecolor="white", figsize=(8, 7),
                  missing_kwds={"color": "lightgrey"})
    gdf[gdf["buurtcode"] == M4H].boundary.plot(ax=ax, color="black", linewidth=2)
    for _, row in gdf.iterrows():
        p = row.geometry.representative_point()
        ax.annotate(row["buurtnaam"], (p.x, p.y), fontsize=6, ha="center")
    ax.set_title(title)
    ax.set_axis_off()
    plt.savefig(f"{OUT}/{filename}", dpi=150, bbox_inches="tight")
    plt.close()


make_map(cars, "Cars per household (M4H outlined)", "03_cars_map.png")
make_map("percHuurwoningenInBezitWoningcorporaties", "Social housing % (M4H outlined)",
         "04_social_housing_map.png")

# figure 5: facility distances, M4H vs surroundings 
dist = pd.DataFrame({
    "M4H": [m4h[c] for c in facilities],
    "Surrounding buurten": [weighted_mean(others, c, "aantalInwoners") for c in facilities],
    "Rotterdam (city)": [rotterdam[c] for c in facilities],
}, index=facilities.values())
dist.plot.barh(figsize=(8, 5), width=0.75)
plt.gca().invert_yaxis()
plt.xlabel("Average distance by road (km)")
plt.title("Distance to nearest facility")
plt.savefig(f"{OUT}/05_facility_distance.png", dpi=150, bbox_inches="tight")
plt.close()

# Export 
cols = ["buurtcode", "buurtnaam", "aantalInwoners", "aantalHuishoudens"] + list(weights)
gdf[cols].to_csv(f"{OUT}/buurten.csv", index=False)
gdf[cols + ["geometry"]].to_crs(4326).to_file(f"{OUT}/buurten.geojson", driver="GeoJSON")

print("Done", OUT)