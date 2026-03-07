"""
Metric Explanations — structured educational content for each
environmental factor displayed in the Data Explorer.

Each entry provides:
  title       — display name
  subtitle    — short tagline
  what        — what the data represents
  factors     — key factors influencing the metric
  impact      — environmental / health impact
  solutions   — best practices and solutions
  did_you_know — an engaging fact
"""

METRIC_EXPLANATIONS = {
    "co2_per_capita": {
        "title": "CO₂ Emissions per Capita",
        "subtitle": "Measuring each nation's carbon footprint",
        "what": (
            "This metric measures the average tonnes of carbon dioxide emitted "
            "per person per year. It accounts for emissions from burning fossil "
            "fuels (coal, oil, natural gas), industrial processes such as cement "
            "production, and flaring. By expressing it per capita, we can fairly "
            "compare countries of vastly different population sizes."
        ),
        "factors": (
            "• <b>Energy mix</b> — Countries reliant on coal and oil have higher "
            "per-capita emissions than those using renewables or nuclear.<br>"
            "• <b>Industrialization level</b> — Manufacturing-heavy economies "
            "produce more CO₂ per person.<br>"
            "• <b>Transportation</b> — Car-dependent societies with low public "
            "transit usage emit significantly more.<br>"
            "• <b>Climate & geography</b> — Cold climates require more heating; "
            "vast distances increase transport emissions.<br>"
            "• <b>Policy</b> — Carbon taxes, emissions trading, and efficiency "
            "standards directly influence national emissions."
        ),
        "impact": (
            "CO₂ is the primary greenhouse gas driving global warming. Every "
            "additional tonne traps heat in the atmosphere, contributing to rising "
            "sea levels, more extreme weather events, ocean acidification, and "
            "disruption of ecosystems worldwide. The Paris Agreement aims to limit "
            "warming to 1.5 °C, requiring global emissions to reach net-zero by 2050."
        ),
        "solutions": (
            "• Transition to renewable energy (solar, wind, hydro)<br>"
            "• Electrify transportation and expand public transit<br>"
            "• Improve building energy efficiency and insulation<br>"
            "• Implement carbon pricing mechanisms<br>"
            "• Protect and restore carbon sinks (forests, wetlands)<br>"
            "• Shift diets toward lower-carbon food sources"
        ),
        "did_you_know": (
            "If everyone on Earth emitted as much CO₂ as the average American "
            "(~14 t/year), global emissions would be over <b>4× higher</b> than "
            "current levels — exceeding 100 billion tonnes annually."
        ),
    },

    "renewable_percentage": {
        "title": "Renewable Energy Share",
        "subtitle": "Tracking the global shift to clean power",
        "what": (
            "This metric shows the percentage of a country's total energy "
            "consumption that comes from renewable sources — including hydro, "
            "solar, wind, geothermal, and biomass. A higher percentage indicates "
            "less dependence on fossil fuels and a cleaner energy profile."
        ),
        "factors": (
            "• <b>Natural resources</b> — Countries with abundant rivers (hydro), "
            "sunlight (solar), or wind corridors have natural advantages.<br>"
            "• <b>Government policy</b> — Feed-in tariffs, subsidies, and "
            "renewable mandates accelerate adoption.<br>"
            "• <b>Grid infrastructure</b> — Modern grids with energy storage can "
            "handle variable renewable supply.<br>"
            "• <b>Investment costs</b> — Solar panel prices have dropped 90% "
            "since 2010, making renewables cost-competitive.<br>"
            "• <b>Political will</b> — National commitments and international "
            "agreements drive long-term transitions."
        ),
        "impact": (
            "Every percentage point shift from fossil fuels to renewables reduces "
            "greenhouse gas emissions, improves air quality, and decreases "
            "energy import dependence. Renewable energy also creates green jobs — "
            "the sector employed 13.7 million people globally in 2022. "
            "However, challenges remain around energy storage, grid stability, "
            "and land use for large-scale installations."
        ),
        "solutions": (
            "• Invest in utility-scale solar and offshore wind<br>"
            "• Deploy grid-scale battery storage systems<br>"
            "• Modernize power grids for bidirectional energy flow<br>"
            "• Incentivize rooftop solar and community energy projects<br>"
            "• Phase out fossil fuel subsidies<br>"
            "• Support R&D in emerging tech (green hydrogen, wave energy)"
        ),
        "did_you_know": (
            "Iceland generates nearly <b>100%</b> of its electricity from "
            "renewables — primarily geothermal and hydropower — making it one "
            "of the cleanest energy systems on Earth."
        ),
    },

    "forest_area_percentage": {
        "title": "Forest Coverage",
        "subtitle": "The planet's green lungs under pressure",
        "what": (
            "This metric represents the percentage of a country's total land area "
            "covered by forest. Forests include natural and planted trees, but "
            "exclude tree stands used primarily for agriculture (such as fruit "
            "orchards or palm oil plantations). It is a key indicator of "
            "ecological health and carbon sequestration capacity."
        ),
        "factors": (
            "• <b>Deforestation</b> — Agricultural expansion, logging, and "
            "urban sprawl are the largest drivers of forest loss.<br>"
            "• <b>Reforestation programs</b> — Some nations actively replant "
            "forests to recover lost coverage.<br>"
            "• <b>Climate conditions</b> — Tropical regions naturally have "
            "higher forest density; arid zones have less.<br>"
            "• <b>Legal protections</b> — National parks, conservation laws, "
            "and indigenous land rights help preserve forests.<br>"
            "• <b>Economic pressures</b> — Demand for palm oil, soy, cattle "
            "ranching, and timber drives deforestation in developing economies."
        ),
        "impact": (
            "Forests absorb approximately 2.6 billion tonnes of CO₂ per year — "
            "about 30% of human emissions. They regulate local weather, prevent "
            "soil erosion, filter water, and host ~80% of the world's terrestrial "
            "biodiversity. Deforestation releases stored carbon back into the "
            "atmosphere and is responsible for roughly 10% of global emissions."
        ),
        "solutions": (
            "• Enforce anti-deforestation laws and combat illegal logging<br>"
            "• Support community-based forest management<br>"
            "• Promote sustainable agriculture to reduce land conversion<br>"
            "• Invest in large-scale reforestation and afforestation<br>"
            "• Choose certified sustainable products (FSC-certified wood)<br>"
            "• Protect indigenous peoples' land rights"
        ),
        "did_you_know": (
            "The Amazon Rainforest produces <b>20%</b> of the world's oxygen and "
            "stores 150–200 billion tonnes of carbon. Losing it would accelerate "
            "global warming dramatically."
        ),
    },

    "pm25": {
        "title": "Air Pollution (PM2.5)",
        "subtitle": "Invisible particles, visible health crisis",
        "what": (
            "PM2.5 refers to particulate matter smaller than 2.5 micrometers — "
            "about 30× thinner than a human hair. This metric shows the annual "
            "mean concentration of PM2.5 in a country's air (µg/m³). These "
            "particles come from vehicle exhaust, industrial emissions, "
            "construction dust, wildfires, and household cooking with solid fuels."
        ),
        "factors": (
            "• <b>Fossil fuel combustion</b> — Coal power plants and diesel "
            "vehicles are major PM2.5 sources.<br>"
            "• <b>Industrial activity</b> — Manufacturing, mining, and "
            "construction generate significant particulate matter.<br>"
            "• <b>Agricultural burning</b> — Crop residue burning creates "
            "seasonal pollution spikes in many developing countries.<br>"
            "• <b>Geography</b> — Valleys and basins trap pollutants; coastal "
            "cities benefit from sea breezes.<br>"
            "• <b>Regulation</b> — Emission standards for vehicles and industry "
            "vary widely between countries."
        ),
        "impact": (
            "PM2.5 particles penetrate deep into the lungs and bloodstream, "
            "causing heart disease, stroke, lung cancer, and respiratory illness. "
            "The WHO estimates air pollution causes <b>7 million premature deaths</b> "
            "annually. The WHO guideline level is just 5 µg/m³ — yet many countries "
            "exceed 50 µg/m³, exposing billions to unsafe air quality daily."
        ),
        "solutions": (
            "• Transition from coal to clean energy sources<br>"
            "• Enforce strict vehicle emission standards (Euro 6/EPA Tier 3)<br>"
            "• Promote electric vehicles and public transportation<br>"
            "• Ban open-air crop burning and provide alternatives<br>"
            "• Improve industrial emission controls and monitoring<br>"
            "• Plant urban green belts to filter particulate matter"
        ),
        "did_you_know": (
            "Breathing air at 50 µg/m³ PM2.5 (common in many cities) is equivalent "
            "to smoking <b>2–3 cigarettes per day</b>. Children and elderly are "
            "most vulnerable to its effects."
        ),
    },
}
