# 📊 WFM Analyzer — Walk Forward Matrix para StrategyQuant

Herramienta web para **analizar, rankear y validar** estrategias de StrategyQuant X a partir de sus archivos `.sqx`. Detecta zonas estables en la matriz Walk Forward, calcula métricas de robustez y genera un dashboard visual con ranking automático y exportación de resultados.

---

## ✨ Features

- 📂 **Carga masiva** — Arrastra múltiples archivos `.sqx` simultáneamente y procesa todo en lote
- 🎯 **Detección de zona estable** — Algoritmo propio que busca la ventana 3×3 más plana en la superficie IS Ret/DD
- 🔥 **Heatmaps interactivos** — Visualiza 3 matrices: IS Ret/DD, Fitness OOS y Param Stability con escala cinemática
- 🏆 **Ranking automático** — Score compuesto que combina fitness, estabilidad de parámetros y densidad de celdas verdes
- ✅ **Validación por umbrales** — Fitness OOS, Param Stability y Green Cells configurables en vivo
- 📦 **Exportación** — Descarga el resumen en JSON estructurado o TXT legible
- 🎨 **Dashboard premium** — Interfaz dark con glassmorphism, gradientes y micro-animaciones
- 🔍 **Buscador + filtros** — Por nombre, por estado (aprobadas / descartadas / errores) y ordenamiento por score o nombre
- 📊 **Métricas con delta** — Cada métrica comparada contra su threshold, diferencia visible de un vistazo
- ⚡ **Sin estado persistente** — Todo se procesa en memoria, los archivos nunca se guardan

---

## 🛠️ Stack / Tecnologías

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.19+-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.24+-013243?style=flat-square&logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)

---

## 🚀 Cómo usar

1. **Exporta** tus estrategias desde StrategyQuant X como archivos `.sqx` (File → Save Strategy)
2. **Abre la app** en tu navegador
3. **Arrastra** uno o varios archivos `.sqx` a la zona de carga
4. **Ajusta** los umbrales si lo necesitas (Fitness OOS, Param Stability, Green cells mínimas)
5. **Pulsa "Analizar"** y espera el ranking
6. **Explora** cada estrategia: cambia entre las 3 superficies (Ret/DD, Fitness, PS) y revisa la zona óptima detectada
7. **Exporta** el resumen en JSON o TXT con un clic

---

## 💻 Instalación local

```bash
# Clonar el repositorio
git clone https://github.com/Sebastianlr11/wfm-analyzer.git
cd wfm-analyzer

# (Opcional) Crear entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
streamlit run app.py
```

> Requiere **Python 3.9+**

La app abrirá automáticamente en `http://localhost:8501`.

---

## ☁️ Deploy

La app está desplegada en **Streamlit Community Cloud** — gratis, auto-deploy en cada `git push`.

Para desplegar tu propia copia:

1. Fork este repo a tu cuenta de GitHub
2. Entra a [share.streamlit.io](https://share.streamlit.io)
3. **New app** → selecciona el repo → archivo principal `app.py`
4. Deploy

---

## 📐 Arquitectura

```
wfm-analyzer/
├── app.py              # Dashboard Streamlit, CSS, layout y render de componentes
├── analyzer.py         # Motor de analisis: zona estable, scoring, ranking, validacion
├── parser.py           # Parser de archivos .sqx (ZIP + XML) a estructura interna
├── requirements.txt    # Dependencias Python
└── README.md
```

**Flujo de datos:**

```
.sqx (ZIP)  →  parser.py  →  dict con matrices runs×oos
                                   ↓
                             analyzer.py  →  zona estable + score + verdict
                                   ↓
                               app.py  →  heatmap + metricas + ranking
```

---

## 🧮 Metodología

El score final de cada estrategia combina:

- **Fitness OOS normalizado** (0-1) — medido sobre la zona estable detectada
- **Param Stability** — Sys. Parameter Permutation de la zona
- **Green cells ratio** — proporción de celdas que pasan todos los umbrales
- **Zone flatness penalty** — pairwise deviation + cardinal deviation de la ventana 3×3

Una estrategia se marca **APPROVED** solo si pasa los 3 gates: Fitness ≥ threshold, PS ≥ threshold, y Green cells ≥ mínimo configurado.

---

## 📄 Licencia

[MIT](LICENSE) — Libre para uso personal y comercial.
