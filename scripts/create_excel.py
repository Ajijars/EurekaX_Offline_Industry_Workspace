import pandas as pd
import json

def create_excel():
    with open('data/real_datasets/dummy_products.json', 'r') as f:
        data = json.load(f)
    
    products = data.get('products', [])
    df = pd.DataFrame(products)
    
    # Select some interesting columns
    df = df[['id', 'title', 'category', 'price', 'rating', 'stock', 'brand']]
    
    # Save as Excel
    df.to_excel('data/real_datasets/products_financial.xlsx', index=False)
    print("Created products_financial.xlsx")

if __name__ == '__main__':
    create_excel()
