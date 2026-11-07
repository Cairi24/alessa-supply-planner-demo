# ALESSA Supply Planner V9 — Demostración web remota

## Qué incluye
La misma navegación, identidad azul/amarillo/rojo, filtros por columna y tabla de compras editable de V8, con **36 SKU totalmente ficticios**. Se puede publicar en la nube para verla en otro dispositivo. **No contiene ventas, inventarios, presupuestos, SKU, proveedores ni pedidos reales de ALESSA.** Los nombres «Proveedor Demostración» y los productos son simulados.

**No incluye:** carga de archivos reales, autenticación corporativa, envío de correo, conexión al servidor, persistencia de decisiones entre sesiones ni cálculos validados sobre datos de ALESSA. Las aprobaciones son solo simuladas en la sesión web. El Excel exportado contendrá solo datos ficticios.

## Publicar en Streamlit Community Cloud (enlace web)

1. Crea un repositorio nuevo en GitHub llamado, por ejemplo, `alessa-planner-demo`. Puedes utilizar un repositorio **privado**. No subas la carpeta de V8 con datos reales ni ninguno de los archivos `.xlsx` originales.
2. Sube **el contenido** de esta carpeta V9 (de modo que `app.py` y `requirements.txt` queden en la raíz del repositorio). No necesitas añadir el ZIP dentro del repositorio.
3. Abre https://share.streamlit.io, inicia sesión con GitHub y selecciona **Create app**.
4. Elige tu repositorio, la rama `main` y el archivo principal **`app.py`**. Selecciona **Deploy**.
5. Obtendrás una dirección `https://....streamlit.app` accesible desde otra computadora o celular. Si deseas restringir quién puede verla, ve a **App settings → Sharing → Only specific people can view this app** y agrega usuarios autorizados.
6. Prueba el filtro `Riesgo`, modifica la columna `Compra final` y exporta un plan XLSX **ficticio**.

⚠️ Publicar un repositorio público hace que el código esté visible, aunque los datos sean ficticios. Una app privada restringe el acceso según la configuración del servicio; revisa sus políticas antes de compartirla.

## Ejecutar en otro servidor

El repositorio contiene un `Dockerfile`. Tras autorización de Sistemas puedes construir la imagen en un servidor propio:

```bash
docker build -t alessa-planner-demo:v9 .
docker run --rm -p 127.0.0.1:8501:8501 alessa-planner-demo:v9
```

Esto deja la interfaz en `http://127.0.0.1:8501` para un proxy HTTPS **con autenticación**. No abras el puerto 8501 directamente a internet. Configura HTTPS, acceso corporativo y controles de seguridad mediante Sistemas.

## Diferencia entre demo y aplicación real

La aplicación V8 con información real no debe publicarse en Community Cloud ni GitHub sin permiso de ALESSA. Para una versión productiva remota necesitamos implementar identidad/autorización, almacenamiento persistente y permisos por comprador, respaldo, cifrado, aislamiento por sesión y una arquitectura de datos validada. La edición V9 **no habilita cargar datos empresariales**: es segura para demostración precisamente porque solo usa datos sintéticos.

## En caso de trabajar sin internet

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Consideraciones de cálculo

El forecast y los indicadores son únicamente ilustrativos. Los niveles Base/Moderada/Alta/Máxima siguen siendo factores provisionales. La nacionalización se calcula con 7 días hábiles y el calendario de feriados del piloto sigue siendo preliminar.
