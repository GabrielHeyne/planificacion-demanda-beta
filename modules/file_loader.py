import pandas as pd

# Función para cargar y validar archivos
def cargar_archivos(demanda_file, stock_file):
    # Cargar archivos CSV o Excel en DataFrames
    if demanda_file.type == "text/csv":
        df_demanda = pd.read_csv(demanda_file)
    else:
        df_demanda = pd.read_excel(demanda_file)

    if stock_file.type == "text/csv":
        df_stock = pd.read_csv(stock_file)
    else:
        df_stock = pd.read_excel(stock_file)
    
    # Aquí puedes hacer validaciones sobre los datos si es necesario

    return df_demanda, df_stock

