import os
import pandas as pd
import numpy as np
from pathlib import Path
from PIL import Image

# Setup directories
DATA_DIR = Path("data/samples")
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR = DATA_DIR / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

print(f"Generating mock data in {DATA_DIR.absolute()}")

# 1. Employees Data (CSV)
np.random.seed(42)
num_employees = 150
departments = ["Sales", "Engineering", "HR", "Marketing", "Finance"]
employees = pd.DataFrame({
    "employee_id": [f"EMP-{i:04d}" for i in range(1, num_employees + 1)],
    "first_name": ["John", "Jane", "Alice", "Bob", "Charlie"] * 30,
    "last_name": ["Doe", "Smith", "Johnson", "Brown", "Davis"] * 30,
    "department": np.random.choice(departments, num_employees),
    "salary": np.random.randint(50000, 150000, num_employees),
    "hire_date": pd.date_range(start="2018-01-01", periods=num_employees, freq="W").strftime("%Y-%m-%d")
})
employees.to_csv(DATA_DIR / "employees.csv", index=False)
print("Created employees.csv")

# 2. Retail Data (CSV)
num_tx = 1000
sales = pd.DataFrame({
    "transaction_id": [f"TX-{i:06d}" for i in range(1, num_tx + 1)],
    "date": pd.date_range(start="2023-01-01", periods=num_tx, freq="h").strftime("%Y-%m-%d %H:%M:%S"),
    "store_id": np.random.choice(["STORE-01", "STORE-02", "STORE-03", "ONLINE"], num_tx, p=[0.2, 0.3, 0.1, 0.4]),
    "amount": np.round(np.random.uniform(10.50, 1500.00, num_tx), 2),
    "customer_segment": np.random.choice(["New", "Returning", "VIP"], num_tx)
})
sales.to_csv(DATA_DIR / "sales_transactions.csv", index=False)
print("Created sales_transactions.csv")

# 3. Financial Data (Excel)
try:
    months = ["July", "August", "September"]
    financials = pd.DataFrame({
        "Category": ["Software Subscriptions", "Hardware Sales", "Consulting", "Server Costs", "Marketing", "Payroll"],
        "July_2023": np.random.randint(10000, 500000, 6),
        "August_2023": np.random.randint(10000, 500000, 6),
        "September_2023": np.random.randint(10000, 500000, 6)
    })
    financials["Q3_Total"] = financials["July_2023"] + financials["August_2023"] + financials["September_2023"]
    financials.to_excel(DATA_DIR / "q3_financials.xlsx", index=False, sheet_name="Q3_2023")
    print("Created q3_financials.xlsx")
except Exception as e:
    print(f"Could not create Excel (missing openpyxl?): {e}")
    # Fallback to CSV
    financials.to_csv(DATA_DIR / "q3_financials.csv", index=False)
    print("Created q3_financials.csv as fallback")

# 4. Image Data
# Generate a few solid color dummy images representing products
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
names = ["product_widget_a", "product_gadget_b", "product_tool_c", "product_device_d", "product_accessory_e"]
for color, name in zip(colors, names):
    img = Image.new('RGB', (200, 200), color=color)
    img.save(IMG_DIR / f"{name}.jpg")
print("Created 5 sample product images in data/samples/images/")

print("Sample data generation complete!")
