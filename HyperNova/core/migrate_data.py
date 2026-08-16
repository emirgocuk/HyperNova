import shutil
import os
import glob

def migrate():
    # Define source and dest
    # Using raw string for source to handle special chars if needed, but python handles paths well
    source_dir = r"d:\Projects\playroom\trading-bot\roadmap-moondev\Free Algo Trading Roadmap, Resources & Discord"
    dest_dir = r"d:\Projects\playroom\trading-bot\HyperNova\data"
    
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        
    print(f"Looking for CSVs in {source_dir}")
    csv_files = glob.glob(os.path.join(source_dir, "*.csv"))
    
    if not csv_files:
        print("No CSV files found!")
        return
        
    print(f"Found {len(csv_files)} files. Copying...")
    for f in csv_files:
        try:
            shutil.copy2(f, dest_dir)
            print(f"Copied {os.path.basename(f)}")
        except Exception as e:
            print(f"Error copying {f}: {e}")
            
if __name__ == "__main__":
    migrate()
