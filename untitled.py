import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import rasterio
from rasterstats import zonal_stats
import numpy as np
import unicodedata

# ==============================
# Funciones auxiliares
# ==============================

def normalize_str(s):
    """Quitar tildes y pasar a mayúsculas."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).upper()

def compute_stats(gdf, src, band=1):
    """Calcular estadísticas zonales para una banda específica."""
    affine = src.transform
    array = src.read(band)

    stats = zonal_stats(
        vectors=gdf,
        raster=array,
        affine=affine,
        stats=["count", "mean", "min", "max", "std"],
        add_stats={
            "p10": lambda x: np.nanpercentile(np.array(x, copy=True), 10) if len(x) > 0 else np.nan,
            "p90": lambda x: np.nanpercentile(np.array(x, copy=True), 90) if len(x) > 0 else np.nan,
            "range": lambda x: (np.nanmax(x) - np.nanmin(x)) if len(x) > 0 else np.nan,
        },
        nodata=src.nodata
    )

    df = pd.DataFrame(stats)
    df["BAND"] = band
    df["YEAR"] = 2019 + band  # Ajusta según tu metadata
    return df

# ==============================
# Streamlit App
# ==============================

st.title("Análisis de Friaje y Estadísticas Zonales de Tmin")

tabs = st.tabs([
    "📊 Data description",
    "🌍 Raster data analysis",
    "🧩 Public policy proposals"
])

# ------------------------------
# TAB 1: Data description
# ------------------------------
with tabs[0]:
    st.header("Descripción de Datos")
    st.markdown("""
    - **Shapefile**: distritos del Perú (nivel distrital preferido).  
    - **Raster Tmin**: temperatura mínima (GeoTIFF).  
    - **Unidades**: °C (si el raster está escalado ×10, se reescala).  
    - **Cobertura temporal**: bandas (Band 1 = 2020, Band 2 = 2021, etc.).  
    """)

    st.subheader("Carga de Archivos")
    shp_file = st.file_uploader("Sube el Shapefile (.shp)", type=["shp"])
    raster_file = st.file_uploader("Sube el Raster Tmin (.tif)", type=["tif"])

    if shp_file and raster_file:
        gdf = gpd.read_file(shp_file)
        gdf["NOMBRE"] = gdf["NOMBRE"].apply(normalize_str)

        src = rasterio.open(raster_file)
        st.success("Archivos cargados correctamente ✅")
        st.write(gdf.head())

# ------------------------------
# TAB 2: Raster data analysis
# ------------------------------
with tabs[1]:
    st.header("Análisis Raster y Estadísticas Zonales")

    if shp_file and raster_file:
        all_stats = []
        for b in range(1, src.count + 1):
            df_band = compute_stats(gdf, src, band=b)
            all_stats.append(df_band)

        stats_df = pd.concat(all_stats, axis=0).reset_index(drop=True)

        # Repetir geometrías
        gdf_repeated = pd.concat([gdf.reset_index(drop=True)] * src.count, ignore_index=True)

        # Merge final
        result = pd.concat([gdf_repeated, stats_df.add_prefix("TMIN_")], axis=1)

        st.subheader("Tabla de Resultados")
        st.dataframe(result.head())

        # Botón de descarga
        csv = result.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar resultados (CSV)", csv, "tmin_stats.csv", "text/csv")

        # Distribución
        st.subheader("Distribución de Tmin (media distrital)")
        fig, ax = plt.subplots()
        result["TMIN_mean"].hist(ax=ax, bins=30, color="skyblue", edgecolor="black")
        ax.set_title("Distribución de Tmin (media distrital)")
        st.pyplot(fig)

        # Ranking
        latest_year = result["TMIN_YEAR"].max()
        ranking = (
            result[result["TMIN_YEAR"] == latest_year]
            .sort_values("TMIN_mean")
            .head(15)
        )

        st.subheader(f"Top 15 distritos más fríos - {latest_year}")
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(ranking["NOMBRE"], ranking["TMIN_mean"], color="steelblue")
        ax.set_xlabel("Tmin (°C)")
        st.pyplot(fig)

        # Mapa coroplético
        st.subheader("Mapa: Tmin promedio por distrito")
        gdf_latest = result[result["TMIN_YEAR"] == latest_year]
        fig, ax = plt.subplots(figsize=(8, 10))
        gdf_latest.plot(column="TMIN_mean", cmap="coolwarm", legend=True, ax=ax)
        ax.set_title(f"Tmin promedio distrital - {latest_year}")
        st.pyplot(fig)

# ------------------------------
# TAB 3: Public policy proposals
# ------------------------------
with tabs[2]:
    st.header("Propuestas de Política Pública")
    st.markdown("""
    **Diagnóstico**  
    - Friaje en la Amazonía (Loreto, Ucayali, Madre de Dios).  
    - Heladas en la sierra sur (Puno, Cusco, Ayacucho, Huancavelica, Pasco).  

    **Medidas priorizadas**  
    1. **Viviendas térmicas / ISUR** → Reducción de casos de IRA en escolares.  
    2. **Kits antiheladas y refugios para ganado** → Menor mortalidad de alpacas.  
    3. **Calendarios agrícolas y pronósticos tempranos** → Reducir pérdidas de papa y quinua.  

    **KPI sugeridos**  
    - −20% casos de IRA en MINSA/ESSALUD.  
    - −25% mortalidad de alpacas (MIDAGRI).  
    - +15% rendimiento de cultivos sensibles (FAO).  
    """)
