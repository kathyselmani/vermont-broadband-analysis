# Business Questions

The analysis answers five questions about **residential fixed broadband in Vermont**
(FCC Broadband Data Collection, data as of December 31, 2025).

| # | Question | Where it is answered |
|---|----------|----------------------|
| 1 | How is reported broadband availability distributed across the state? What share of residential locations are served (≥ 100/20 Mbps), underserved or unserved? | `notebooks/03_exploratory_analysis.ipynb` §1, dashboard §01 |
| 2 | Which technologies reach Vermont homes, and at what advertised speeds? | notebook 03 §2, dashboard §02 |
| 3 | Where is provider choice limited? How many locations have zero, one, or several wired 100/20 providers, and which providers are the sole wired option? | notebook 03 §3 and §5, dashboard §03 and §05 |
| 4 | How does access vary geographically (county, census tract, H3 hexagon)? | notebook 03 §4 and §6, dashboard map and §04 |
| 5 | How does availability relate to population density, income, poverty and household broadband adoption? | `notebooks/04_socioeconomic.ipynb`, dashboard §06 |

## Out of scope

- Price, affordability and measured performance (the FCC data is *advertised* availability).
- Mobile broadband (only fixed availability files are used).
- Causal claims. Socioeconomic relationships are reported as descriptive associations.
