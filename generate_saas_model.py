import csv
import json

# Pricing tiers (monthly)
tiers = {"starter": 29, "professional": 99, "enterprise": 299}
customers = {"starter": 10, "professional": 5, "enterprise": 2}
growth = {"starter": 0.15, "professional": 0.12, "enterprise": 0.08}
churn = {"starter": 0.05, "professional": 0.03, "enterprise": 0.02}

# Costs
fixed_monthly = 78000  # Salaries 50k + office 5k + software 3k + marketing 15k + other 5k
var_per_customer = 5

projections = []

for month in range(60):
    year = month // 12

    # Apply 5% annual price increase
    prices = {t: tiers[t] * (1.05**year) for t in tiers}

    # Calculate customer growth/churn
    if month > 0:
        for tier in tiers:
            new = int(customers[tier] * growth[tier])
            churned = int(customers[tier] * churn[tier])
            customers[tier] = customers[tier] + new - churned

    # Revenue
    mrr = sum(customers[t] * prices[t] for t in tiers)
    arr = mrr * 12

    # Costs
    total_customers = sum(customers.values())
    var_costs = total_customers * var_per_customer
    fixed = fixed_monthly * (1.10**year)  # 10% annual salary increase
    total_costs = fixed + var_costs

    # Profit
    net_profit = mrr - total_costs
    margin = (net_profit / mrr * 100) if mrr > 0 else 0

    projections.append(
        {
            "Month": month,
            "Year": year,
            "Customers_Starter": customers["starter"],
            "Customers_Professional": customers["professional"],
            "Customers_Enterprise": customers["enterprise"],
            "Total_Customers": total_customers,
            "Price_Starter": round(prices["starter"], 2),
            "Price_Professional": round(prices["professional"], 2),
            "Price_Enterprise": round(prices["enterprise"], 2),
            "MRR": round(mrr, 2),
            "ARR": round(arr, 2),
            "Fixed_Costs": round(fixed, 2),
            "Variable_Costs": round(var_costs, 2),
            "Total_Costs": round(total_costs, 2),
            "Net_Profit": round(net_profit, 2),
            "Net_Margin_Pct": round(margin, 1),
        }
    )

# Summary
first, last = projections[0], projections[-1]
print("SaaS Financial Model - 5 Year Projection")
print("=" * 60)
print(f"\nINITIAL STATE (Month 0):")
print(
    f"  Customers: {first['Total_Customers']} (S:{first['Customers_Starter']}, P:{first['Customers_Professional']}, E:{first['Customers_Enterprise']})"
)
print(f"  MRR: ${first['MRR']:,.0f}")
print(f"  ARR: ${first['ARR']:,.0f}")
print(f"  Net Profit: ${first['Net_Profit']:,.0f}")
print(f"  Margin: {first['Net_Margin_Pct']:.1f}%")

print(f"\nFINAL STATE (Year 5, Month 59):")
print(
    f"  Customers: {last['Total_Customers']} (S:{last['Customers_Starter']}, P:{last['Customers_Professional']}, E:{last['Customers_Enterprise']})"
)
print(f"  MRR: ${last['MRR']:,.0f}")
print(f"  ARR: ${last['ARR']:,.0f}")
print(f"  Net Profit: ${last['Net_Profit']:,.0f}")
print(f"  Margin: {last['Net_Margin_Pct']:.1f}%")

print(f"\nGROWTH METRICS:")
print(
    f"  Customer Growth: {((last['Total_Customers']-first['Total_Customers'])/first['Total_Customers']*100):.0f}%"
)
print(f"  MRR Growth: {((last['MRR']-first['MRR'])/first['MRR']*100):.0f}%")
print(f"  ARR Growth: {((last['ARR']-first['ARR'])/first['ARR']*100):.0f}%")

# Find profitability month
prof_month = next((p["Month"] for p in projections if p["Net_Profit"] > 0), None)
if prof_month:
    print(f"  Months to Profitability: {prof_month}")
else:
    print(f"  Months to Profitability: Not achieved in projection")

# Save CSV
with open("saas_financial_model.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=projections[0].keys())
    writer.writeheader()
    writer.writerows(projections)
print("\n" + "=" * 60)
print("Saved: saas_financial_model.csv")

# Save summary JSON
summary = {
    "pricing_tiers": {
        "starter": {"initial_price": 29, "features": "Basic"},
        "professional": {"initial_price": 99, "features": "Advanced"},
        "enterprise": {"initial_price": 299, "features": "Full suite + support"},
    },
    "assumptions": {
        "monthly_growth_rate": growth,
        "churn_rate": churn,
        "annual_price_increase": 0.05,
        "annual_salary_increase": 0.10,
        "variable_cost_per_customer": var_per_customer,
    },
    "initial": {
        "customers": first["Total_Customers"],
        "mrr": first["MRR"],
        "arr": first["ARR"],
        "profit": first["Net_Profit"],
        "margin_pct": first["Net_Margin_Pct"],
    },
    "final": {
        "month": 59,
        "year": 4,
        "customers": last["Total_Customers"],
        "mrr": last["MRR"],
        "arr": last["ARR"],
        "profit": last["Net_Profit"],
        "margin_pct": last["Net_Margin_Pct"],
    },
    "growth": {
        "customer_growth_pct": round(
            ((last["Total_Customers"] - first["Total_Customers"]) / first["Total_Customers"] * 100),
            1,
        ),
        "mrr_growth_pct": round(((last["MRR"] - first["MRR"]) / first["MRR"] * 100), 1),
        "arr_growth_pct": round(((last["ARR"] - first["ARR"]) / first["ARR"] * 100), 1),
    },
    "metrics": {"months_to_profitability": prof_month},
}
with open("saas_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("Saved: saas_summary.json")
print("=" * 60)
