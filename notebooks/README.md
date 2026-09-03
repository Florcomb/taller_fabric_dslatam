# Notebooks en formato `.ipynb`

Los mismos siete notebooks del taller, en formato Jupyter estándar.

## Cuál usar

El repositorio mantiene los notebooks en **dos formatos**, con el mismo contenido:

| | `fabric/<nombre>.Notebook/notebook-content.py` | `notebooks/<nombre>.ipynb` |
|---|---|---|
| Qué es | Formato de la integración con git de Fabric | Jupyter estándar |
| Se sincroniza con el workspace | **Sí** | No — vive fuera de `/fabric` |
| Cómo llega a Fabric | Solo con conectar el workspace a git | **Importar → Notebook → desde este equipo** |
| Se lee bien en GitHub | Sí, como Python | Regular: es JSON |
| Se abre en VS Code / Jupyter | No como notebook | **Sí** |
| Diff legible en un PR | **Sí** | No |

**Regla práctica:**

- **Vía rápida por git** → no toques esta carpeta. Fabric crea los notebooks desde `fabric/`.
- **Importar a mano, o trabajar fuera de Fabric** → usa estos `.ipynb`.
- **Taller en vivo paso a paso** → cualquiera de los dos. Copiar celda por celda desde el `.py` hace ver la estructura; importar el `.ipynb` es más rápido.

## Importar a Fabric

En el workspace: **Importar → Notebook → Desde este equipo** → selecciona uno o varios `.ipynb`.

Al importarlos, Fabric los crea como notebooks nuevos. Conserva los nombres: `nb_01_bronze_ingesta` invoca a `nb_00_setup` con `%run`, y esa llamada resuelve **por nombre**. Si renombras `nb_00_setup`, los otros seis dejan de funcionar.

> Estos notebooks **no traen lakehouse anclado**. No hace falta adjuntar ninguno: `nb_00_setup` resuelve el workspace y los tres lakehouses en tiempo de ejecución. Puedes adjuntar `lh_silver_polar` como lakehouse por defecto si quieres ver las tablas en el explorador, pero es solo comodidad visual.

## La fuente de verdad es el `.py`

Los `.ipynb` se **generan** a partir de los `notebook-content.py` con [`tools/py_a_ipynb.py`](../tools/py_a_ipynb.py):

```bash
python tools/py_a_ipynb.py
```

Y para verificar que están al día, sin escribir nada:

```bash
python tools/py_a_ipynb.py --check
```

Si editas un notebook, **edita el `.py` y regenera**. Al revés no funciona: los cambios hechos en un `.ipynb` no se propagan hacia atrás, y la próxima ejecución del conversor los pisa.

La razón de que la fuente sea el `.py`: es lo que Fabric sincroniza. Si Fabric confirma un cambio desde el workspace, llega en ese formato. Tener el `.ipynb` como fuente crearía dos verdades que se contradicen en el primer commit desde Fabric.

## Orden de ejecución

```
nb_00_setup              ← no se ejecuta solo; los demás lo invocan con %run
  ├─ nb_01_bronze_ingesta
  ├─ nb_02_silver_transforma
  ├─ nb_03_gold_agrega
  ├─ nb_04_modelos_semanticos      (instala semantic-link-labs)
  ├─ nb_05_enriquecer_sempy
  └─ nb_99_validacion              ← correr ANTES de generar la ontología
```

En `nb_04`, `nb_05` y `nb_99`, el `%pip install` es la **primera** celda, antes del `%run`. No inviertas ese orden: `%pip` reinicia el intérprete de Python y se lleva por delante todo lo que definió `nb_00_setup`.
