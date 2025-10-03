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
    st.header("Heladas y friajes en el Perú: retos y políticas públicas de adaptación")
    st.markdown("""
### Introducción
El Perú es uno de los países más vulnerables a fenómenos climáticos extremos (IPCC, 2022). En las zonas altoandinas, las heladas generan graves impactos en la salud, la agricultura y la ganadería; mientras que, en la Amazonía, los friajes ocasionan descensos bruscos de temperatura que afectan a comunidades poco preparadas para el frío (SENAMHI, 2021). Ambos fenómenos se han intensificado en frecuencia y magnitud debido al cambio climático, lo que exige intervenciones públicas focalizadas y sostenibles (PCM, Plan Multisectorial ante Heladas y Friajes, 2022).

## Heladas altoandinas: impactos y respuestas

Al evaluar todos los distritos del territorio peruano, dentro del percentil 10 de temperatura mínima resaltan los siguientes departamentos: Apurímac, Arequipa, Ayacucho, Cusco, Huancavelica, Junín, Lima, Moquegua, Pasco, Puno y Tacna. De hecho, tomando temperaturas mínimas de sus distritos más fríos en los últimos 4 años se registran promedios cercanos a los −0.9 °C, con extremos en Tacna (−3.37 °C) y Cusco (−0.95 °C). Estas condiciones generan un aumento en casos de infecciones respiratorias agudas (IRA), pérdidas agrícolas y alta mortalidad de camélidos andinos (FAO, 2019; MINAGRI, 2020).

### Intervenciones recomendadas:

•	Viviendas térmicas (programas MiAbrigo/ISUR, costo aprox. S/ 11,000 por hogar) (FONCODES, 2021).
•	Kits antihelada con frazadas, estufas solares y cobertores para cultivos (S/ 500–800 por familia).
•	Refugios ganaderos para alpacas y ovinos (S/ 3,000–4,000 por unidad).
•	Calendarios agrícolas adaptados con información agroclimática del SENAMHI.

### Indicadores clave (KPI):

•	−20 % casos de IRA en distritos priorizados (MINSA, 2022).
Las infecciones respiratorias agudas (IRA) son uno de los principales efectos en salud por bajas temperaturas. En zonas altoandinas, los niños y adultos mayores son los más vulnerables: el frío intenso, viviendas mal aisladas y falta de abrigo generan picos de hospitalización durante heladas. Reducir un 20 % los casos significan que las intervenciones estarían protegiendo efectivamente a la población, aliviando también la carga sobre el sistema de salud.
•	−25 % mortalidad de alpacas (MIDAGRI, 2020).
La ganadería de camélidos es la base económica y alimentaria de miles de familias altoandinas. Reducir en un cuarto esa mortalidad mediante refugios, cobertizos y forraje de emergencia significa proteger ingresos familiares, asegurar proteínas locales y evitar pérdidas patrimoniales en hogares que dependen casi exclusivamente de esta actividad.
•	+15 % rendimiento de cultivos sensibles como papa y quinua (FAO, 2019).
El frío intenso daña cultivos básicos como papa, habas o quinua, esenciales tanto para la seguridad alimentaria como para el ingreso campesino. Aumentar 15 % los rendimientos gracias a tecnologías antihelada implica más resiliencia económica y alimentaria frente a climas extremos.
## Friajes amazónicos: vulnerabilidad y adaptación

Si bien Loreto, Madre de Dios y Ucayali no tienen temperaturas frías en comparación a los altoandinos, durante friajes extremos la temperatura puede descender hasta los 11–16 °C (SENAMHI, 2021), lo que representa un fuerte choque para comunidades habituadas a valores medios de 25–30 °C. Dentro del percentil 10 dentro de estos departamentos se tienen promedios de temperatura entre 20.6 y 20.8 °C. Asimismo, se identificaron 12 distritos como Balsapuerto (Loreto), Manu (Madre de Dios) o Iparia (Ucayali) se encuentran entre los más expuestos ya que tuvieron los registros de temperaturas más bajas en algún momento en los últimos 4 años.

### Intervenciones recomendadas:

•	Kits de abrigo (S/ 150–300 por hogar o estudiante).
•	Acondicionamiento de escuelas y centros de salud con cerramientos térmicos (S/ 20,000–40,000 por escuela; S/ 50,000–70,000 por establecimiento).
•	Campañas de salud preventiva con vacunación contra la influenza y educación comunitaria (MINSA, 2022).

###Indicadores clave (KPI):

•	−15 % casos de IRA en población infantil.
•	+10 % asistencia escolar durante friajes.
•	−10 % hospitalizaciones por complicaciones respiratorias.

## Conclusión

La evidencia de organismos nacionales e internacionales (SENAMHI, MINSA, FAO, PCM, MIDIS/FONCODES) confirma que las heladas y friajes son fenómenos recurrentes, cada vez más intensos y con impactos multidimensionales. La focalización en distritos del percentil 10 de Tmin permite priorizar recursos en territorios más vulnerables, optimizando la acción del Estado. Una estrategia integral que combine viviendas térmicas, refugios ganaderos, kits de abrigo y fortalecimiento de infraestructura social garantizará impactos medibles y sostenibles, consolidando la adaptación del Perú frente al cambio climático.

## Fuentes principales:

•	SENAMHI (2021). Reportes de friaje y heladas en el Perú.
•	PCM (2022). Plan Multisectorial ante Heladas y Friajes 2019–2021, actualización 2022.
•	FONCODES (2021). Evaluación del programa MiAbrigo.
•	FAO (2019). Impactos del cambio climático en la agricultura andina.
•	MINSA (2022). Boletín epidemiológico de infecciones respiratorias agudas.
•	MIDAGRI (2020). Plan de atención a la ganadería altoandina frente a heladas.
•	IPCC (2022). Sexto Informe de Evaluación.

""")
