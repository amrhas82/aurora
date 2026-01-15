#!/usr/bin/env python3
"""SaaS Financial Model with Tiered Pricing
Comprehensive revenue, cost, and growth projections
"""

import json
from dataclasses import dataclass

import pandas as pd


@dataclass
class PricingTier:
    """Pricing tier configuration"""

    name: str
    monthly_price: float
    annual_price: float
    features: list[str]
    target_segment: str


@dataclass
class CustomerMetrics:
    """Customer acquisition and retention metrics"""

    tier: str
    initial_count: int
    monthly_growth_rate: float
    churn_rate: float
    acquisition_cost: float


class SaaSFinancialModel:
    """Complete financial model for SaaS business"""

    def __init__(self, months: int = 36):
        self.months = months
        self.pricing_tiers = self._define_pricing_tiers()
        self.customer_metrics = self._define_customer_metrics()

    def _define_pricing_tiers(self) -> dict[str, PricingTier]:
        """Define tiered pricing structure"""
        return {
            "starter": PricingTier(
                name="Starter",
                monthly_price=29,
                annual_price=290,  # 2 months free
                features=["Basic features", "Email support", "5 users"],
                target_segment="Small businesses, freelancers",
            ),
            "professional": PricingTier(
                name="Professional",
                monthly_price=99,
                annual_price=990,
                features=["Advanced features", "Priority support", "20 users", "API access"],
                target_segment="Growing teams",
            ),
            "enterprise": PricingTier(
                name="Enterprise",
                monthly_price=299,
                annual_price=2990,
                features=[
                    "All features",
                    "24/7 support",
                    "Unlimited users",
                    "Custom integrations",
                    "SLA",
                ],
                target_segment="Large organizations",
            ),
        }

    def _define_customer_metrics(self) -> dict[str, CustomerMetrics]:
        """Define customer acquisition and retention by tier"""
        return {
            "starter": CustomerMetrics(
                tier="starter",
                initial_count=50,
                monthly_growth_rate=0.15,  # 15% monthly growth
                churn_rate=0.08,  # 8% monthly churn
                acquisition_cost=150,
            ),
            "professional": CustomerMetrics(
                tier="professional",
                initial_count=20,
                monthly_growth_rate=0.12,
                churn_rate=0.05,
                acquisition_cost=500,
            ),
            "enterprise": CustomerMetrics(
                tier="enterprise",
                initial_count=5,
                monthly_growth_rate=0.08,
                churn_rate=0.03,
                acquisition_cost=2000,
            ),
        }

    def calculate_customers(self) -> pd.DataFrame:
        """Calculate customer counts over time"""
        results = []

        for month in range(self.months):
            month_data = {"month": month + 1}

            for tier_name, metrics in self.customer_metrics.items():
                if month == 0:
                    customers = metrics.initial_count
                else:
                    prev_customers = results[month - 1][f"{tier_name}_customers"]
                    # New customers from growth
                    new_customers = prev_customers * metrics.monthly_growth_rate
                    # Lost customers from churn
                    churned = prev_customers * metrics.churn_rate
                    customers = prev_customers + new_customers - churned

                month_data[f"{tier_name}_customers"] = int(customers)

            results.append(month_data)

        return pd.DataFrame(results)

    def calculate_revenue(
        self, customers_df: pd.DataFrame, annual_ratio: float = 0.3
    ) -> pd.DataFrame:
        """Calculate MRR and ARR by tier

        Args:
            customers_df: Customer counts by tier
            annual_ratio: Proportion of customers on annual plans
        """
        revenue_data = customers_df.copy()

        for tier_name, tier in self.pricing_tiers.items():
            customers = revenue_data[f"{tier_name}_customers"]

            # Split between monthly and annual
            monthly_customers = customers * (1 - annual_ratio)
            annual_customers = customers * annual_ratio

            # Monthly recurring revenue
            mrr = monthly_customers * tier.monthly_price + annual_customers * tier.annual_price / 12

            revenue_data[f"{tier_name}_mrr"] = mrr.round(2)

        # Total MRR
        revenue_data["total_mrr"] = (
            revenue_data["starter_mrr"]
            + revenue_data["professional_mrr"]
            + revenue_data["enterprise_mrr"]
        )

        # ARR (Annual Run Rate)
        revenue_data["arr"] = revenue_data["total_mrr"] * 12

        return revenue_data

    def calculate_costs(self, revenue_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate operating costs"""
        cost_data = revenue_df.copy()

        # Customer Acquisition Cost (CAC)
        for tier_name, metrics in self.customer_metrics.items():
            new_customers = (
                cost_data[f"{tier_name}_customers"]
                .diff()
                .fillna(cost_data[f"{tier_name}_customers"].iloc[0])
            )
            cost_data[f"{tier_name}_cac"] = (new_customers * metrics.acquisition_cost).clip(lower=0)

        cost_data["total_cac"] = (
            cost_data["starter_cac"] + cost_data["professional_cac"] + cost_data["enterprise_cac"]
        )

        # Cost of Goods Sold (COGS) - hosting, infrastructure
        # Assume 15% of revenue
        cost_data["cogs"] = cost_data["total_mrr"] * 0.15

        # Operating Expenses
        # Scale with revenue but have fixed component
        base_opex = 20000  # Base monthly operating expenses

        cost_data["sales_marketing"] = cost_data["total_cac"]
        cost_data["engineering"] = base_opex * 0.4 + cost_data["total_mrr"] * 0.10
        cost_data["support"] = base_opex * 0.2 + cost_data["total_mrr"] * 0.08
        cost_data["general_admin"] = base_opex * 0.4 + cost_data["total_mrr"] * 0.07

        cost_data["total_opex"] = (
            cost_data["sales_marketing"]
            + cost_data["engineering"]
            + cost_data["support"]
            + cost_data["general_admin"]
        )

        # Total costs
        cost_data["total_costs"] = cost_data["cogs"] + cost_data["total_opex"]

        # Profit/Loss
        cost_data["ebitda"] = cost_data["total_mrr"] - cost_data["total_costs"]
        cost_data["cumulative_profit"] = cost_data["ebitda"].cumsum()

        return cost_data

    def calculate_unit_economics(self, financial_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate key unit economics metrics"""
        metrics = financial_df.copy()

        for tier_name in self.pricing_tiers.keys():
            tier = self.pricing_tiers[tier_name]
            tier_metrics = self.customer_metrics[tier_name]

            # Lifetime Value (LTV)
            avg_customer_lifetime_months = 1 / tier_metrics.churn_rate
            ltv = tier.monthly_price * avg_customer_lifetime_months

            # CAC Payback Period (months)
            cac_payback = tier_metrics.acquisition_cost / tier.monthly_price

            # LTV:CAC Ratio
            ltv_cac_ratio = ltv / tier_metrics.acquisition_cost

            metrics[f"{tier_name}_ltv"] = ltv
            metrics[f"{tier_name}_cac_payback"] = cac_payback
            metrics[f"{tier_name}_ltv_cac"] = ltv_cac_ratio

        return metrics

    def generate_summary_metrics(self, financial_df: pd.DataFrame) -> dict:
        """Generate key summary metrics"""
        latest = financial_df.iloc[-1]
        first = financial_df.iloc[0]

        return {
            "final_month": int(latest["month"]),
            "total_customers": sum(
                [int(latest[f"{tier}_customers"]) for tier in self.pricing_tiers.keys()]
            ),
            "monthly_recurring_revenue": float(latest["total_mrr"]),
            "annual_run_rate": float(latest["arr"]),
            "cumulative_profit": float(latest["cumulative_profit"]),
            "months_to_profitability": (
                int(financial_df[financial_df["cumulative_profit"] > 0]["month"].min())
                if (financial_df["cumulative_profit"] > 0).any()
                else None
            ),
            "revenue_growth": {
                "first_month_mrr": float(first["total_mrr"]),
                "last_month_mrr": float(latest["total_mrr"]),
                "total_growth_pct": float(
                    ((latest["total_mrr"] - first["total_mrr"]) / first["total_mrr"]) * 100
                ),
            },
            "unit_economics": {
                tier: {
                    "ltv": float(latest[f"{tier}_ltv"]),
                    "cac_payback_months": float(latest[f"{tier}_cac_payback"]),
                    "ltv_cac_ratio": float(latest[f"{tier}_ltv_cac"]),
                }
                for tier in self.pricing_tiers.keys()
            },
        }

    def run_model(self) -> tuple[pd.DataFrame, dict]:
        """Run complete financial model"""
        # Calculate customer progression
        customers_df = self.calculate_customers()

        # Calculate revenue
        revenue_df = self.calculate_revenue(customers_df)

        # Calculate costs and profitability
        financial_df = self.calculate_costs(revenue_df)

        # Add unit economics
        financial_df = self.calculate_unit_economics(financial_df)

        # Generate summary
        summary = self.generate_summary_metrics(financial_df)

        return financial_df, summary

    def export_to_csv(self, financial_df: pd.DataFrame, filename: str = "saas_financial_model.csv"):
        """Export financial model to CSV"""
        financial_df.to_csv(filename, index=False)
        print(f"Financial model exported to {filename}")

    def export_summary(self, summary: dict, filename: str = "saas_summary.json"):
        """Export summary metrics to JSON"""
        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary metrics exported to {filename}")

    def print_summary(self, summary: dict):
        """Print formatted summary"""
        print("\n" + "=" * 60)
        print("SaaS FINANCIAL MODEL SUMMARY")
        print("=" * 60)

        print(f"\nFinal Month: {summary['final_month']}")
        print(f"Total Customers: {summary['total_customers']:,}")
        print(f"Monthly Recurring Revenue: ${summary['monthly_recurring_revenue']:,.2f}")
        print(f"Annual Run Rate: ${summary['annual_run_rate']:,.2f}")
        print(f"Cumulative Profit: ${summary['cumulative_profit']:,.2f}")

        if summary["months_to_profitability"]:
            print(f"Months to Profitability: {summary['months_to_profitability']}")
        else:
            print("Months to Profitability: Not yet profitable")

        print("\nRevenue Growth:")
        print(f"  First Month MRR: ${summary['revenue_growth']['first_month_mrr']:,.2f}")
        print(f"  Last Month MRR: ${summary['revenue_growth']['last_month_mrr']:,.2f}")
        print(f"  Total Growth: {summary['revenue_growth']['total_growth_pct']:.1f}%")

        print("\nUnit Economics by Tier:")
        for tier, metrics in summary["unit_economics"].items():
            print(f"  {tier.upper()}:")
            print(f"    LTV: ${metrics['ltv']:,.2f}")
            print(f"    CAC Payback: {metrics['cac_payback_months']:.1f} months")
            print(f"    LTV:CAC Ratio: {metrics['ltv_cac_ratio']:.2f}x")

        print("\n" + "=" * 60 + "\n")


def main():
    """Run the financial model"""
    # Create 3-year model
    model = SaaSFinancialModel(months=36)

    # Run the model
    financial_df, summary = model.run_model()

    # Print summary
    model.print_summary(summary)

    # Export results
    model.export_to_csv(financial_df)
    model.export_summary(summary)

    # Print sample of detailed data
    print("Sample Financial Data (First 6 months):")
    print(
        financial_df[["month", "total_mrr", "arr", "total_costs", "ebitda", "cumulative_profit"]]
        .head(6)
        .to_string(index=False)
    )

    print("\nSample Financial Data (Last 6 months):")
    print(
        financial_df[["month", "total_mrr", "arr", "total_costs", "ebitda", "cumulative_profit"]]
        .tail(6)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
